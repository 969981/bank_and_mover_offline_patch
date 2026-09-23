# Official Bank Recovery A：Bulk-only 使用边界

`feature/official-bank-recovery-auto-rollback` 是安全清锁优先的实验分支。

## 适用场景

只用于下面这种流程：

```text
官方服务器下载 BankObject
        ↓
bulk_import.bin overlay 到 Bank Box
        ↓
联动游戏中的 Pokémon 不做人工移动/交换
        ↓
保存
```

当本次 Bulk Sync 确实 apply 成功时，runtime flag `0x003ABFFC` 被置 1。保存开始前，Recovery A 先通过原版 Bank-local save 路径持久化 exact transaction 的私有 `status=3` WAL，然后清 runtime flag，再发起 RMC52 Stage。

下次 state18 如果发现：

```text
server pending transaction
==
local status=3 WAL
```

并且完整匹配：

```text
dataId
curVersion
updateVersion
size
transactionPassword low/high
```

Recovery A 始终选择 stock Rollback。

## 为什么必须限制为 Bulk-only

A 的设计目标是：

```text
宁可丢弃网络失败的这一轮 Bulk 保存
也不要让 Bank 进入永久 Trainer/save mismatch 锁
```

如果用户在同一 Bank 会话里还手工把 Pokémon 从游戏拖入/拖出 Bank，游戏存档本身可能已经发生业务数据变化。此时若故障恰好发生在：

```text
game save 已成功
但 local recovery 仍停在 pre-Stage status=3
```

A 仍会按设计选择 Rollback server transaction，这可能让游戏侧已经持久化的人工移动与服务器 Bank 回滚后的内容产生业务不一致。

因此 A 分支不得作为普通 Bank 的全局 recovery patch 使用。

## 与 Recovery B 的区别

Recovery B 不依赖“这是 Bulk-only”这个假设：

- pre-RMC52 也先写 durable status=3 WAL；
- 若 game recovery 已有 exact `status=2`，则保留 stock Commit；
- 只有没有 durable Commit 证据时，才使用 status=3 WAL 作为 Rollback fallback。

因此，普通 Bank / 手工搬 Pokémon 场景应优先使用 Recovery B。

## 当前验证范围

Recovery A 已覆盖：

- stock Bank v1.5 exact hook-site byte verification；
- host recovery policy/runtime tests；
- ARM/Thumb object size budget；
- Official Bulk Sync regression；
- V3 backup filename live-second semantics。

仍需实机验证：

- 在纯 Bulk-only 会话的不同网络断点进行故障注入；
- 确认下次 state18 能稳定进入 stock Rollback 并清除 server pending；
- 确认成功保存路径与原 V3 一致。
