# Pokémon Bank 网络保存失败后的 Trainer/Save Mismatch 恢复研究

> 研究分支：`feature/official-bank-recovery-research`
>
> 基线分支：`feature/official-bank-bulk-sync`
>
> 目标应用：Pokémon Bank `00040000000C9B00`，内部版本 v1.5。
>
> stock `.code` SHA-256：`2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`

## 1. 实机问题定义

当前已经确认的实机现象不是“恢复旧存档后 Bank 拒绝联动”，而是：

1. 使用 `feature/official-bank-bulk-sync` 正常联动某个 XY/ORAS/SM/USUM 游戏；
2. `bulk_import.bin` 被合并进刚从官方服务器下载的 runtime `BankObject`；
3. 大多数情况下，原版 Bank 保存事务可以正常完成；
4. 少数情况下，因为网络异常，Bank 保存失败；
5. 此后没有使用 JKSM/Checkpoint 恢复游戏存档，也没有再进入游戏修改或保存；
6. 下一次使用同一份游戏存档联动 Bank 时，出现“训练家/存档不一致”一类错误并阻塞，无法继续进入 Bank Box UI。

因此，本研究明确排除以下前提：

- 用户主动回滚了游戏存档；
- `bulk_import.bin` 直接写了游戏 `main`；
- 所有保存失败都会触发 mismatch；
- mismatch 一定等价于简单比较 Trainer ID；
- mismatch 一定只由公开资料中的 0x20 Pokémon Bank application data 决定。

要解释的是：**同一份游戏 save 在一次网络异常保存后，为什么会被下一次 Bank recovery flow 判定为与上一次事务不一致。**

---

## 2. Official Bulk Sync V3 与该故障的边界

V3 的唯一 stock hook：

```text
0x002AF460  BankDataSyncState_Update
```

V3 只在：

```text
substate == 2
callbackStatus == 1
specialFlag == 0
```

时取得 fresh server `BankObject`，备份后将 `bulk_import.bin` 的主 100 Box 数据合入 runtime object。

当前实现没有 hook：

```text
BankSaveState_Update
BankSave_SerializeAndStage
BankRemote_StageFileUpdate
CompleteUpdateBankObject
RollbackBankObject
state 11/17/18/22/23 recovery flow
```

`official_bulk_sync.c` 也没有打开当前游戏的 `main` 做 raw write。

因此当前高置信度边界是：

```text
V3 负责产生一个被修改过的 runtime BankObject
        ↓
用户按“保存”
        ↓
后续保存、游戏 main 写回、Complete/Rollback 仍全部由 stock Bank 执行
```

这意味着网络故障后的 trainer/save mismatch 首先应按 **stock Bank transaction/recovery failure** 调查，而不是先假定 bulk merge 直接破坏了游戏 save。

---

## 3. 已确认的 stock 保存事务

已静态确认的保存链：

```text
0x002B1CF8  BankSaveState_Update
        ↓
0x002B2320  BankSave_SerializeAndStage
        ↓
serialize complete 0xBB518 BankObject
        ↓
0x002A2504  BankRemote_StageFileUpdate
        ↓
RMC 52 PrepareUpdateBankObject
        ↓
HPP/HTTPS upload
        ↓
game/local save
        ↓
成功：0x001D5D74 / RMC 53 CompleteUpdateBankObject
失败：0x001D5C28 / RMC 54 RollbackBankObject
```

事务对象：

```c
struct BankTransactionParam_mem {
    uint64_t dataId;              // +0x00
    uint32_t curVersion;          // +0x08
    uint32_t updateVersion;       // +0x0C
    uint32_t size;                // +0x10
    uint32_t padding;             // +0x14
    uint64_t transactionPassword; // +0x18
};                                // 0x20
```

恢复查询 `GetTransactionParam(slotId)` 还会返回：

```text
pStatus:uint32
pApplicationId:uint16
```

原版客户端至少显式识别：

```text
pStatus == 52  // PrepareUpdateBankObject
pStatus == 53  // CompleteUpdateBankObject
```

因此“保存失败”不能被理解为原子性的“什么都没发生”。在网络异常时，服务器事务、上传状态、游戏本地保存、最终 Complete/Rollback 可能处在不同阶段。

---

## 4. 当前恢复状态链

