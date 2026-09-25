# Pokémon Bank Recovery C：TechStable r3 技术说明

> 分支：`feature/official-bank-existing-lock-recovery`
>
> 目标：Pokémon Bank v1.5 / `00040000000C9B00`
>
> 当前组合：**Official Bulk Sync V3 + Recovery C Existing Lock Recovery + C-only precise reconnect**。

## 1. 基线

```text
image base  0x00100000
.code size  0x2AC000
SHA-256     2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
RX tail     0x00313910..0x00314000
```

当前 r3 IPS：

```text
size        1856 bytes
SHA-256     F5FCB3370D4CDC7521C9841BF61371FC2EFAEA7438E2546173B42F6353086A9D
```

## 2. 实机发现：所谓“服务器被锁住”是 state17 固定入口文案

第一次 Recovery C 实机验证已经跨过 Trainer mismatch，但进入 state17 后立即显示：

```text
由于上次操作中断，
因此服务器被锁住了。
请稍后再试。
```

机器码重新核对后确认，state17 initializer 在真正执行 Commit/Rollback 前就固定调用 UI helper：

```asm
0x002A9708  LDR r0,[r0,#0x2C]
0x002A970C  MOV r1,#0x0E
0x002A9710  LDR r0,[r0,#0x80]
0x002A9714  STR r0,[r4,#0x38]
0x002A9718  BL  0x0025DA24
```

因此该提示不是“服务器重新查询后确认仍被锁定”的证据，而是 recovery state17 的固定提示。r3 保留原 UI helper，仅把 message id `0x0E` 改成中性的 `0x0C`。

## 3. 为什么 r3 不再让 Recovery C 成功后直接进入 state16

stock 外层状态机已确认：

```text
state18 result4 -> state17
state17 result4 -> state16 BankDataSync
state17 result3 -> state20 clean disconnect/cleanup
```

r1/r2 的 C 路径是：

```text
state18 mismatch
→ synthetic status=1
→ state17 Rollback
→ clear transactionPassword
→ save game
→ result4
→ 同一 recovery session 立即进入 state16
```

r3 改为：**只有 Recovery C 自己制造的 recovery，在成功 Rollback/cleanup 后返回 result3，结束当前 recovery session；普通 stock state17 仍返回 result4。**

## 4. C-only transient marker

state17 对象分配大小为 `0x68`。stock 使用：

```text
state17 +0x60  callback success/status byte
state17 +0x61  callback error byte
```

在 state17 update/init/destructor 中没有使用 `+0x62`。r3 将它作为只存在于当前 state17 对象生命周期中的 transient terminal-result byte。

构造时原版：

```asm
0x002A61C8 STRB r1,[r0,#0x60]
0x002A61CC STRB r1,[r0,#0x61]
```

r3 替换为：

```asm
MOV r1,#0x40000
STR r1,[r0,#0x60]
```

小端结果：

```text
+0x60 = 0
+0x61 = 0
+0x62 = 4   ; ordinary stock state17 terminal result
+0x63 = 0
```

因此普通 state17 默认行为仍是 `result=4`。

## 5. Recovery C 的 RAM-only status=3

state18 两个真实 mismatch edge 仍是：

```text
0x002A89D0  dataId mismatch
0x002A89E0  curVersion mismatch
```

Recovery C 从当前 `[state18+0x28]` 的 server `BankTransactionParam` 重建完整 transaction context：

```text
dataId
curVersion
updateVersion
size
transactionPassword
```

但 r3 不再直接写 `GameRecoveryRecord.status=1`，而先写：

```text
status = 3
```

这里的 3 只表示：

> “这是 Recovery C 在 RAM 中根据 CURRENT SERVER T1 合成的 recovery，需要成功后 clean disconnect。”

它不是新的持久化 recovery 状态。

## 6. state17 精确消费 status=3

stock 在：

```asm
0x002A9518 LDRB r0,[r0,#0x1C]
0x002A951C CMP  r0,#1
```

读取 recovery status。

r3 将 `0x002A9518` Hook 到 `OfficialExistingLock_State17Status`：

```asm
ldrb   r1,[r0,#0x1c]
cmp    r1,#3
streqb r1,[r4,#0x62]   ; C-only terminal result = 3
moveq  r1,#1
streqb r1,[r0,#0x1c]   ; restore stock Rollback status before any save
mov    r0,r1
b      0x002A951C
```

所以：

