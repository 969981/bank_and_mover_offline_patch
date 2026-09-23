# Official Bank Recovery B 智能 Commit/Rollback 实机验证指南

> 分支：`feature/official-bank-recovery-smart`
>
> 状态：`EXPERIMENTAL / HOST VERIFIED / IPS HOOK NOT YET EMITTED`

## 1. 目标

Variant B 在 exact tool-owned transaction 的前提下，根据已确认保存阶段选择恢复方向：

```text
TX_BOUND                 -> Rollback
GAME_SAVE_STARTED        -> Rollback
GAME_SAVE_OK             -> Commit
REMOTE_COMPLETE_STARTED  -> Commit
```

`DONE` 但服务器仍报告同一 transaction pending 属于矛盾状态，保持 BLOCK，不猜测 Commit。

## 2. 当前已自动化验证

GitHub Actions `official-bank-recovery-b-ci` 覆盖：

- 48-byte staged OBRX marker v2；
- pending -> TX_BOUND 的真实 transaction bind；
- stage 单调逐级前进、禁止回退/跨级；
- smart Commit/Rollback policy；
- marker exact transaction match；
- persistence contract；
- runtime-neutral stage lifecycle 与 status=1/2 recovery record 重建；
- stock recovery model regression；
- Official Bulk Sync core regression。

## 3. A/B 对照故障窗口

### B0 Prepare 前失败

marker 未绑定真实 transaction。

预期：不自动 Commit/Rollback，保持 stock。

### B1 TX_BOUND 后、game save 开始前失败

预期：

```text
Rollback
```

与 Variant A 相同。

### B2 GAME_SAVE_STARTED 后、成功 callback 前失败

预期：

```text
Rollback
```

因为没有正证据证明游戏 `main` 已持久化成功。

### B3 GAME_SAVE_OK 后、Complete 前网络失败

预期：

```text
Commit
```

这是 B 与 A 的核心差异：

- A：放弃 staged Bank 更新并 Rollback；
- B：保留已确认 game-save 成功对应的 staged Bank 更新并 Complete。

### B4 REMOTE_COMPLETE_STARTED 后通信结果未知

若下一次服务器仍明确返回同一 pending transaction，marker exact match：

```text
Commit
```

若服务器已无 pending：

```text
LOCAL_CLEANUP
```

不得再次发送重复 Commit。

### B5 DONE + server 仍 pending

这是矛盾状态：

```text
BLOCK
```

不得根据 DONE 猜测服务器实际状态。

## 4. 每次实机实验需要记录

```text
故障注入时点
marker stage
profile
dataId
transactionPassword
curVersion
updateVersion
size
server pStatus / pApplicationId（若可获取）
stock local/game record 是否 match
B 选择的 action
Commit/Rollback 返回结果
下一次能否进入 Bank UI
BankObject 是否保留本次 bulk 结果
游戏 main 是否保持一致
```

## 5. A/B 评价指标

对同一类网络故障分别跑 A/B：

| 指标 | A | B |
|---|---|---|
| 是否解除 mismatch 锁 | 应是 | 应是 |
| game save 未确认时 | Rollback | Rollback |
| game save 已确认成功时 | Rollback | Commit |
| 是否保留本次 bulk 更新 | 否 | GAME_SAVE_OK 后应保留 |
| 恢复逻辑复杂度 | 低 | 高 |

## 6. 当前机器码阻塞项

B 比 A 多三个必须精确定位的 Hook 时点：

```text
GAME_SAVE_STARTED
GAME_SAVE_OK callback
REMOTE_COMPLETE_STARTED
```

此外仍需要：

```text
state7 TX_BOUND
state18 mismatch edge
remote resolved cleanup
```

所有位点必须基于以下 stock `.code` 验证原始 ARM bytes：

```text
size   = 0x2AC000
SHA256 = 2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

在精确 bytes 未取得前，不生成可安装 IPS。
