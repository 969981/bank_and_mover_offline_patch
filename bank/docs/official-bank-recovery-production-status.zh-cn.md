# Pokémon Bank 官方 Bulk Sync Recovery A：生产实现状态

日期：2026-09-23

## 目标

Recovery A 只服务于 `bulk_import.bin` 实际成功应用后的官方 Bank 保存事务。它的原则是：只要本次 Bulk 保存未完整结束，下一次恢复时始终优先 Rollback，不尝试保留这次远端更新。

普通 Pokémon Bank 保存不改变原版事务语义。

## 根因模型

原版保存流程在远端 Stage/RMC52 之前，`state+0x28` 已经持有完整 `BankTransactionParam`：

- `dataId`
- `curVersion`
- `updateVersion`
- `size`
- `transactionPassword`

`0x002B2494` 将 `state+0x28` 装入 `r3`，`0x002B24A0` 调用 `BankRemote_StageFileUpdate`。因此服务器可能建立 pending transaction 的危险窗口开始于 Stage，而 stock game/local recovery 尚未必已经持久化。

## Recovery A write-ahead journal

Bulk Apply 成功后，运行时字节 `0x003ABFFC` 置 1。Bank v1.5 stock 映像中 `0x003ABFFC..0x003ABFFF` 为全零，构建 verifier 将其作为版本合同校验。

保存进入 stock case1 (`0x002B1DE4`) 时：

1. 普通会话：flag != 1，完全 stock。
2. Bulk 会话：先转入 stock case7/case8，本地持久化当前 exact transaction，使用 native `status=1`。
3. WAL 本地保存失败：转 state20，绝不发 RMC52。
4. WAL 成功：重新回 case1，再执行原版 SerializeAndStage。

这样服务器 pending transaction 一旦可能存在，本地已经有一个原版 state18 能识别的 exact Rollback record。

## 永远 Rollback 的关键修正

stock game save 成功后，case5 `0x002B1F50` 原指令：

```asm
MOV r1,#2
```

会把 local recovery 升级为 Commit 状态。Recovery A 现在 Hook 此处：

- Bulk session：写 `status=1`，随后清 session flag；
- 普通 Bank：保持 `status=2`。

因此即使游戏 main 已经成功保存、网络随后在 Complete 阶段失败，A 下次仍使用 stock state18 的 Rollback 路径。

如果 game save 失败，则 stock case7 本身写 `status=1`；case8 helper 会清理仍存活的 Bulk session flag。

## state18

A 不修改 state18。

原版 state18 对 local recovery 做 `dataId + curVersion` 验证并依据：

- `status=1` -> Rollback
- `status=2` -> Commit

Recovery A 全程只生成 native `status=1` 的 Bulk recovery，所以无需 Trainer mismatch bypass，也不需要伪造 transactionPassword。

## 生产 Hook

- `0x002AF460`：Official Bulk Sync state16 dispatcher
- `0x002B1DE4`：pre-RMC52 WAL entry
- `0x002B1F50`：Bulk-only rollback status selector
- `0x002B2090`：WAL/local-save result handler

state18、case7 status 指令保持 stock。

## 空间

当前 CI 实测：

- Official Bulk Thumb payload：1557 bytes
- Recovery A WAL Thumb：112 bytes
- ARM dispatcher：36 bytes
- 合计约 1705 / 1776 bytes

仍保留约 71 bytes RX-tail 余量。

## 故障矩阵

| 故障位置 | durable record | 服务器可能状态 | 下次行为 |
|---|---|---|---|
| pre-WAL 保存失败 | 无新 WAL | 尚未 Stage | 不会产生 server pending |
| WAL 成功、Stage 前崩溃 | status=1 | 无 pending | server 无 pending，正常清理/忽略旧记录 |
| Stage/RMC52 后、game save 前断网 | status=1 | pending | stock state18 Rollback |
| game save 进行中断电 | status=1 | pending | stock state18 Rollback |
| game save 成功、local case5 保存前断电 | pre-WAL status=1 | pending | stock state18 Rollback |
| case5 local save 成功、Complete 前断网 | status=1 | pending | stock state18 Rollback |
| Complete 成功 | status=1 可能残留但 server 无 pending | committed | 不再存在待恢复 server tx |

## 构建安全门

构建和 smoke test 要求：

- stock `.code` size `0x2AC000`
- SHA-256 `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`
- Hook 原始 bytes 精确匹配
- `0x003ABFFC..0x003ABFFF == 00 00 00 00`
- 所有新增可执行代码位于 `0x00313910..0x00314000`
- patched data/BSS 映像不得变化
- IPS replay 必须等于 patched `.code`

当前分支 CI 与 armips smoke 已通过。实机下一阶段应做按故障窗口断网/断电的 fault-injection，而不是继续扩大 Hook 范围。