已经确认的外层状态：

| State | Update | 当前意义 |
|---:|---:|---|
| 7 | `0x002B1CF8` | 保存：serialize / stage / game save / commit-or-rollback |
| 8 | `0x002ACBDC` | 查询服务器记录与 transaction status |
| 10 | `0x002ADC50` | 选择联动游戏 |
| 11 | `0x002AF034` | 检查服务器 update/transaction 状态并选择 recovery path |
| 16 | `0x002AF460` | 选择游戏后的完整 BankObject 下载 |
| 17 | `0x002A93F4` | 另一侧记录的 transaction reconciliation/retry |
| 18 | `0x002A8760` | 当前用户记录的 transaction reconciliation/retry |
| 19 | `0x002AEB9C` | 不保存路径的 rollback/release |
| 22 | `0x002A9118` | save-error handling |
| 23 | `0x002AD7BC` | forced rollback / transaction recovery |
| 25 | `0x002A7094` | Bank Box UI |

正常 Bank 路径：

```text
4 -> 10 -> 11 -> [18] -> 17 -> 16 -> 12/13 -> 25
```

当前 mismatch 的优先调查范围因此是：

```text
state 8
  -> state 10
  -> state 11
  -> state 17/18
  -> Trainer/save identity validation
  -> state 16
```

以及故障产生侧：

```text
state 7
  -> network error
  -> state 22
  -> state 23 / rollback or reconciliation
```

---

## 5. 新发现：BankObject 自身保存 8 份 source-game trainer summary

完整 v1.5 BankObject 在：

```text
0x0AD61C
```

保存：

```text
8 × 0x44-byte source-game records
```

项目现有 viewer 已能稳定解析每条记录：

```text
+0x00  26 bytes  UTF-16 player name
+0x1A  u16       sex / related value
+0x1C  u32       trainer_id
+0x20  9 × u32   statistics / per-source fields
```

对应现有实现：

```python
SOURCE_RECORD_BASE = 0xAD61C
SOURCE_RECORD_SIZE = 68

name       = decode_utf16(core[base:base + 26])
sex        = u16(base + 26)
trainer_id = u32(base + 28)
stats      = 9 * u32(base + 32)
```

这是一条高价值新线索，因为用户看到的阻塞文本属于 trainer/save mismatch 语义，而服务器 BankObject 本身确实保留了按 8 个受支持游戏 profile 划分的 Trainer summary。

**但目前不能据此断言这 8 条记录就是 mismatch gate。**

下一步必须确认：

1. 哪些 stock 函数写入 `BankObject + 8 + 0xAD61C`；
2. 写入源是否来自当前 active `GameSaveModel`；
3. state 11/17/18 是否读取这些记录；
4. 是否将其中 `trainer_id` / name / stats 与当前 game save 比较；
5. mismatch 是本地 branch，还是服务器 response 后的错误映射。

---

## 6. 另一个候选：游戏 save 中的 Bank linkage/application state

Gen6 公开 save-format 研究表明，游戏 `main` 存在独立的 Pokémon Bank application/linkage block，其中包含 Bank identity-like 数据、previous/current usage counter 与 signature-like 数据。

这一事实能解释：

```text
“游戏 Pokémon 一个都没动”
!=
“Bank 保存过程中游戏 main 一个字节都没改”
```

但是当前项目自己的静态分析还没有闭环证明：

```text
该 block 的 stock writer
该 block 的 stock reader
其与 state 11/17/18 的关系
其与 Trainer ID Error 的直接关系
```

因此它在本研究中保持 **候选数据源** 身份，不作为既定根因。

---

## 7. 当前根因假设矩阵

### H1：服务器 pending transaction + 本地 game-link 状态分叉

网络故障发生在：

```text
Prepare/Upload 成功
-> game save 已发生
-> CompleteUpdate 未可靠完成
```

下一次 recovery flow 对当前 game linkage 与 transaction context 进行比较并失败。

支持点：

- stock 保存明确把 game save 放在远端 stage 与 final complete/rollback 之间；
- 服务器明确保留 `curVersion/updateVersion/transactionPassword/pStatus/pApplicationId`；
- 用户无需手工 restore 即可复现。

待证：具体 game-link writer 与 comparator。

### H2：BankObject source-game trainer summary 与当前 save 不一致

