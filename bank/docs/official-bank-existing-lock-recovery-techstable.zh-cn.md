# Pokémon Bank Recovery C4：Persistent Repair / TechStable

> 分支：`feature/official-bank-existing-lock-recovery`
>
> 目标：Pokémon Bank v1.5 / Title ID `00040000000C9B00`
>
> 当前组合：**Official Bulk Sync V3 + Recovery C4 Persistent Existing-Lock Repair**。

## 1. 严格基线

```text
image base  0x00100000
.code size  0x2AC000
stock SHA-256
2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF

RX tail     0x00313910..0x00314000
```

C4 `code.ips`：

```text
size        1901 bytes
SHA-256     2C400AF5E0C5C997136A6C8F070B614D19A00A09339160A590AFDB684D3F8733
```

应用 C4 后完整 `.code` SHA-256：

```text
77ED66B94E0CC0619F6F52327CA2C1693536032F211E670459E57A842E8C7472
```

## 2. C4 为什么改变恢复顺序

r1-r3 的共同思路是在 state18 mismatch 后根据 CURRENT SERVER pending transaction T1 重建 GameRecoveryRecord，再尽快进入恢复链。

实机结果说明，仅在 RAM 中制造一致状态并立即进行后续 recovery，仍不足以把“服务器 T1 / 游戏存档 recovery”两边真正恢复到 stock 可重复进入的状态。

C4 因此改成 **persist first, remote second**：

```text
第一次进入
server pending T1
        ↓
state18 game recovery mismatch
        ↓
C4 从 CURRENT SERVER T1 重建 exact GameRecoveryRecord
        ↓
先用 Pokémon Bank 原版游戏保存器
把 exact T1/status=1 真正持久化进游戏存档
        ↓
本轮 clean disconnect
        ↓
【本轮不发 Commit，不发 Rollback】

下一次进入
server T1
=
game persisted recovery T1/status1
        ↓
完全回到 stock recovery
        ↓
stock Rollback / cleanup
```

这样服务器 pending T1 在第一轮修复期间保持不动；只有本地恢复记录真正保存成功后，下一次才让原版 Bank 根据匹配的事务凭据处理服务器。

## 3. CURRENT SERVER T1 是唯一数据源

state18 两个精确 mismatch edge：

```text
0x002A89D0  dataId mismatch
0x002A89E0  curVersion mismatch
```

入口约束：

```text
r4        = state18 object
r0        = current GameRecoveryRecord *
[r4+0x28] = CURRENT SERVER BankTransactionParam *
```

C4 复制：

```text
server +0x00 dataId               -> game +0x00
server +0x18 transactionPassword  -> game +0x08
server +0x08 curVersion           -> game +0x10
server +0x0C updateVersion        -> game +0x14
server +0x10 size                 -> game +0x18
```

不会使用历史 WAL、猜测 transactionPassword，也不会 Commit 未知历史事务。

## 4. status=3 仍然只是 RAM handoff marker

C4 在 state18 临时写：

```text
GameRecoveryRecord.status = 3
```

`3` 不是新的存档格式，只表示：

> 这是 C4 根据 CURRENT SERVER T1 合成的记录；state17 必须先持久化修复，而不是先碰服务器。

state17 在 `0x002A9518` 读取 status 时立即：

```text
status3
→ state17 +0x62 = 3        ; transient terminal-result marker
→ GameRecoveryRecord.status = 1
→ substate = 5             ; 直接进入 game-save stage
```

所以真正交给游戏保存器的数据已经是 stock：

```text
status = 1  // Rollback recovery
```

status3 不会被设计为落盘值。

## 5. C4 第一轮明确绕过远端 Commit/Rollback

stock state17：

```text
status1 -> substate3 -> Rollback
status2 -> substate2 -> Commit
```

C4 status3 被识别后直接设置：

```text
substate = 5
```

因此跳过：

```text
0x002A9564  stock remote path
0x002A9588  stock remote path
```

第一轮只做本地持久化修复。

## 6. 复用原版游戏保存器，不自行实现 Gen6/Gen7 save

stock state17 case5 原本会：

```text
remote transaction 成功
→ clear GameRecoveryRecord.transactionPassword
→ vtable +0x18 启动游戏保存
→ case6 / vtable +0x1C 等待保存结果
```

已确认 Bank v1.5 state17 vtable：

```text
vtable          0x0036198C
vtable +0x18 -> 0x002B4AB4  stock game-save start
vtable +0x1C -> 0x002B4A20  stock game-save poll
```

C4 Patch `0x002A95F0..0x002A9618`：

