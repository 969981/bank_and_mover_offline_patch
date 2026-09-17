# Pokémon Bank SaveBoxes / BankObject 更新事务逆向分析

本文记录 Pokémon Bank v1.5 原版客户端中“保存盒子到服务器”相关流程的静态逆向结论，重点覆盖 BankObject 更新事务、请求对象、版本字段、事务状态、HPP/HTTP 上传、提交/回滚与冲突恢复。

> 本文只描述能够从原版客户端二进制、NEX 协议结构和公开实现交叉确认的客户端协议行为。任天堂服务端内部的数据库判断、事务密码生成、版本递增策略等服务端实现细节不在本文确认范围内。

## 1. 分析目标与基线

目标应用：

- Title ID：`00040000000C9B00`
- Pokémon Bank 内部版本：v1.5
- Image base：`0x00100000`
- 解压 `.code` SHA-256：

```text
2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

该哈希与 `bank/docs/code-analysis.md` 中记录的 stock binary 完全一致，因此本文地址均针对同一原版二进制。

参考：

- [`code-analysis.md`](./code-analysis.md)
- [NintendoClientsWiki - Data Store Protocol (Pokemon Bank)](https://github.com/kinnay/NintendoClientsWiki/blob/master/Data-Store-Protocol-(Pokemon-Bank).md)
- [PretendoNetwork/nex-protocols-go](https://github.com/PretendoNetwork/nex-protocols-go/tree/master/datastore/pokemon-bank)

## 2. 结论摘要

Pokémon Bank 中不存在一个单独的 REST 风格 `SaveBoxesToServer()` 请求。

用户在 Bank Box UI 中执行保存后，客户端实际上执行的是一个分阶段的远端事务：

```text
Bank Box UI
    |
    v
0x002B1CF8  BankSaveState_Update
    |
    +--> 0x002B2320 BankSave_SerializeAndStage
    |        |
    |        +--> Serialize BankObject
    |        |      size = 0xBB518
    |        |
    |        +--> 0x002A2504 BankRemote_StageFileUpdate
    |                 |
    |                 +--> RMC 52 PrepareUpdateBankObject
    |                 |
    |                 +--> server returns
    |                 |      BankTransactionParam
    |                 |      DataStoreReqUpdateInfo
    |                 |
    |                 +--> HPP / HTTPS upload BankObject body
    |
    +--> game / local save
    |
    +--> success
    |      +--> 0x001D5D74
    |             RMC 53 CompleteUpdateBankObject
    |
    +--> failure
           +--> 0x001D5C28
                  RMC 54 RollbackBankObject
```

因此“保存到服务器”至少包含三层协议：

1. NEX RMC 控制平面；
2. HPP/HTTP 文件传输；
3. 最后的事务 commit / rollback。

## 3. 原版保存状态机

Wokann 已确认普通 Bank 保存的关键链：

```text
0x002B2320 BankSave_SerializeAndStage
  -> 0x002B2490 completes 0xBB518 serialization
  -> 0x002B24A0 / 0x002A2504 stages the remote update
  -> game and local save operations
  -> 0x001D5D74 commits
  -> 0x001D5C28 rolls back on failure
