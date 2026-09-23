# Pokémon Bank Trainer mismatch / 异常事务恢复研究

> 分支：`feature/official-bank-recovery-research`
>
> 基线：从 `feature/official-bank-bulk-sync` 派生。研究现象：Official Bulk Sync 正常情况下可以成功保存；若保存过程中发生网络故障，下一次仍使用同一份、未通过 JKSM 恢复且未人工修改的游戏存档联动 Bank，客户端有时会提示训练家/存档不一致并阻止继续。

详细地址与伪代码见：[`official-bank-recovery-address-map.zh-cn.md`](./official-bank-recovery-address-map.zh-cn.md)。

## 1. 已闭环的核心结论

本次静态分析已经确认：**Trainer mismatch 的核心 gate 不是普通 Pokémon OT/TID 比较，也不是简单比较 BankObject 的 source-game trainer record，而是服务器 pending transaction 与本地/游戏 recovery record 的事务身份比较。**

关键函数：

```text
0x002B1CF8  BankSaveState_Update
0x002A93F4  game recovery
0x002A8760  local/game recovery + mismatch gate
0x002A8D30  recovery metadata callback / error display data
```

state 18 `0x002A8760` 的核心条件已经从原版 Ghidra 导出闭环：

```text
serverTx.dataId == recoveryRecord.dataId
&&
serverTx.curVersion == recoveryRecord.curVersion
```

若 Bank-local recovery record 不匹配，客户端会再检查当前联动游戏保存的 recovery record；若仍不匹配，就进入 case 8/9 的错误提示路径。

命中后，record 的：

```text
status == 1 -> RollbackBankObject
status == 2 -> Complete/Commit BankObject
```

决定恢复方向。

## 2. 游戏里真正保存的 recovery record

原版 `BankSaveState_Update` 在服务器 Stage/Upload 成功后、最终 Complete 之前，先把当前 `BankTransactionParam` 写入游戏 save model：

```text
GameRecoveryRecord
+0x00  dataId                u64
+0x08  transactionPassword   u64
+0x10  curVersion            u32
+0x14  updateVersion         u32
+0x18  size                  u32
+0x1C  status                u8
```

family-specific runtime object：

```text
Gen6   model + 0x1ADF8
SM     model + 0xB1394
USUM   model + 0xB4570
```

保存正常准备提交时：

```text
status = 2
```

随后原版真正保存游戏 `main`。

所以：

> “用户没有修改游戏 Pokémon、也没有 JKSM restore”并不等于“Bank 没有修改游戏 save”。

Bank 为跨 Game ↔ Server 事务恢复而写入了独立 recovery bookkeeping。

## 3. Bank 本地还有第二份 recovery record

游戏保存成功后，stock Bank 再把同一个 transaction 写到自己的 persistent local record：

```text
LocalRecoveryRecord
+0x08  dataId                u64
+0x10  transactionPassword   u64
+0x18  curVersion            u32
+0x1C  updateVersion         u32
+0x20  size                  u32
+0x24  status                u8
```

保存方向：

```text
game save success -> status 2 -> Commit

game save failure -> status 1 -> Rollback
```

因此原版实际上用两份本地证据帮助下一次启动恢复：

```text
Bank-local recovery record
+
Game-save recovery record
```

## 4. 为什么网络失败后同一份 save 仍能 mismatch

现在不再需要假设用户回档。

一个完全符合原版代码的窗口是：

```text
Server Prepare/Stage 创建 pending transaction T1
          ↓
网络/请求异常
          ↓
Server 仍保留 T1
          ↓
Game recovery record 尚未成功持久化 T1
并且/或者 Bank-local record 尚未成功持久化 T1
          ↓
下次启动 state 18
          ↓
server = T1
local/game = T0 或空记录
          ↓
dataId / curVersion mismatch
          ↓
Trainer mismatch block
```

另一个需要实机故障注入区分的窗口，是 remote rollback/cleanup 与 local/game cleanup 的先后不同步。

无论具体是哪一个网络窗口，**“same physical save”不能保证 transaction record 一致**，因为服务器和两个本地介质由不同异步步骤更新。

## 5. 为什么错误信息会显示 Trainer ID

state 18 在恢复过程中还会针对 server `dataId` 请求小型 metadata。

`0x002A8D30` 对 `0x1E` 字节返回体解析出：

```text
26 bytes  名称类字段
1 byte    属性/性别类字段
u16       ID 类字段
```