```text
if state17+0x62 == 3:
    不清 transactionPassword
else:
    保留 stock 语义，清 transactionPassword

call 0x002B4AB4
substate = 6
```

因此 C4 写游戏存档时保存的是：

```text
dataId              = CURRENT SERVER T1
auth/password        = CURRENT SERVER T1
curVersion           = CURRENT SERVER T1
updateVersion        = CURRENT SERVER T1
size                 = CURRENT SERVER T1
status               = 1
```

而不是只在 RAM 中暂时伪造。

## 7. 保存成功与失败的事务边界

### 保存成功

stock case6 的原版 poll 返回 success 后：

```text
case7
→ C4 terminal result = 3
→ state20 clean disconnect
```

服务器 pending T1 在这一轮从未被修改。

### 保存失败

C4 不把失败伪装成成功：

```text
stock save poll failure
→ stock error path / result20
```

并且由于第一轮没有发 Commit/Rollback：

```text
server pending T1 仍然存在
```

下一次仍可重新尝试持久化 repair，属于 fail-closed。

## 8. 下一次启动为什么能回到 stock recovery

如果第一轮保存成功，则下一次游戏存档中已经存在：

```text
exact CURRENT SERVER T1
status = 1
```

于是原本触发 C4 的：

```text
dataId mismatch
curVersion mismatch
```

不应再成立。

后续由原版 Bank 自己执行匹配 recovery，包括服务器 Rollback、清 transactionPassword 和 cleanup save。C4 不伪造服务器返回值，也不自己重写 Nintendo 的 transaction RPC。

## 9. “服务器被锁住”提示不是服务器状态探针

state17 initializer 在真正执行 recovery RPC 之前就会显示固定 recovery 文案。C4 仍将其 message id 从 `0x0E` 换成中性 `0x0C`，但不根据 UI 文案判断服务器是否存在 pending T1。

真正判断依据应是下一次进入时：

```text
是否仍命中 dataId/curVersion mismatch
是否能走 stock matching recovery
是否最终恢复正常 BankDataSync
```

## 10. Bulk Sync V3 保留

固定输入仍是：

```text
SD:/3ds/Bank/bulk_import.bin
```

可以保持文件原位。

C4 第一轮只修游戏 recovery 存档，不 Apply Bulk。等 stock recovery 真正完成并重新进入正常 `BankDataSync` 后，Bulk V3 才在 fresh BankObject 上执行。

Bulk 的 Pokémon 数据源仍是 `bulk_import.bin`；不是自动读取当前游戏 PC Box。

## 11. Patch surface

C4 允许修改：

```text
0x002A61C8..0x002A61D0  state17 transient marker init
0x002A89D0..0x002A89D4  state18 dataId mismatch
0x002A89E0..0x002A89E4  state18 curVersion mismatch
0x002A9518..0x002A951C  state17 C4 status hook
0x002A95F0..0x002A9618  persist-first case5 block
0x002A966C..0x002A9670  C-only terminal result
0x002A970C..0x002A9710  neutral recovery message
0x002AF460..0x002AF464  Bulk dispatcher hook
0x00313910..0x00314000  verified RX tail
```

另外静态验证要求保持：

```text
0x003619A4 == 0x002B4AB4  // state17 vtable +0x18
0x002B4AB4 stock prologue unchanged
0x002A9718 stock UI-helper BL unchanged
```

## 12. RX-tail 预算

最新 armips 实际结果：

```text
1767 / 1776 bytes
remain 9 bytes
```

关键链接符号：

```text
0x00313910 OfficialBulk_BankDataSyncDispatch
0x00313934 OfficialExistingLock_State17Status
0x00313958 OfficialExistingLock_GameMismatch
0x00313A6C OfficialBulkSync_Process
```

## 13. 验证状态

已完成：

```text
TDD RED：旧策略返回 immediate-recovery，测试按预期失败
TDD GREEN：C4 persist-first policy PASS
Recovery C host regression               PASS
stock recovery model regression          PASS
Official Bulk Sync regression            PASS
ARMv6K production build                  PASS
Windows armips link smoke                PASS
C4 save-call target 0x002B4AB4           PASS
state18/state17 branch decode             PASS
RX tail 1767/1776                         PASS
真实 stock SHA/check bytes                PASS
真实 stock patch-surface whitelist        PASS
IPS replay == patched real stock image    PASS
```

仍待实机确认：

```text
第一轮：mismatch -> exact T1 persist -> clean disconnect
第二轮：stock matching recovery -> server pending T1 被清理
随后：normal BankDataSync -> Bulk V3 -> 原版保存 -> redownload
网络/关机 fault injection
```

因此 C4 仍标记 **TechStable**，不是 hardware-verified Stable。
