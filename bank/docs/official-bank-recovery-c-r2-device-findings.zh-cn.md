# Recovery C r2：首次实机反馈与 state17“服务器锁定”提示根因

日期：2026-09-25  
分支：`feature/official-bank-existing-lock-recovery`

## 1. 实机现象

Recovery C TechStable 首次用于真实 Trainer/recovery mismatch 存档后，不再直接显示原先的 Trainer mismatch，而是立即进入提示：

> 由于上次操作中断，因此服务器被锁住了。请稍后再试。

该画面本身不能证明服务器刚刚返回了“lock”。

## 2. 根因已经定位到 stock state17 初始化 UI

stock Bank v1.5：

```asm
0x002A9700  PostSelectionConnectionState_Initialize / state17 initialize
0x002A9708  LDR r0,[r0,#0x2C]
0x002A970C  MOV r1,#0x0E
0x002A9710  LDR r0,[r0,#0x80]
0x002A9714  STR r0,[r4,#0x38]
0x002A9718  BL  0x0025DA24     ; 显示 message 0x0E
0x002A971C  LDR r0,[r4,#0x38]
0x002A9720  BL  0x001D5B44
```

也就是说，state17 一初始化就先显示 message `0x0E`。这一动作发生在 state17 真正读取游戏 recovery record、决定 Commit/Rollback 之前，因此该提示不是 Rollback RPC 的返回结果。

## 3. 为什么 Recovery C 必然会碰到这个画面

Recovery C TechStable 在 state18 的 game transaction `dataId` / `curVersion` mismatch 边缘接管，使用 CURRENT server `BankTransactionParam` 重建一份内存 GameRecoveryRecord，并强制：

```text
status = 1   # Rollback
```

随后让 state18 从 stock case11 以 `result=4` 结束。

stock outer transition 对 state18：

```text
state18 result=4 -> state17
```

因此 C 的安全设计本来就是：

```text
state18 mismatch
 -> Recovery C 重建 exact current tx + game status=1
 -> state18 result=4
 -> state17
 -> stock Rollback
 -> stock 清 transactionPassword
 -> stock 保存游戏
 -> state17 result=4
 -> state16
```

进入 state17 的瞬间，stock initializer 就会显示 message `0x0E`，于是看起来像“Recovery C 又制造了一个服务器锁”。实际上这是客户端固定 UI 文案。

## 4. state17 真正的 Recovery 路径

关键机器码：

```text
0x002A94DC..0x002A9528  读取 GameRecoveryRecord
                         transactionPassword != 0
                         status=1 -> substate3 Rollback
                         status=2 -> substate2 Commit

0x002A9588..0x002A95A4  stock RollbackBankObject
0x002A95C0..0x002A9614  成功后清 game transactionPassword 并启动 game save
0x002A9640..0x002A9660  等待 game save
0x002A966C..0x002A9678  成功 terminal result=4
```

outer transition 对 state17 的 `result=4`：

```asm
0x002A583C  CMP r2,#3
0x002A5844  CMP r2,#4
0x002A5848  MOVEQ r0,#16
```

因此成功路径仍然会进入 state16；Recovery C 不需要绕过 state17。

## 5. r2 的最小修复

不改变事务语义，只禁止 state17 初始化时写入误导提示：

```asm
.org 0x002A9718
    nop
```

stock bytes：

```text
C1 D0 FE EB    ; BL 0x0025DA24
```

r2 bytes：

```text
00 F0 20 E3    ; ARM NOP
```

保留不变：

- state17 GameRecoveryRecord 读取；
- status=1 Rollback；
- `RollbackBankObject`；
- transactionPassword 清理；
- game save；
- state17 `result=4 -> state16`；
- Official Bulk Sync V3；
- `/3ds/Bank/bulk_import.bin`。

## 6. 为什么不直接跳过 state17

直接把 state18 result4 改成 state16 会丢失两件关键事情：

1. 对 CURRENT server transaction 的 stock Rollback；
2. 游戏存档中 recovery transactionPassword 的持久化清理。

这会把“提示难看”变成真正的 recovery 状态残留，因此 r2 不做这种 bypass。

## 7. r2 实机验证重点

保留 `bulk_import.bin` 可以测试完整链：

```text
Recovery C mismatch takeover
 -> state17（不再显示错误的 lock banner）
 -> Rollback
 -> game recovery cleanup/save
 -> state16
 -> 正常 game-linked BankDataSync
 -> Official Bulk Sync V3 apply bulk_import.bin
 -> Bank UI
 -> 原版保存
```

如果 r2 取消提示后仍长期停留、没有进入 state16/Bank UI，则问题已经不是 UI，而是 state17 的 Rollback callback / game-save completion；下一步应针对 `state+0x60`、`state+0x61` 和 substate 3/4/5/6 做实机 telemetry，而不是继续修改提示或无条件跳过事务。
