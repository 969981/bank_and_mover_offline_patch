# Official Bank Recovery B：智能 Commit / Rollback 实机验证指南

> 分支：`feature/official-bank-recovery-smart`
>
> 状态：`EXPERIMENTAL / CIA + MACHINE-CODE + CI VERIFIED / HARDWARE FAULT TEST PENDING`

## 1. 目标

B 同样先消灭“server pending 已存在、但本地/游戏都没有 durable recovery record”的锁死窗口；与 A 不同的是，B 会利用 **游戏存档中已经持久化的 stock `status=2` recovery record** 作为 Commit 正证据，尽量保留已经成功完成游戏保存的 Bulk transaction。

核心：

```text
Stage 前：Bank-local exact tx -> status=1 -> 持久化
        ↓
服务器才能建立 pending
        ↓
游戏 main 保存时：stock GameRecoveryRecord -> status=2
        ↓
游戏保存成功后：stock local record 最终也可升级 status=2
```

restart 恢复时：

```text
local exact status=2
    -> stock Commit

local exact status=1
    -> 继续检查 game recovery
       ├─ game exact status=2 -> Commit
       ├─ game dataId/version mismatch -> Rollback
       └─ game status 异常 -> 保留 stock error

local 本身不 exact
    -> 不使用我们的 fallback，保留 stock game validation / mismatch
```

## 2. 为什么不再使用外置 OBRX marker

早期设计用 `/3ds/Bank/...` marker 记录 `TX_BOUND / GAME_SAVE_OK / COMPLETE_STARTED`。

CIA 级分析后发现没有必要：Bank 原版已经维护两份持久恢复记录：

- Bank-local RecoveryRecord；
- GameRecoveryRecord。

而 `BankTransactionParam` 在 `0x002B24A0` 发 RMC52 之前已经完整存在。因此最可靠的 journal 就是 **stock local RecoveryRecord 本身**，不需要额外文件、checksum、SD 文件生命周期或额外 FS Hook。

旧 marker 纯函数/host tests 保留为研究回归，但 production B 不依赖它们。

## 3. Pre-Stage write-ahead journal

和 A 一样，B Hook：

```text
0x002B1DE4  save case1
0x002B2090  case8 local-save result
```

先复用原版 case7：

```text
state+0x28 exact BankTransactionParam
    ↓
Bank-local RecoveryRecord
status = 1
    ↓
stock local save
    ↓
确认成功后才真正调用 BankSave_SerializeAndStage / RMC52
```

这意味着：服务器只要可能出现 pending，本地就一定先有同一 transaction 的 durable rollback fallback。

## 4. 智能 Commit 判定

B 保留 stock case5 的：

```asm
0x002B1F50  MOV r1,#2
```

因此正常 game save 成功后，本地 recovery 最终会升级为 status=2。

更关键的是窄窗口：

```text
game main 已保存成功（GameRecoveryRecord status=2）
但 case5 local status=2 尚未持久化
```

此时 local 仍是 pre-journal status=1。原版 state18 会立即 Rollback，无法利用 game status=2。

B 修改 state18：local exact status1 时先检查 game record。

### 4.1 local exact status1

原版 local status decision：

```text
0x002A8968
```

B 将 exact `status=1` 标记为 `state+0x88=2`，然后进入原版 game check `0x002A8988`。

### 4.2 game exact status2

原版 game check 自己会验证：

```text
dataId 64-bit
curVersion
status
```

exact + `status=2` 后直接走 stock Commit；B 不伪造 tx、不修改 transactionPassword。

### 4.3 game mismatch

真实两个 mismatch branch：

```asm
0x002A89D0  BNE  ; dataId mismatch
0x002A89E0  BNE  ; curVersion mismatch
```

B 只 Hook 这两条，不 Hook 共享 `0x002A8AD0` funnel。

如果 `state+0x88==2`，说明刚才已经验证了一份 exact local status1 journal：

```text
game mismatch -> stock Rollback (substate 6)
```

否则：

```text
game mismatch -> stock substate 8 / Trainer-save mismatch
```

### 4.4 local mismatch

`0x002A8904 / 0x002A891C` 只负责清掉我们的 local-journal flag，再进入 stock game check；因此真实不同存档不会被错误“继承”一次旧的 rollback permission。

## 5. A / B 真正区别

| 场景 | A | B |
|---|---|---|
| Stage 前 | 先持久化 local status1 | 同样 |
| server pending、game 未保存 | Rollback | Rollback |
| game save 已 durable，但 local status2 尚未 durable | **Rollback** | **读取 game status2 后 Commit** |
| local status2 已 durable | A 不允许产生，仍保持 local status1 | stock Commit |
| Complete 成功 | stock cleanup | stock cleanup |
| unrelated mismatch | stock protection | stock protection |

A 修改 `0x002B1F50: status2 -> status1`；B 保留原版 status2。

## 6. Hook / stock bytes

验证基线：

```text
.code size   0x2AC000
SHA-256      2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

关键位点：

```text
0x002B1DE4  pre-journal entry
0x002B1FF8  stock status1 record writer
0x002B2090  local-save result
0x002B2494  tx pointer load
0x002B24A0  Stage/RMC52 call

0x002A8904  local dataId mismatch
0x002A891C  local curVersion mismatch
0x002A8968  local status decision
0x002A8988  stock game check entry
0x002A89D0  game dataId mismatch
0x002A89E0  game curVersion mismatch
0x002A8AC8  stock Commit path
```

## 7. RX tail budget

Production V3 Thumb object：1577 bytes。

B tail 预计：

```text
V3 object       1577
ARM dispatch      36
prejournal        48
journal result    60
local clear       12
game decision     24
--------------------
合计            1757 / 1776
剩余约            19 bytes
```

local-status 0x20-byte rewrite 和两条 BNE replacement 都是原地 patch，不占 tail。

因此 B 已接近 tail 极限，后续不能随意往 tail 加日志字符串或新通用 helper。

## 8. 实机故障矩阵

重点注入：

1. pre-journal 保存前失败：不得发 Stage；
2. Stage 成功、game recovery 未 durable：Rollback；
3. game save 中途失败：Rollback；
4. game main 已 durable、local status2 尚未 durable：**B 应 Commit**；
5. local status2 已 durable、Complete 网络失败：stock Commit；
6. unrelated game/save：保持 stock mismatch。

记录：

```text
server pStatus / pending tx
local recovery dataId/curVersion/status
game recovery dataId/curVersion/status
state+0x88 recovery-source flag
最终 Commit / Rollback
下一次是否能正常进入 Bank
Bulk 更新是否保留
游戏 main 是否仍一致
```

B 的验收标准是：**网络故障不能再制造永久锁；只在存在 durable game status=2 正证据时保留事务，否则安全 Rollback。**
