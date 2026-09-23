# Pokémon Bank v1.5 异常保存恢复与 Trainer mismatch 地址图

> 目标：解释“正常保存通常成功，但网络偶发失败后，同一份、未恢复/未修改的游戏存档再次联动时提示训练家/存档不一致”的原版客户端机制。
>
> 基线：Pokémon Bank `00040000000C9B00`，内部 v1.5，解压 `.code` SHA-256 `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`。

## 1. 结论

这次静态分析已经把“Trainer mismatch”从泛化的 Trainer ID 比较收敛成**事务恢复记录不匹配**：

```text
服务器 pending BankTransactionParam
        │
        ├─ dataId:u64
        ├─ curVersion:u32
        ├─ updateVersion:u32
        ├─ size:u32
        └─ transactionPassword:u64
        │
        ▼
state 18 @ 0x002A8760
        │
        ├─ 优先比较 Bank 本地 persistent recovery record
        │     dataId + curVersion
        │
        └─ 再比较当前联动游戏 save 内 recovery record
              dataId + curVersion
              │
              ├─ match + status=2 -> Commit
              ├─ match + status=1 -> Rollback
              └─ mismatch/未知状态 -> case 8/9 错误提示
```

因此 Nintendo UI 最终显示“训练家不一致/Trainer ID Error”，**并不代表主判定条件就是 Pokémon 的 OT/TID 或游戏普通 Trainer ID**。真正决定能否继续自动恢复的核心条件，在当前 v1.5 客户端中是：

```text
remote pending transaction.dataId == persisted recovery.dataId
&&
remote pending transaction.curVersion == persisted recovery.curVersion
```

Trainer 名称/ID 更像是错误提示中用于告诉用户“上一次对应哪份游戏”的展示 metadata。

## 2. 原版保存如何提前写 recovery record

### 2.1 `0x002B1CF8 BankSaveState_Update`

保存开始仍是：

```text
case 1  Serialize + Prepare/Stage
case 2  wait remote upload/stage callback
case 3  写游戏侧 recovery record，然后保存 game main
case 4  wait game save
```

关键是 **case 3 发生在最终 `CompleteUpdateBankObject` 之前**。

### 2.2 游戏侧 recovery record

case 3 取得 active game model：

```text
0x00233A6C  active game model
```

然后按代际选择 recovery-record 对象：

```text
Gen6       model + 0x1ADF8
SM         model + 0xB1394
USUM       model + 0xB4570
```

调用对象 vtable `+0x0C` 后得到真正记录指针。

逻辑布局由写入代码直接确认：

```text
GameRecoveryRecord
+0x00  dataId                u64
+0x08  transactionPassword   u64
+0x10  curVersion            u32
+0x14  updateVersion         u32
+0x18  size                  u32
+0x1C  status                u8
```

case 3 写入：

```text
status = 2
```

随后调用游戏 family 的保存 writer 并真正保存 `main`。

这说明：即使用户在 Bank UI 中完全没有移动游戏盒子里的 Pokémon，只要执行一次 Bank 保存，原版依然可能为了事务恢复而写游戏 `main` 中的 recovery bookkeeping。

## 3. game save 成功后还有第二份 Bank-local recovery record

`BankSaveState_Update` case 5 只在 game save 成功后执行。

对象位置：

```text
*(flow + 0x74)
```

setters：

```text
0x001D4D84  status
0x001D4D6C  dataId
0x001D4D78  transactionPassword
0x001D4D60  curVersion
0x001D4D54  updateVersion
0x001D4D48  size
```

getter 反向确认的底层布局：

```text
LocalRecoveryRecord underlying storage
+0x08  dataId                u64
+0x10  transactionPassword   u64
+0x18  curVersion            u32
+0x1C  updateVersion         u32
+0x20  size                  u32
+0x24  status                u8
```

正常 game save 成功路径写：

```text
status = 2  -> 后续应 Commit
```

若 game save 失败，case 7 写：