```

对应地址：

| 地址 | 作用 |
|---:|---|
| `0x002B1CF8` | Bank 保存状态机 |
| `0x002B2320` | 序列化 BankObject 并开始远端 stage |
| `0x002A2504` | Prepare / stage BankObject update |
| `0x001D5D74` | 完成远端更新事务 |
| `0x001D5C28` | 回滚未完成远端更新事务 |

原版 BankObject 完整文件长度：

```text
0xBB518 bytes
```

保存路径中的 stage 调用可抽象为：

```c
BankRemote_StageFileUpdate(
    remote_context,
    serialized_bank_data,
    bank_data_size,
    transaction_param
);
```

ARM32 调用点表现为：

```text
r0 = remote context
r1 = serialized BankObject pointer
r2 = 0xBB518
r3 = BankTransactionParam *
BL 0x002A2504
```

## 4. BankTransactionParam

Pokemon Bank 专用 DataStore 协议定义了：

```c
struct BankTransactionParam
{
    uint64_t dataId;
    uint32_t curVersion;
    uint32_t updateVersion;
    uint32_t size;
    uint64_t transactionPassword;
};
```

### 4.1 Wire 序列化顺序

NEX wire format 中字段顺序为：

```text
dataId
curVersion
updateVersion
size
transactionPassword
```

Pretendo 的 `BankTransactionParam.WriteTo()` / `ExtractFrom()` 与该顺序一致。

### 4.2 ARM32 内存布局

客户端运行时按 ARM32 ABI 对齐后，可表示为：

```c
struct BankTransactionParam_mem
{
    uint64_t dataId;               // +0x00
    uint32_t curVersion;           // +0x08
    uint32_t updateVersion;        // +0x0C
    uint32_t size;                 // +0x10
    uint32_t padding;              // +0x14, ABI alignment only
    uint64_t transactionPassword;  // +0x18
};                                 // sizeof = 0x20
```

`+0x14` 的 4 字节仅用于内存对齐，不属于 NEX wire structure。

## 5. UID / identity

原版 update request 中没有一个名为 `uid` 的字段。

实际参与身份和对象定位的上下文至少包括：

```text
NEX authenticated session / principal
slotId
dataId
applicationId (事务查询/恢复路径)
```

其中：

- `dataId:uint64` 是服务器 DataStore BankObject ID；
- 它不应直接等同于 NNID、PID 或用户 UID；
- 当前用户身份主要由已经建立的 NEX 认证会话决定；
- DataStore metadata 另有 `ownerId:uint32`；
- `pApplicationId:uint16` 用于事务状态/恢复语境，不是 UID。

因此不能把原版协议简化成：

```json
{"uid": "...", "boxes": "..."}
```

## 6. revision / 版本控制

原版不存在单个 `revision` 字段，而是：

```text
curVersion
updateVersion
```

推荐逆向命名：

```text
curVersion     -> base_revision
updateVersion  -> pending_revision
```

客户端会把当前事务版本信息提交给 `PrepareUpdateBankObject`，服务端再返回新的 `BankTransactionParam` 供后续 HPP 上传和最终 complete/rollback 使用。

这说明版本号是事务并发控制的一部分。

### 已确认

客户端确实携带：

```text
dataId
curVersion
updateVersion
transactionPassword
```

作为更新事务上下文。

### 未从客户端静态证明

不能仅凭客户端代码断言服务端内部一定执行：

```c
if (curVersion != db.version)
    return Conflict;
```

也不能静态确认服务端 `updateVersion` 一定按 `curVersion + 1` 生成。

这些属于服务端实现策略，需要服务器实现、历史抓包或动态实验继续确认。

## 7. timestamp

一个重要结论是：

**`BankTransactionParam` 中没有 timestamp。**

Prepare / Complete BankObject update 的 transaction object 不包含：

```text
timestamp
updatedAt
lastModified
serverTime
```

DataStore metadata 确实包含：

```text
createdTime
updatedTime
```

Pokemon Bank 相关结构中也能看到带 `updatedTime` 的服务器元数据对象。

但 `updatedTime` 不属于 `BankTransactionParam`，因此目前没有证据表明 Bank update 的乐观并发控制直接使用 timestamp。

客户端可见的主要 update token 是：

```text
curVersion
updateVersion
transactionPassword
```

## 8. transactionPassword

`transactionPassword:uint64` 应视为服务器事务上下文中的 opaque token，而不是 Bank 文件本身的“密码”。

PrepareUpdate 后返回的完整 `BankTransactionParam` 会继续被状态机保存，并在后续：

```text
CompleteUpdateBankObject
```

或：

```text
RollbackBankObject
```

中提交回服务端。

因此一个有效的 update transaction 至少需要保持：

```text
dataId
curVersion
updateVersion
size
transactionPassword
slotId
authenticated NEX session
```

这些值之间的对应关系不能安全地从不同会话或旧事务中任意拼接。

## 9. Pokemon Bank 专用 NEX RMC 48-54

Pokemon Bank DataStore extension protocol 的 BankObject 相关方法如下。

### 48 / `0x30` GetTransactionParam

```cpp
GetTransactionParam(
    uint16_t slotId
)
->
    BankTransactionParam pTransactionParam,
    uint32_t pStatus,
    uint16_t pApplicationId;
```

### 49 / `0x31` PreparePostBankObject

```cpp
PreparePostBankObject(
    uint16_t slotId,
    uint32_t size
)
->
    DataStoreReqPostInfo pReqPostInfo;
```

用于创建/首次 post BankObject 的流程，与普通已存在 BankObject 的 update 流程应区分。

### 50 / `0x32` CompletePostBankObject

```cpp
CompletePostBankObject(
    DataStoreCompletePostParam param
);
```

### 51 / `0x33` PrepareGetBankObject

```cpp
PrepareGetBankObject(
    uint16_t slotId,
    uint16_t applicationId
)
->
    BankTransactionParam pTransactionParam,
    DataStoreReqGetInfo pReqGetInfo;
```

### 52 / `0x34` PrepareUpdateBankObject

```cpp
PrepareUpdateBankObject(
    BankTransactionParam transactionParam
)
->
    BankTransactionParam pTransactionParam,
    DataStoreReqUpdateInfo pReqUpdateInfo;
