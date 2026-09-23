# Pokémon Bank 官方 Bulk Sync Recovery B：生产实现状态

日期：2026-09-23

## 目标

Recovery B 只服务于 `bulk_import.bin` 实际成功应用后的官方 Bank 保存事务。它优先保留已经安全完成的 game save：

- 没有 durable game `status=2` 证据 -> Rollback
- 有与 server pending transaction 匹配的 durable game `status=2` -> Commit

普通 Pokémon Bank 保存保持 stock 语义。

## pre-RMC52 私有 WAL

Bulk Apply 成功后设置 runtime session flag `0x003ABFFC=1`。Bank v1.5 stock 映像该 4-byte 区域为全零，verifier 会硬校验。

保存进入 case1 `0x002B1DE4` 后，Bulk 会话先经 stock case7/case8 的本地保存流程，把当前完整 `BankTransactionParam` 持久化为私有 `status=3` WAL；只有 WAL 成功才允许继续 Stage/RMC52。

`state+0x28` 在 `0x002B2494` 已经作为完整事务参数传给 `BankRemote_StageFileUpdate @ 0x002B24A0`，所以这个 write-ahead journal 覆盖了“server pending 已建立而 game/local recovery 尚未落盘”的危险窗口。

WAL 保存失败时直接转 state20，不向服务器创建 pending transaction。

## 为什么使用 status=3

`status=3` 只表示 Recovery B 的 durable fallback，不直接代表 Commit/Retry。

state18 中，stock 首先已经完成 local `dataId + curVersion` 匹配并把 `state+0x88` 清零。B 仅当 local status=3 时继续核对：

- `updateVersion`
- `size`
- `transactionPassword` low/high

只有这些字段与当前 server pending transaction 全部一致，才设置 `state+0x88=2`，表示存在可信的 Rollback fallback，并进入 stock game recovery 检查。

## game recovery 决策

### game recovery 完整匹配

stock 会把 `state+0x88` 改为 1，并读取 game recovery status：

- `status=1` -> stock Rollback
- `status=2` -> stock Commit
- 其它 status -> 原版 Trainer/save mismatch

因此 game save 已真正持久化成功时，原版 game `status=2` 是 Commit 的 durable evidence。

### game dataId / curVersion 不匹配

这两条真实 mismatch branch：

```asm
0x002A89D0 BNE 0x002A8AD0
0x002A89E0 BNE 0x002A8AD0
```

被定向到 in-place decision block。如果 `state+0x88==2`，说明刚才已经验证了 exact private WAL，但不存在匹配的 durable game record，因此选择 stock state6 Rollback；否则保持 stock state8 Trainer/save mismatch。

### game record 匹配但 status 异常

此时 stock 已把 `state+0x88` 改成 1，因此不会被 B 当作 WAL fallback，仍走 stock mismatch。这避免了“只要有 status=3 就强制 Rollback/Commit”的错误放行。

## smart 行为为什么成立

- Stage 后、game save 前中断：local status=3，game 不匹配 -> Rollback。
- game save 成功后：stock game recovery status=2；随后 stock case5 会把 local recovery 正常覆盖成 status=2 -> Commit。
- 如果 case5 尚未来得及覆盖，但 game status=2 已 durable：B 仍先检查 game record，因此 Commit。
- server tx 与 WAL 任一扩展字段不一致：不认领该事务，回到 stock game check/mismatch。

## 生产 Hook

- `0x002AF460`：Official Bulk state16 dispatcher
- `0x002B1DE4`：pre-RMC52 WAL entry
- `0x002B1FFC`：private status=3 selector，仅 WAL pass
- `0x002B2090`：WAL save result
- `0x002A8968`：local private WAL full-field validation
- `0x002A89D0`：game dataId mismatch edge
- `0x002A89E0`：game curVersion mismatch edge
- `0x002A8A64..0x002A8A7C`：复用 stock 冗余 block 作为 Rollback-vs-mismatch 决策，不额外占 tail

## 空间

当前生产 packing 非常紧：

- ARM dispatcher：36 bytes
- Recovery B WAL Thumb：约 160 bytes
- Official Bulk payload：约 1577 bytes
- 合计约 1773 / 1776 bytes

只剩约 3 bytes，因此后续不要再往 RX tail 增加日志/文件 IO。需要新增诊断时应优先使用现有 stock 状态字段、构建期验证或另行设计安全 code placement。

## 故障矩阵

| 故障位置 | local | game | server | 恢复 |
|---|---|---|---|---|
| pre-WAL 保存失败 | 无新 WAL | unchanged | 无 pending | 不发 Stage |
| WAL 后、Stage 前崩溃 | status=3 | unchanged | 无 pending | 无 server tx，不自动提交 |
| Stage 后、game save 前 | status=3 | old/mismatch | pending | Rollback |
| game save 过程中断 | status=3 | 无可靠 status=2 | pending | Rollback |
| game recovery status=2 已落盘、case5 前中断 | status=3 | exact status=2 | pending | Commit |
| case5 local status=2 后、Complete 前断网 | status=2 | exact status=2 | pending | stock Commit |
| server tx 与 status=3 WAL 全字段不一致 | stale/foreign | 任意 | different pending | 不认领，stock mismatch/check |
| game exact 但 recovery status 异常 | exact local WAL | exact invalid game status | pending | stock mismatch |

## 构建安全门

- stock `.code` size `0x2AC000`
- SHA-256 `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`
- Hook 原 bytes 精确匹配
- `0x003ABFFC..0x003ABFFF == 00 00 00 00`
- patched data/BSS 映像不变
- WAL / Bulk symbols 必须全部落在 RX tail
- IPS replay 必须完全重建 patched `.code`

当前分支 CI 与 armips smoke 已通过。下一阶段重点是实机 fault-injection：分别在人为断网的 Stage、game-save、Complete 窗口验证 A/B 的恢复结果和 Bank 服务器最终状态。
