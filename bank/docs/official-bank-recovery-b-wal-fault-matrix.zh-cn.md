# Official Bank Recovery B：WAL 故障矩阵

本文记录 `feature/official-bank-recovery-smart` 当前 production 设计。

## 目标

解决官方 Pokémon Bank 保存事务中以下窗口造成的持久锁：

```text
server pending transaction 已建立
        ↓
客户端尚未把对应 transaction recovery record 可靠落盘
        ↓
异常退出 / 网络故障
        ↓
下次 state18 无法证明 Commit 或 Rollback
        ↓
Trainer / save mismatch
```

Recovery B 不再根据“推测故障发生在第几阶段”决定 Commit / Rollback，而是只使用已经持久化的证据。

## Pre-RMC52 WAL

在原版 `BankSaveState_Update` case1 真正执行 `BankSave_SerializeAndStage` / RMC52 之前，先使用原版 Bank-local recovery save 路径写入当前完整 `BankTransactionParam`：

```text
status = 3   // 私有 WAL 状态，仅补丁识别

dataId
curVersion
updateVersion
size
transactionPassword
```

只有本地 WAL 保存成功后才允许真正的 Stage 请求开始。

因此，只要服务器可能已经建立 pending transaction，本地就已经至少存在一份包含 exact transaction 的 durable WAL。

## state18 证据优先级

### 1. 普通 stock local status=2

原版本地 recovery record 已经证明正常保存链推进到 Commit 语义：

```text
local exact + status=2 -> stock Commit
```

### 2. 普通 stock local status=1

保持原版：

```text
local exact + status=1 -> stock Rollback
```

### 3. 私有 local status=3 WAL

原版 state18 已先验证：

```text
dataId
curVersion
```

补丁再验证：

```text
updateVersion
size
transactionPassword low/high
```

只有全部一致，才把该 WAL 标记为可信 Rollback fallback（`state+0x88 = 2`），随后进入原版 game recovery 检查。

### 4. game recovery exact + status=2

说明游戏存档已经持久化到本次 transaction：

```text
game exact + status=2 -> stock Commit
```

因此即使 local 还停留在 pre-Stage status=3，已经成功保存游戏的事务仍可完成 Commit。

### 5. game recovery exact + status=1

保持原版：

```text
game exact + status=1 -> stock Rollback
```

### 6. game recovery mismatch / invalid

若此前已经验证 exact local status=3 WAL：

```text
trusted WAL fallback + no durable game Commit evidence -> stock Rollback
```

否则：

```text
保留 stock state8 Trainer/save mismatch
```

## 故障矩阵

| 故障窗口 | durable local | durable game | 下一次动作 |
|---|---|---|---|
| WAL 保存前失败 | 无新 WAL | 无变化 | 未发送 RMC52，不产生新的 server pending |
| WAL 保存成功，Stage 请求前失败 | status=3 | 无变化 | server 无对应 pending；不会错误 Commit |
| Stage 建立 pending 后、case3 前失败 | status=3 exact | 旧/无 | Rollback |
| case3 写 game record 但 game save 未完成 | status=3 exact | 未可靠持久化 | Rollback |
| game save 成功、local case5 前失败 | status=3 exact | status=2 exact | Commit |
| local case5 保存成功、Complete 前失败 | status=2 exact | status=2 exact | Commit |
| Complete 请求中断、server 仍 pending | status=2 exact | status=2 exact | Commit/recovery |
| server tx 与 status=3 任何扩展字段不符 | stale/foreign | 任意 | status=3 不授权远端操作，继续 stock game 检查/阻塞 |
| game record dataId/curVersion mismatch，但无 trusted WAL | 任意 | mismatch | stock Trainer/save mismatch |

## 关键 Hook 位点

Bank v1.5 verified stock image：

```text
size    0x2AC000
SHA256  2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

Production hooks：

```text
0x002B1DE4  case1 pre-Stage WAL gate
0x002B1FFC  case7 recovery status selector
0x002B2090  case8 local-save result interceptor
0x002A8968  state18 local recovery status decision
0x002A89D0  game dataId mismatch BNE
0x002A89E0  game curVersion mismatch BNE
0x002A8A64  in-place mismatch decision block
```

## 安全边界

- 不把 Trainer/save 校验永久 NOP。
- 不使用旧 transactionPassword 操作新 server transaction。
- 私有 status=3 必须完整匹配当前 server transaction 才能成为 fallback。
- Commit 必须有 stock status=2 的持久化证据。
- 没有足够证据时宁可保留 stock 阻塞，也不猜测 Commit。
- 当前验证覆盖静态分析、host regression、ARM/Thumb 代码尺寸和 armips 链接；仍需 3DS 实机网络故障注入验证。