```

### 53 / `0x35` CompleteUpdateBankObject

```cpp
CompleteUpdateBankObject(
    uint16_t slotId,
    BankTransactionParam transactionParam,
    bool isForce
);
```

### 54 / `0x36` RollbackBankObject

```cpp
RollbackBankObject(
    uint16_t slotId,
    BankTransactionParam transactionParam,
    bool isForce
);
```

普通 Bank 保存路径中观察到的正常 complete / rollback 使用非 force 语义；不要把 `isForce` 当成 conflict 字段。

## 10. PrepareUpdateBankObject 的返回对象

服务端对 RMC 52 的响应可抽象为：

```c
struct PrepareUpdateResponse
{
    BankTransactionParam pTransactionParam;
    DataStoreReqUpdateInfo pReqUpdateInfo;
};
```

其中 `DataStoreReqUpdateInfo` 提供实际 HPP/HTTP 文件上传所需的信息，核心包括：

```c
struct DataStoreReqUpdateInfo
{
    uint32_t version;
    string url;
    List<DataStoreKeyValue> requestHeaders;
    List<DataStoreKeyValue> formFields;
    Buffer rootCaCert;
};
```

因此客户端不会自行推导最终上传 URL。

流程是：

```text
PrepareUpdateBankObject
        |
        +--> transaction context
        |
        +--> upload URL
        +--> HTTP headers
        +--> multipart/form fields
        +--> root CA certificate
        |
        v
HPP / HTTPS upload
```

## 11. HPP / HTTP 层

`code-analysis.md` 已确认相关函数：

| 地址 | 作用 |
|---:|---|
| `0x00198A78` | Prepare and start HTTP request |
| `0x00199570` | HTTP streaming send/receive worker |
| `0x001C1EF8` | Build multipart file stream (`name="file"`) |
| `0x001C22F0` | Emit multipart prefix/body/suffix |
| `0x00245414` | Send HTTPC chunk |
| `0x002454A4` | Finish POST body |
| `0x002454C4` | Receive HTTP response |
| `0x001B23E8` | Initialize HPP POST job |
| `0x001B2544` | Process HPP result / redirect / retry |
| `0x001B2820` | Rebuild retry request |

原版 HPP/HTTP 层明确处理：

```text
307 Temporary Redirect
404 Not Found
409 Conflict
500 Internal Server Error
```

Wokann 静态分析确认：

- 最多跟随 5 次 `307` redirect；
- `409` 与 `500` 会进入 retry 路径；
- error response cache 上限为 `0x2800` bytes。

因此 `409 Conflict` 是实际文件上传阶段可见的显式冲突信号之一。

## 12. conflict 不是一个布尔字段

原版中没有：

```c
bool conflict;
```

冲突和恢复由多个机制共同组成。

### 12.1 Transaction / revision 层

```text
dataId
curVersion
updateVersion
transactionPassword
```

共同描述当前服务器对象及 update transaction。

### 12.2 HPP/HTTP 层

HTTP `409 Conflict` 明确进入客户端 retry 路径。

### 12.3 Transaction recovery 层

客户端可通过：

```text
GetTransactionParam(slotId)
```

重新查询服务器上是否存在未完成事务，并得到：

```text
BankTransactionParam
pStatus
pApplicationId
```

随后由状态机选择 reconciliation / retry / rollback 路径。

## 13. pStatus

公开协议只定义：

```text
pStatus:uint32
```

而未给出完整语义枚举。

原版客户端恢复状态机会直接比较至少：

```text
0x34 == 52
0x35 == 53
```

这两个值又恰好对应 Pokemon Bank 专用 RMC：

```text
52 PrepareUpdateBankObject
53 CompleteUpdateBankObject
```

因此目前可高置信度解释：

```text
pStatus == 52
    服务器记录显示存在 PrepareUpdate / staged update 阶段事务，
    客户端需要进入未完成更新恢复路径。

pStatus == 53
    事务已进入 CompleteUpdate 相关阶段，
    客户端需要执行 completion reconciliation。
```

现阶段不应在没有动态证据的情况下给其它 `pStatus` 值强行命名。

相关 Bank 外层状态包括：

| State | 地址 | 已知作用 |
|---:|---:|---|
| 11 | `0x002AF034` | 检查服务器 update/transaction 状态并选择恢复路径 |
| 17 | `0x002A93F4` | other-side transaction reconciliation / retry |
| 18 | `0x002A8760` | current-user transaction reconciliation / retry |
| 19 | `0x002AEB9C` | rollback/release no-save path |
| 23 | `0x002AD7BC` | forced rollback / transaction recovery |

## 14. First-use Post 与普通 Update 必须区分

首次使用 Bank、服务器尚不存在 BankObject 时，原版不是直接执行普通 update。

已有分析确认 state 9：

```text
0x002AE568
```

负责 first-use Bank file creation。

核心路径：

```text
initialize BankObject
    |