```text
status = 1  -> 后续应 Rollback
```

然后才执行对应的远端 Complete/Rollback。

## 4. 正常完成后的清理

正常 Commit 成功后，`BankSaveState_Update` case `0x0D` 会重新取得游戏侧 recovery record，并执行：

```text
record +0x08 transactionPassword low  = 0
record +0x0C transactionPassword high = 0
```

随后再次保存游戏。

这说明 `transactionPassword != 0` 本身就是原版识别“游戏里还有未结束事务上下文”的重要信号。

## 5. state 17：只有游戏 recovery record 时也能恢复

### `0x002A93F4`

state 17 读取与保存阶段相同的 family-specific game recovery record。

若：

```text
transactionPassword != 0
```

则把整份记录拷入状态对象，并依据：

```text
status == 1 -> BankRemote_RollbackStagedUpdate
status == 2 -> BankRemote_CommitStagedUpdate
```

远端操作成功以后，再清除游戏 record 的 transactionPassword 并保存游戏。

因此原版设计本身就考虑了“程序/网络中断，下次靠游戏存档继续事务”的恢复场景。

## 6. state 18：真正的 mismatch gate

### `0x002A8760`

这是本次研究最关键的函数。

### 6.1 先尝试 Bank-local recovery record

case 3：

```text
local.dataId == serverTx.dataId
&&
local.curVersion == serverTx.curVersion
```

命中后读取：

```text
transactionPassword
updateVersion
size
status
```

并：

```text
status == 1 -> case 6 Rollback
status == 2 -> case 5 Commit
其它        -> fallback 到 game record 检查
```

### 6.2 再尝试当前游戏 recovery record

case 4：

```c
server = *(BankTransactionParam **)(state + 0x28);
game   = ActiveGameRecoveryRecord();

if (server->dataId == game->dataId &&
    server->curVersion == game->curVersion) {
    // copy transaction context
    if (game->status == 1) rollback;
    else if (game->status == 2) commit;
    else mismatch;
}
else {
    mismatch;
}
```

从反编译对应的原始判断可直接看到三项比较：

```text
server[0] == game[0]   dataId low
server[1] == game[1]   dataId high
server[2] == game[4]   curVersion
```

**没有在这个 gate 中直接比较游戏 Trainer ID。**

## 7. mismatch 后为什么 UI 显示“训练家”

state 18 case 1 会针对 server `dataId` 调：

```text
BankRemote_QueryMetadata
```

其 callback 邻域 `0x002A8D30` 会解析服务器返回的小型 metadata。

当 payload 长度为 `0x1E` 时，它解析：

```text
26 bytes  -> state +0x66  UTF-16 名称类字段
1 byte    -> state +0x65  属性/性别类字段
u16       -> state +0x80  ID 类字段
```

case 9 再把这些字段格式化到错误 UI，并显示 message id `10`。

所以：

```text
事务记录 mismatch
       ↓
恢复方向无法安全判定
       ↓
客户端展示服务器 metadata 中的上次训练家信息
       ↓
用户看到“Trainer ID / 训练家不一致”
```

这解释了为什么错误名称看起来像“Trainer ID 检查”，但底层 blocking predicate 实际是 transaction recovery identity/version。

## 8. 为什么同一份未恢复存档仍能触发

不需要 JKSM restore。

一个足以产生该状态的窗口是：

```text
Prepare/Stage 在服务器建立 pending transaction T1
          ↓
网络故障/请求异常
          ↓
服务器仍保留 T1
          ↓
游戏 recovery record 尚未来得及写成 T1
或 Bank-local recovery record 尚未来得及持久化 T1
          ↓
下次启动 state18
          ↓
server = T1
local/game = old T0 / empty
          ↓
dataId 或 curVersion 不一致
          ↓
case8/9 Trainer mismatch
```

另一个需要实机故障注入继续区分的窗口，是远端 rollback/cleanup 与本地清理先后不一致。

