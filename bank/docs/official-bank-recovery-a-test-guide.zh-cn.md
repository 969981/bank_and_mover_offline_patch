# Official Bank Recovery A 实机验证指南

> 分支：`feature/official-bank-recovery-auto-rollback`
>
> 状态：`EXPERIMENTAL / STATIC + HOST VERIFIED / HARDWARE FAULT TEST PENDING`

## 1. 最终目标

Variant A 严格按最初定义实现：**只要 stock recovery 已经无法使用本地/游戏 recovery record、即将进入 state18 的 mismatch/error substate 8，就放弃这一次 pending transaction，使用 CURRENT server transaction 走原版 Rollback。**

它不再使用 OBRX marker，也不判断该 pending transaction 是否来自 bulk session。原因是 A 本身就是“最简单、最保守”的解锁方案：

```text
stock 能自己恢复 -> 完全 stock
stock 准备进入 mismatch/error -> 强制 Rollback CURRENT server tx
```

因此网络失败那一次 staged Bank 更新会被放弃，但客户端不会长期停在 Trainer/save mismatch。

## 2. Verified stock machine-code path

真实 NoCrypto CIA 已直接拆包并验证：

```text
Title ID           00040000000C9B00
.code size         0x2AC000
.code SHA-256      2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

state18 两个会把 substate 置为 8 的 funnel：

```text
0x002A8A74  MOV R0,#8   // matched record but invalid status
0x002A8AD0  MOV R0,#8   // local/game transaction mismatch
```

A 将二者都 branch 到：

```text
0x002A8B4C  OfficialRecovery_A_RollbackShim
```

原版 case8 的前 `0x20` bytes 被复用为 shim。由于 state18 内所有进入 substate 8 的 funnel 均已重定向，A 中这段原版 error-case 代码不再可达。

shim：

```text
serverTx = *(state + 0x28)
copy serverTx[0x20] -> state + 0x40
next substate = 6
```

然后直接重回 stock：

```text
state18 case6
 -> BankRemote_RollbackStagedUpdate @ 0x001D5C28
```

没有伪造旧 game/local record，没有 raw-write 游戏 `main`，也没有自定义远端协议。

## 3. 当前自动化验证

GitHub Actions `official-bank-recovery-a-ci` 覆盖：

- NoCrypto CIA → NCCH → ExeFS → BLZ `.code` 抽取 helper；
- stock `.code` size/SHA；
- `0x002A8A74 / 0x002A8AD0 / 0x002A8B4C` 原始 bytes；
- auto-rollback host policy；
- CURRENT server tx → rollback recovery context host model；
- stock recovery decision model regression；
- Official Bulk Sync core regression；
- production Thumb object仍为 1577 bytes；
- A ARM shim可编码且严格为 `0x20` / 32 bytes。

A 不占用新的 RX-tail 空间；shim 使用原版 case8 的不可达头部。

## 4. 实机故障矩阵

### A0 正常保存

```text
bulk apply -> Prepare/Stage -> game save -> Complete success
```

预期：

- state18 mismatch shim 不执行；
- 保存结果与原 V3 相同；
- 下一次正常进入 Bank。

### A1 网络在 Prepare/Stage 前失败

服务器没有可恢复 pending transaction 时，A 无事可做，保持 stock。

预期：不产生新的 Rollback 请求。

### A2 服务器留下 pending，但 stock local/game record 能正常 match

预期：

```text
stock match
 -> stock status=1 Rollback 或 status=2 Commit
```

A 的两个 error funnel 都不会被执行。

### A3 真正复现 Trainer/save mismatch

条件：

```text
server pending transaction 存在
local recovery 无法 match
current game recovery 无法 match
```

原版会走：

```text
0x002A8AD0 -> substate 8 -> Trainer/save error
```

A 预期：

```text
0x002A8AD0
 -> OfficialRecovery_A_RollbackShim
 -> CURRENT server tx copy 到 state+0x40
 -> substate 6
 -> stock RollbackBankObject
```

Rollback 成功后再次进入 Bank，应不再被同一 pending transaction 锁住。

### A4 recovery record match，但 status 异常

原版会从：

```text
0x002A8A74 -> substate 8
```

A 同样转为 CURRENT server tx 的 stock Rollback。

### A5 普通、真实的不同存档 mismatch

A 的取舍与 B 不同：如果服务器确实留有 pending transaction，而当前游戏无法 match，A **仍会 Rollback 服务器 pending transaction**，而不是继续显示 Trainer mismatch。

这是 A 的明确设计代价，也是为什么 A 定位为：

```text
安全解锁优先 / pending transaction 保留优先级最低
```

A 不会 Commit 不确定 transaction，因此不会把 staged BankObject正式提交；代价是该 pending 修改被丢弃。

## 5. 必须采集的实机证据

每次网络故障实验至少记录：

```text
故障发生阶段
Bank 最终错误文本
下次启动是否进入 stock recovery
是否命中 A shim
server Rollback 返回值
Rollback 后再次联动是否正常
BankObject 是否回到故障前版本
游戏 main 是否仍可正常加载
```

建议首先用一份可以重复恢复/备份的测试游戏存档验证，不先拿唯一生产存档做首轮 fault injection。

## 6. 与 B 的边界

A：

```text
无法确认恢复方向 -> 永远 Rollback
```

B：

```text
无法确认 stock record
 -> 工具 marker exact-match
 -> GAME_SAVE_STARTED -> Rollback
 -> GAME_SAVE_OK      -> Commit
 -> marker不匹配      -> 保留 stock mismatch
```

因此 A 是用于先验证“强制走 stock Rollback 是否能稳定清锁”的基准实现；B 才负责尽量保住已经成功推进到 game-save-complete 的 bulk transaction。
