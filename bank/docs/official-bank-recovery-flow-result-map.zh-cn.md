# Pokémon Bank state18 → state17 恢复结果转移图

> 本文补充 `official-bank-recovery-address-map.zh-cn.md`，专门记录 `0x002A5580 BankFlow_SelectNextState` 对 recovery 状态结果码的分流，以及它对实验性 forced rollback 的影响。

## 1. `BankFlow_SelectNextState`

原版外层选择函数：

```text
0x002A5580 BankFlow_SelectNextState(flow, currentStateId)
```

它读取：

```text
current state object +0x30 -> result byte
```

并根据 `currentStateId + result` 返回下一 state。

## 2. state18 的结果

`state18 @ 0x002A8760` 内部：

```text
case 0x0B:
    result(+0x30) = 4
    return complete

case 0x0C:
    result(+0x30) = 3
    return complete

case 8:
    某些条件可设置 result = 0x16
```

外层 `BankFlow_SelectNextState` 对 `currentStateId == 18 (0x12)`：

```text
result 3    -> state 20 (0x14)
result 4    -> state 17 (0x11)
result 0x16 -> state 23 (0x17)
```

因此正常 state18 recovery 远端操作成功后：

```text
state18
  result 4
    ↓
state17
```

## 3. state17 会再次读取 GameRecoveryRecord

`state17 @ 0x002A93F4`：

```text
取得 active game family recovery record
    ↓
transactionPassword != 0 ?
    ↓ yes
读取 status
    ↓
status == 1 -> Rollback
status == 2 -> Commit
    ↓
远端成功后清 game transactionPassword
    ↓
再次保存游戏
```

这说明 state18 与 state17 不是可以随意拆开的两段。

## 4. 对 forced rollback 的关键安全约束

不能只在 state18 mismatch 时做：

```text
force Rollback
```

然后照常返回 result 4。

假设当前游戏仍保存：

```text
GameRecoveryRecord.status = 2
transactionPassword != 0
```

则会发生：

```text
state18 强制 Rollback
        ↓ result 4
state17
        ↓
读取 GameRecoveryRecord.status = 2
        ↓
再次调用 Commit
```

这会把一个本来想“安全回滚”的实验改造成 **Rollback → Commit 的冲突序列**。

因此任何 recovery-only forced rollback 至少必须同时满足以下之一：

### 方案 A：同步修正 GameRecoveryRecord

在进入 state17 前，把与目标 transaction 对应的游戏 recovery record 改为：

```text
status = 1
```

并保证其中 `dataId/curVersion/transactionPassword/updateVersion/size` 属于同一 server transaction。

风险：如果 mismatch 的原因正是 game record 不是这次 transaction，就不能简单改 status；还必须重建完整 transaction context。

### 方案 B：成功 Rollback 后清理 GameRecoveryRecord 并跳过 state17

只在确认远端 Rollback 成功以后：

```text
clear game transactionPassword
save game
```

然后让外层进入安全的后续 state，而不是 result 4 → state17。

这更接近“这次 transaction 已经被明确放弃”的语义，但需要准确复制 stock cleanup 顺序。

### 方案 C：不主动 Rollback，只做 Probe

第一版实验只记录：

```text
server tx
local record
game record
```

保留 stock mismatch UI。

这是当前在没有完整 stock `.code` 机器码与实机故障样本之前风险最低的方案。

## 5. 当前推荐顺序

```text
Phase 1  diagnostics / transaction marker
Phase 2  实机确认 mismatch 三方数据
Phase 3  只对可证明 bulk-only 的 transaction 做 recovery
Phase 4  若选择 rollback，必须同时处理 state17 / game record cleanup
```

不要实现：

```text
state18 mismatch -> 直接跳 case6 Rollback -> 保持 result4
```

因为外层结果映射已经证明这不足以构成完整安全恢复。