但无论是哪一个窗口，都已经可以确定：

> “用户未恢复存档”并不能保证 recovery record 与 server pending transaction 一致，因为二者由不同介质、不同异步步骤持久化。

## 9. Official Bulk Sync 在这里扮演什么角色

当前 V3 仅修改 runtime BankObject，未 Hook：

```text
BankSaveState_Update
PrepareUpdate
Game Save
Complete
Rollback
```

因此它不是直接制造 mismatch 的 compare。

它的关系是：

```text
bulk_import.bin
 -> runtime BankObject 有变化
 -> 用户需要执行 stock Bank save transaction
 -> 网络若在 recovery-record/remote-transaction 的窄窗口失败
 -> 暴露原版 recovery mismatch gate
```

正常网络下能稳定保存成功，与这个机制完全兼容。

## 10. 为什么不能直接把 case 4 比较 NOP

如果无条件把：

```text
dataId/curVersion mismatch -> error
```

改成：

```text
always match
```

后续 case 5/6 会直接调用 stock：

```text
BankRemote_CommitStagedUpdate
BankRemote_RollbackStagedUpdate
```

而这两个调用需要一套**彼此匹配的 transactionPassword/dataId/version**。

错误地从旧 game record 拼出 transaction context，可能造成：

- 对错误 transaction Complete；
- 对错误 transaction Rollback；
- 409/协议错误；
- 更糟时破坏 Game ↔ Bank 的防复制事务语义。

因此实验 Hook 的正确目标不是“永久 TrainerCheck=true”，而是：

1. 先确认当前确实处于 incomplete transaction recovery；
2. 确认这次事务是本工具产生的 bulk-only session；
3. 对 mismatch 场景优先考虑**安全 Rollback**，而不是盲目 Commit；
4. 保留正常手动 Game ↔ Bank 操作的原版 gate。

## 11. 当前地址表

| 地址 | 暂定命名/作用 | 状态 |
|---:|---|---|
| `0x002B1CF8` | `BankSaveState_Update` | 已确认完整事务状态机 |
| `0x002A93F4` | game-record recovery | 已确认 status 1 rollback / 2 commit |
| `0x002A8760` | local/game recovery + mismatch gate | **已确认核心比较** |
| `0x002A8D30` | recovery metadata callback | 已确认 UI metadata parse |
| `0x001D4D84` | local recovery status setter | 已确认 |
| `0x001D4D6C` | local recovery dataId setter | 已确认 |
| `0x001D4D78` | local recovery transactionPassword setter | 已确认 |
| `0x001D4D60` | local recovery curVersion setter | 已确认 |
| `0x001D4D54` | local recovery updateVersion setter | 已确认 |
| `0x001D4D48` | local recovery size setter | 已确认 |
| `0x002CB908` | local recovery dataId getter | 已确认 |
| `0x002CB8DC` | local recovery transactionPassword getter | 已确认 |
| `0x002CB8D0` | local recovery curVersion getter | 已确认 |
| `0x002CB8C4` | local recovery updateVersion getter | 已确认 |
| `0x002CB8E8` | local recovery size getter | 已确认 |
| `0x002CB8A8` | local recovery status getter | 已确认 |
| `0x002A9118` | save-error UI state | 已确认，不是 mismatch compare 本体 |
| `0x002AD7BC` | `FUN_002AD724` 内部地址 | 已纠正文档：不是独立函数头 |

## 12. 下一步机器码级工作

静态伪代码已足以证明 predicate 和恢复动作，但要生成可验证 IPS 仍需要 stock `.code` 的实际 ARM 指令：

1. 定位 `0x002A8760` case 4 中三项 compare 对应的精确 `CMP/BNE`；
2. 确认是否存在比直接分支 patch 更窄的 probe 注入点；
3. 建立 patch whitelist；
4. 保证正常 state18 匹配路径逐字节保持 stock；
5. 第一版只做 diagnostic/recovery-only 实验，不默认发布永久 bypass。