```text
ordinary status1 -> unchanged
ordinary status2 -> unchanged
Recovery C status3 -> state17 marker=3, GameRecoveryRecord immediately restored to status1
```

**status=3 在任何 game save 之前就被恢复成 stock status=1，因此不应落盘。**

## 7. stock Rollback 和 cleanup 完全保留

C marker 被消费后，state17 继续原版：

```text
status1
→ BankRemote_RollbackStagedUpdate
→ remote success callback
→ clear GameRecoveryRecord.transactionPassword
→ stock family-specific game save
→ wait save success
```

Recovery C 不重写 Nintendo 的 Rollback RPC，也不手工伪造成功。

## 8. 只改 Recovery C 的 terminal result

stock state17 success terminal：

```asm
0x002A966C MOV  r0,#4
0x002A9670 STRB r0,[r4,#0x30]
```

r3 只把第一条改成：

```asm
0x002A966C LDRB r0,[r4,#0x62]
```

于是：

```text
普通 stock state17：+0x62=4 -> result4 -> state16
Recovery C state17： +0x62=3 -> result3 -> state20 clean disconnect
```

没有全局 `result4 -> result3` 改写。

## 9. r3 完整状态链

```text
server pending T1
      ↓
state18 game recovery mismatch
      ↓
Recovery C：CURRENT SERVER T1 -> exact RAM context
status=3
      ↓
state18 result4
      ↓
state17 consumes status3
+0x62=3
status restored to1
      ↓
stock Rollback(T1)
      ↓
stock clear transactionPassword
      ↓
stock save game cleanup
      ↓
state17 success loads +0x62 = 3
      ↓
state20 clean disconnect/cleanup
      ↓
下一次干净联动
      ↓
state16 normal BankDataSync
      ↓
Official Bulk Sync V3
```

这让“旧事务恢复”和“下一次 Bulk 导入”跨越一个干净的 session 边界。

## 10. Bulk Sync 仍然存在

`bulk_import.bin` 路径不变：

```text
SD:/3ds/Bank/bulk_import.bin
```

Recovery C r3 不要求移走它。Recovery 成功后当前 session 会 clean disconnect；下一次重新进入/重新联动时，正常 state16 下载 fresh BankObject 后 Bulk V3 才 Apply。

Bulk 的 Pokémon 数据源仍是 `bulk_import.bin`，不是自动读取游戏 PC Box；当前联动游戏用于 stock game-linked flow 和 tag/source/timestamp metadata。

## 11. 代码布局与预算

r3 实际 armips 链接：

```text
0x00313910 OfficialBulk_BankDataSyncDispatch
0x00313934 OfficialExistingLock_State17Status
0x00313950 OfficialExistingLock_GameMismatch
0x00313A70 OfficialBulkSync_Process
```

实际 area：

```text
1771 / 1776 bytes
remain 5 bytes
```

没有使用 mapped `.data/BSS` 作为 code cave。

## 12. 新增/保留的精确 patch surface

```text
0x002AF460..0x002AF464  Bulk dispatcher hook
0x002A89D0..0x002A89D4  Recovery C dataId mismatch
0x002A89E0..0x002A89E4  Recovery C curVersion mismatch
0x002A61C8..0x002A61D0  state17 transient marker init
0x002A9518..0x002A951C  state17 synthetic-status hook
0x002A966C..0x002A9670  C-only terminal result source
0x002A970C..0x002A9710  neutral state17 message id
0x00313910..0x00314000  RX tail payload
```

`0x002A9718` 的 stock UI helper call 保持原字节。

## 13. 验证状态

已通过：

```text
TDD RED: old status=1 policy test fails against new contract
Recovery C host regression               PASS
stock recovery model regression          PASS
Official Bulk Sync regression            PASS
ARMv6K production build                  PASS
Windows armips link smoke                PASS
state18 BNE target decode                 PASS
state17 status-hook target decode         PASS
critical machine-code assertions          PASS
real stock SHA/stock hook bytes           PASS
real stock patch-surface whitelist        PASS
IPS replay == patched real stock image    PASS
```

当前 IPS：

```text
size        1856 bytes
SHA-256     F5FCB3370D4CDC7521C9841BF61371FC2EFAEA7438E2546173B42F6353086A9D
```

仍待：

```text
真实锁存档 r3 端到端：Rollback → cleanup → state20
下一次干净联动：BankDataSync → Bulk V3
Bulk save → exit → redownload round-trip
故障注入
```

因此仍称 **TechStable**，不是 hardware-verified Stable。
