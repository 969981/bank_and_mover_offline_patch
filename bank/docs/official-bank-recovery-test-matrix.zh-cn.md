# Pokémon Bank v1.5 异常保存 / Recovery 实机实验矩阵

> 用途：验证 `state18 @ 0x002A8760` 已逆出的 transaction recovery 模型，并为后续 recovery-only Hook 提供实机证据。
>
> 原则：测试前备份游戏存档；每个实验使用可接受丢弃的 Bank 测试内容。不要把“UI 能进入”当成恢复成功，必须确认服务器 Bank、游戏存档和下一次启动均正常。

## 1. 需要记录的三组状态

每次测试都尽量记录：

### Server pending transaction

```text
dataId
curVersion
updateVersion
size
pStatus
pApplicationId
```

### GameRecoveryRecord

```text
dataId
transactionPassword
curVersion
updateVersion
size
status
```

family runtime offsets：

```text
Gen6  model + 0x1ADF8
SM    model + 0xB1394
USUM  model + 0xB4570
```

### Bank-local recovery record

```text
dataId
transactionPassword
curVersion
updateVersion
size
status
```

## 2. 判定基准

原版 state18 已确认逻辑：

```text
LOCAL.dataId == SERVER.dataId
&& LOCAL.curVersion == SERVER.curVersion
    -> status 1 Rollback / status 2 Commit

否则：

GAME.dataId == SERVER.dataId
&& GAME.curVersion == SERVER.curVersion
    -> status 1 Rollback / status 2 Commit

否则：
    -> mismatch UI
```

因此每个故障注入实验都要回答：

```text
SERVER / LOCAL / GAME 三者到底在哪一步第一次分叉？
```

## 3. 实验 A：正常保存控制组

步骤：

1. 正常联网进入 Official Bulk Sync。
2. Apply `bulk_import.bin`。
3. 正常保存，不人为断网。
4. 退出 Bank，再次进入同一游戏。

预期：

```text
Prepare/Stage
 -> Game record status=2 + save
 -> Local record status=2 + save
 -> Complete
 -> clear game transactionPassword + save
 -> next session no mismatch
```

必须确认：

- server Bank 已更新；
- 同一游戏可再次进入；
- game transactionPassword 最终被清空。

## 4. 实验 B：Prepare 前断网

目标：证明尚未形成 server pending transaction 时不会进入 mismatch recovery。

步骤：

1. 进入 Bank UI 后，在按保存前断网；或在远端 Prepare 尚未发起前阻断连接。
2. 结束错误流程。
3. 恢复网络，重新联动同一游戏。

关注：

```text
Server 是否没有 pending transaction
Game/Local recovery 是否保持旧值/空
```

预期风险：低。

## 5. 实验 C：Prepare/Upload 阶段断网

目标：复现最可能造成“SERVER=T1，但 GAME/LOCAL 仍=T0”的窗口。

步骤：

1. 保存开始。
2. 在 `PrepareUpdateBankObject` 已成功、但 `BankSaveState_Update case3` 尚未完成 game recovery record 保存前断网。
3. 不使用 JKSM，不运行游戏，不人工修改 save。
4. 恢复网络后重新进入 Bank。

若出现 mismatch，记录：

```text
Server T1: dataId / curVersion
Game T0:   dataId / curVersion
Local T0:  dataId / curVersion
```

若该组合成立，即直接证明：

> same physical save 也会因为异步事务分叉而被 state18 阻塞。

## 6. 实验 D：Game recovery save 后、Local recovery save 前断网

目标：验证 state18 的 GAME fallback。

理论状态：

```text
SERVER = T1
GAME   = T1, status=2
LOCAL  = T0/empty
```

原版下一次启动应该：

```text
LOCAL mismatch
 -> GAME match
 -> status=2
 -> stock Commit recovery
```

如果该场景仍出现 Trainer mismatch，则说明还存在静态分析尚未覆盖的额外条件，应停止 bypass 开发并继续逆向。

## 7. 实验 E：Local recovery save 后、Complete 前断网

理论状态：

```text
SERVER = T1 pending
GAME   = T1 status=2
LOCAL  = T1 status=2
```

下一次 state18 应优先 LOCAL match 并执行 Commit。

这是测试原版正常 crash-recovery 设计的关键控制组。

## 8. 实验 F：Game save 失败路径

目标：验证 status=1 的 Rollback recovery。

理论状态：

```text
SERVER = T1 pending
LOCAL  = T1 status=1
GAME   = 未成功写入/旧记录
```

下一次 state18 应：

```text
LOCAL match
 -> status=1
 -> Rollback
```

## 9. 实验 G：Rollback 本身网络失败

目标：复现第二类潜在 mismatch 窗口。

步骤：

1. 制造 game-save failure，使 stock 选择 rollback。
2. 在 `RollbackBankObject` 请求/响应期间断网。
3. 下次恢复网络重新进入。

记录 SERVER/LOCAL/GAME 三组字段，确认：

- server pending 是否仍存在；
- local status 是否仍为 1；
- dataId/curVersion 是否仍匹配。

## 10. 实验 H：Complete 请求发出后断网

目标：区分“服务器其实已经 Complete，但客户端没收到响应”与“服务器仍 pending”。

这是分布式事务中最重要的不确定窗口：

```text
client sends Complete
        ↓
server may commit
        ↓
response lost
```

下一次 `GetTransactionParam` 的 server 状态能告诉我们真实结果。

不要在这个阶段用本地猜测强制 Commit/回滚，必须先查询服务器现状。

## 11. Bulk-only 实验 Hook 的准入条件

只有同时满足以下条件，才允许研究自动 mismatch recovery：

1. 当前确实存在 server pending transaction；
2. 当前流程是普通游戏 Bank recovery，不是 HOME/Mover；
3. 能证明 pending transaction 来源于本工具的一次 bulk session；
4. 当前游戏 Pokémon boxes 没有经过正常 Game ↔ Bank 手动交换，或另有足够证据证明 Rollback 不会造成复制/丢失；
5. stock local/game recovery record 均无法正常匹配，因此客户端本来会进入 mismatch block。

## 12. 第一阶段实验 Hook 的建议行为

优先级：

```text
1. LOG/PROBE
2. 允许 stock recovery 使用已匹配 record
3. bulk-only + 有可靠 marker 时，研究 forced rollback
4. 不做 blind forced commit
```

第一版不要：

```text
NOP 全局 Trainer check
强行把旧 record 当成 server transaction
伪造 transactionPassword
对所有 mismatch 自动 Complete
```

## 13. 成功标准

一次 recovery 测试只有同时满足以下条件才算成功：

- Bank 下一次可正常进入；
- server Bank 内容符合预期；
- 游戏 Pokémon 内容符合预期；
- 再次退出/进入 Bank 不再触发 recovery/mismatch；
- transactionPassword / pending record 正常清理；
- 重复至少多次网络故障注入后无复制/丢失。
