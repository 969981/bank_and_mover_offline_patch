# Pokémon Bank Trainer mismatch / 异常事务恢复研究

> 分支：`feature/official-bank-recovery-research`
>
> 基线：从 `feature/official-bank-bulk-sync` 派生。目标不是重新实现服务器协议，而是解释并复现实机现象：Official Bulk Sync 正常情况下可保存成功；若保存过程中发生网络故障，下一次仍使用同一份、未通过 JKSM 恢复且未人工修改的游戏存档联动 Bank，客户端有时会提示训练家/存档不一致并阻止继续。

## 1. 已确认边界

1. Official Bulk Sync V3 只在 `0x002AF460 BankDataSyncState_Update` 的普通游戏 full-download 路径修改 runtime `BankObject`；不直接写游戏 `main`。
2. 用户在 Bank UI 保存后仍走原版保存事务：`PrepareUpdateBankObject -> HPP upload -> game/local save -> CompleteUpdateBankObject`；失败走 `RollbackBankObject`。
3. 原版恢复相关状态至少包括：
   - state 8 `0x002ACBDC`：查询远端记录/事务状态；
   - state 11 `0x002AF034`：检查服务器事务并选择恢复路径；
   - state 17 `0x002A93F4`：另一侧事务恢复/重试；
   - state 18 `0x002A8760`：当前用户事务恢复/重试；
   - state 22 `0x002A9118`：保存失败处理；
   - state 23 `0x002AD7BC`：强制回滚/事务恢复；
   - state 7 `0x002B1CF8`：保存、提交和回滚状态机。
4. `GetTransactionParam(slotId)` 返回 `BankTransactionParam + pStatus + pApplicationId`；客户端静态代码至少比较 `pStatus==52` 与 `pStatus==53`，与 `PrepareUpdateBankObject` / `CompleteUpdateBankObject` 方法号对应。
5. BankObject 自身在 `0xAD61C` 起包含 `8 × 0x44` source-game records。当前 Viewer 已按每条 `name[26] + sex:u16 + trainer_id:u32 + stats[9]:u32` 解析。这意味着“训练家不一致”的候选输入不只游戏侧 Bank linkage，也可能包括服务器 BankObject 保存的 per-profile 训练家摘要。

## 2. 当前待验证的根因模型

不预设单一根因，按证据优先级验证以下模型：

### H1：异常事务恢复中的游戏身份校验失败

网络故障发生在 stock save transaction 已推进一部分之后，服务器保留 pending/recovery context；下一次进入 state 11/17/18 时，客户端用当前 active game 的身份与上次事务上下文比较，比较失败后进入 Trainer mismatch 错误路径。

### H2：source-game record 参与身份校验

fresh BankObject 的 `0xAD61C + profile*0x44` source record 含 Trainer ID/Name，可能在 full-download 后与 active game model 比较或同步。若前一次事务失败在 source record 与本地 game-side bookkeeping 的不同阶段，就可能造成同一份游戏存档被判定为不一致。

### H3：游戏侧 Bank application/linkage bookkeeping 参与校验

Gen6 公共存档研究表明 Bank 会维护独立的 application/linkage 数据；即使 Pokémon Box 未改变，Bank save 仍可能写 bookkeeping。需要从 Bank CIA 的 GameSaveAdapter writer/validator 反向确认 Gen6/Gen7 实际 runtime 路径，不能仅依赖 raw `main` 偏移推断。

### H4：客户端 gate 只是表象，服务器也拒绝恢复

即便本地绕过 Trainer mismatch branch，后续 RMC 仍可能因 transactionPassword/version/applicationId 不匹配而拒绝。实验必须区分：

- client-only gate；
- client gate + server validation；
- server transaction 本身仍可由 stock rollback/recovery 完成。

## 3. 研究原则

- 不永久 NOP 正常 Trainer/game identity 校验。
- 不跳过 stock `Prepare/Complete/Rollback` 事务语义。
- 不在尚未确认来源时硬编码 XY/ORAS/SM/USUM raw `main` 偏移。
- 第一阶段先做静态函数提取、调用链和常量分析；第二阶段才做 recovery-only 实验 Hook。
- 实验 Hook 必须只在已确认的异常恢复状态触发；正常 state 10/16/25 与正常保存保持 stock 行为。
- 任一“绕过后可进入 UI”的结果都不能直接等同于“服务器事务已解锁”；必须观察后续 state 与 RMC 结果。

## 4. 目标产物

1. `state 8/11/17/18/22/23/7` 的完整反编译摘录、直接调用关系和候选 identity compare 函数表。
2. `source-game record` 写入/读取/比较函数的地址与数据流。
3. Trainer mismatch 最终错误分支/结果码/消息选择位置。
4. 一个只用于研究的 recovery probe：记录关键状态，或在确认安全条件后只绕过 recovery mismatch gate。
5. host tests、ARM 编译检查、text-cave/patch whitelist 验证。
6. 实机实验矩阵：正常保存、Prepare 前断网、上传中断、game save 后/Complete 前断网、下次 recovery。

## 5. 当前结论状态

截至本文件首次提交：

- “Official Bulk Sync 自己直接写坏 game save”已经排除：当前实现只写 runtime BankObject。
- “用户恢复旧 JKSM 存档导致 mismatch”与当前实机复现不符，排除为本次主因。
- “网络失败恰好落在原版事务恢复窗口”与现象高度一致，但具体比较对象与 branch 地址仍需从 CIA 闭环。
- `0xAD61C` source-game record 包含 Trainer ID 是新的高价值线索，优先追踪。