网络故障/rollback 后，server BankObject 中某 profile 的 source-game record 与当前 game model 所派生的 trainer summary 不一致。

支持点：BankObject 确有 8×0x44 trainer summary。

待证：state 11/17/18 是否读取/比较。

### H3：纯客户端 recovery gate

服务器只返回 pending transaction context；客户端自己判断当前游戏不是上次那份并阻塞。

验证方法：在精确确认 comparator 后，仅 recovery 状态实验性 bypass；若随后 stock state 17/18/23 能完成 cleanup 并正常进入 state 16，则成立。

### H4：客户端 + 服务器双重验证

本地 bypass 后，服务器仍通过 applicationId / transaction context / version / identity 拒绝 recovery。

验证方法：实验性 bypass 后观察下一次 RMC/HPP 结果。

---

## 8. 禁止先做的修复

在根因未闭环前，不做：

```text
ValidateTrainer() 永远 return true
NOP 所有 Trainer mismatch branch
跳过所有游戏 main save
伪造所有 Trainer ID
无条件 force Complete/Rollback
```

原因：这些做法可能把真正不同的游戏/旧档也视为同一事务参与者，破坏 Bank 用来避免复制或丢失的跨系统一致性保护。

---

## 9. 第一阶段静态提取目标

原始 Ghidra 导出 `bank/docs/code.bin_all_functions.c` 超过 11 MB，常规 GitHub 内容接口无法方便地按函数读取。

因此研究分支增加一个可复用的静态提取工具，按地址/函数名抽取：

```text
0x002ACBDC  state 8
0x002ADC50  state 10
0x002AF034  state 11
0x002A93F4  state 17
0x002A8760  state 18
0x002A9118  state 22
0x002AD7BC  state 23
0x002B1CF8  state 7
```

并扫描：

```text
0xAD61C / runtime 0xAD624 source-game record references
0x34 / 52 pStatus comparisons
0x35 / 53 pStatus comparisons
calls to 0x001D5D74 / 0x001D5C28
references to active GameProfile/GameSaveModel helpers
```

提取结果将作为后续地址命名和 Hook 选择依据。

---

## 10. 实验 Hook 的准入条件

只有在静态证据确认以下内容后才新增 production/experimental hook：

1. 找到具体 mismatch decision；
2. 找到 decision 的输入来源；
3. 确认它只出现在 pending/recovery 场景，或能可靠判断 recovery context；
4. 明确 bypass 后 stock flow 的下一状态；
5. 保留正常 session 的 trainer/save validation。

第一版实验 Hook 的目标不是“永久取消校验”，而是回答：

> 在已确认的 recovery mismatch 条件下，允许 stock recovery 继续后，服务器是否能自行完成 reconciliation/rollback 并恢复进入 state 16？

若成功，说明主要阻塞是客户端 gate；若后续服务器仍返回 conflict/RMC error，则继续研究服务器侧约束。

---

## 11. V3 代码空间约束

当前 V3 使用：

```text
0x00313910 .. 0x00314000
```

这一段 RX text tail，总大小仅 `0x6F0`。

当前 CI 对 production Thumb object 的 text budget 是：

```text
<= 1680 bytes
```

现有 V3 payload 已非常接近预算，因此 recovery 改造不能假定可以直接把大量新 C 逻辑塞进相同 tail。

后续若需要 runtime recovery code，必须先证明一种安全布局：

- 极小的 branch patch / assembly shim；或
- 经静态引用分析确认可复用的不可达 stock function body；或
- 其它已验证 RX 空间。

禁止重新使用已在 V1 证明危险的 mapped `.data` code cave。

---

## 12. 验证标准

研究阶段每个结论分为：

- **静态确认**：可由 stock code/control-flow/data-flow 直接证明；
- **结构推断**：多处证据一致，但尚缺直接 caller/comparator；
- **实机确认**：通过真实官方服务器 round-trip/recovery 观察；
- **未确认**：仅保留为候选假设。

最终 recovery patch 至少需要：

1. stock hash 限定；
2. host/static contract tests；
3. patch whitelist verifier；
4. 正常成功保存回归；
5. 正常重新联动回归；
6. 网络故障后的 recovery 实机验证；
7. 真正不同 Trainer/save 不应被普通路径无条件接受。