serialize 0xBB518 bytes
    |
0x002A37E0 BankRemote_CreateSerializedFile
    |
PreparePostBankObject / HTTP upload / CompletePostBankObject
```

因此至少存在两类远端写入语义：

```text
POST   -> create new BankObject
UPDATE -> update existing BankObject transactionally
```

后续实验时不能把两条路径混用。

## 15. 推荐的逆向抽象

为了避免 `UID/revision/timestamp/conflict` 这些过度泛化的名字，建议后续工具和 IDA/Ghidra type 统一使用：

```cpp
struct BankSaveTransaction
{
    uint64_t object_id;             // stock: dataId
    uint32_t base_revision;         // stock: curVersion
    uint32_t pending_revision;      // stock: updateVersion
    uint32_t content_size;          // stock: size
    uint64_t transaction_token;     // stock: transactionPassword
};

struct BankTransactionQueryResult
{
    BankSaveTransaction transaction;
    uint32_t phase;                 // stock: pStatus
    uint16_t application_id;        // stock: pApplicationId
};

struct BankUploadTicket
{
    uint32_t version;
    string upload_url;
    Headers request_headers;
    Fields multipart_fields;
    Buffer root_ca_cert;
};
```

注意：该命名是研究层语义化别名，不替代原版 DDL 字段名。

## 16. 完整客户端事务模型

```text
NEX authenticated session
        |
        v
GetTransactionParam(slotId)
        |
        +--> BankTransactionParam
        +--> pStatus
        +--> pApplicationId
        |
        v
serialize BankObject (0xBB518)
        |
        v
PrepareUpdateBankObject(transactionParam)
        |
        +--> updated BankTransactionParam
        |
        +--> DataStoreReqUpdateInfo
                |
                +--> URL
                +--> headers
                +--> formFields
                +--> root CA
        |
        v
HPP / HTTPS upload
        |
        +--> 307 redirect
        +--> 409 conflict / retry
        +--> 500 retry
        |
        v
game/local save
        |
        +--> success
        |       |
        |       v
        |   CompleteUpdateBankObject(
        |       slotId,
        |       transactionParam,
        |       false)
        |
        +--> failure
                |
                v
            RollbackBankObject(
                slotId,
                transactionParam,
                false)
```

## 17. 当前能确认与不能确认的边界

### 客户端侧已高置信度确认

- stock binary 版本与 SHA-256；
- BankObject 大小 `0xBB518`；
- Bank 保存 stage / commit / rollback 地址链；
- `BankTransactionParam` 字段及 wire 顺序；
- ARM32 runtime 对齐后的 `0x20` 内存布局；
- Pokemon Bank DataStore RMC 48-54 方法签名；
- `PrepareUpdateBankObject` 返回 transaction + HTTP upload descriptor；
- HPP/HTTP 文件上传与 `307/404/409/500` 行为；
- timestamp 不属于 `BankTransactionParam`；
- `pStatus` 至少存在 `52/53` 对应的恢复判断；
- normal save 在成功时 complete、失败时 rollback。

### 仍需动态抓包或服务端实现验证

- `transactionPassword` 的服务器生成算法；
- `curVersion` 与数据库 revision 的精确比较规则；
- `updateVersion` 的精确递增/分配策略；
- `pStatus` 的完整枚举；
- HTTP `409` 的服务器具体触发条件；
- `isForce=true` 的服务器精确语义；
- session principal、`ownerId`、`dataId`、`slotId` 的完整授权关系；
- transaction timeout / expiry 行为；
- 同一 BankObject 多客户端并发写入时的服务端优先级和恢复策略。

## 18. 后续建议的动态验证任务

后续若继续研究官方协议，建议优先做“观察而非伪造写入”的动态验证：

1. Hook `GetTransactionParam` 回调，连续记录 `dataId / curVersion / updateVersion / size / transactionPassword / pStatus / pApplicationId`；
2. Hook `PrepareUpdateBankObject` request/response，比较 prepare 前后的 transaction param；
3. Hook HPP job，记录 URL、headers、form fields、HTTP status；
4. Hook `CompleteUpdateBankObject` / `RollbackBankObject` 调用参数；
5. 人为在 prepare 后、HTTP upload 后、local save 后分别终止应用，观察下次启动 `pStatus`；
6. 对比不同 `applicationId`、不同游戏卡带和 HOME 路径的 transaction recovery；
7. 不修改服务器数据的前提下建立完整时序日志，再决定是否需要构造本地协议模拟器。

这能把目前客户端静态分析中剩余的 `pStatus`、revision 和 transaction lifecycle 缺口逐步补齐，同时避免把未经证明的服务端规则写死进补丁。