随后 case 9 把这些信息格式化进错误 UI。

所以“Trainer ID Error”是**错误提示语义**；它帮助用户识别上次会话关联的游戏，但不等于 blocking predicate 本身就是 Trainer ID。

## 6. 对早期假设的修正

### 6.1 `0xAD61C` source-game records

BankObject 的 `8 × 0x44` source-game records 确实含 name/sex/trainer_id/stats，仍然是 BankObject 有意义的 metadata。

但目前已找到的 state18 mismatch 核心 gate **没有用它直接决定 match/mismatch**。因此它从“首要根因候选”降级为辅助 metadata/后续研究项。

### 6.2 Gen6 公共 0x20 Bank application data

早期把它抽象成 counter/link block 是有启发性的，但 Bank CIA 已经提供了更准确的 runtime 事务记录结构：`dataId + transactionPassword + curVersion + updateVersion + size + status`。

后续文档以 CIA 静态代码确认的结构为主，不再把未知 counter 语义当作根因结论。

### 6.3 `0x002AD7BC`

自动函数提取器确认它不是独立函数头，而位于 `FUN_002AD724` 内部。旧文档把它直接标成一个独立“state23 forced rollback/recovery update function”过于粗糙；新地址图将“状态入口地址”和“真实函数首地址”分开记录。

## 7. Official Bulk Sync 的责任边界

当前 V3：

```text
只修改 runtime BankObject
不直接写 game main
不 Hook Prepare/Complete/Rollback
不接管 transactionPassword/version
```

因此 Bulk Sync 并没有实现错误的 Trainer compare。

它和问题的关系是：

```text
bulk_import.bin 改变 BankObject
 -> 用户触发一次 stock save transaction
 -> 正常网络：保存成功
 -> 网络在 recovery-record / server-transaction 窄窗口失败：暴露 stock mismatch gate
```

这正好解释“通常成功、偶发网络失败后被锁”的实机表现。

## 8. 为什么不能直接 NOP mismatch

state 18 在 match 后会拿 recovery record 中的：

```text
transactionPassword
dataId
curVersion
updateVersion
size
status
```

继续调用 stock Commit 或 Rollback。

如果把 dataId/curVersion compare 无条件改成成功，却继续使用一份旧/不匹配 record 的 password/version，会把客户端送入错误 transaction context。

因此研究分支遵循：

- 不永久 `TrainerCheck = true`；
- 不默认伪造 transactionPassword；
- 不绕开 stock Complete/Rollback；
- 第一版实验必须 recovery-only；
- mismatch 场景如果能证明属于本工具 bulk-only session，**优先研究受控 Rollback，而不是盲目 Commit**。

## 9. 已加入的开发设施

### 静态提取器

```text
bank/tools/extract_recovery_chain.py
bank/tools/test_extract_recovery_chain.py
bank/tools/recovery_targets.txt
```

支持：

- 精确函数地址；
- 函数内部地址自动解析到 containing function；
- 直接 callee 列表；
- CI 生成完整 recovery-chain artifact。

### stock recovery decision model

```text
bank/src/official_recovery_probe.h
bank/src/official_recovery_probe_core.c
bank/src/official_recovery_probe_host_test.c
```

把 `state18` 已确认的行为固定为 host-testable model：

```text
LOCAL match + status 1 -> ROLLBACK
LOCAL match + status 2 -> COMMIT
LOCAL 无有效方向       -> fallback GAME
GAME match + status 1  -> ROLLBACK
GAME match + status 2  -> COMMIT
否则                   -> BLOCK
```

这个模块目前不改变实机 patch，只作为后续实验 Hook 的事实合同。

## 10. 下一步

1. 对 stock `.code` 做机器码级反汇编，定位 state18 case4 的精确 `CMP/BNE` 地址；
2. 设计一个**独立实验 build**，不污染 normal V3；
3. 优先做 diagnostic/probe，验证绕过 local gate 后 server 是否允许 stock recovery；
4. 为 Bulk Apply 增加可验证的 session marker，使“bulk-only pending transaction”能够与普通手动 Game ↔ Bank 操作区分；
5. 只有在能证明 transaction 属于 bulk-only session 时，才研究 mismatch 时的受控 forced rollback；
6. 做真实设备网络故障矩阵，记录 server pStatus/dataId/curVersion 与 local/game record 的组合。
