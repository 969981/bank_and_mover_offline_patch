# Official Bank Recovery A：Rollback-only 实机验证指南

> 分支：`feature/official-bank-recovery-auto-rollback`
>
> 状态：`EXPERIMENTAL / CIA + MACHINE-CODE + CI VERIFIED / HARDWARE FAULT TEST PENDING`

## 1. 目标

A 的定义保持为：**只要远端事务没有真正 Complete，重启恢复时一律以 Rollback 为安全方向。**

新的实现不再等 Trainer/save mismatch 出现后强行绕过 state18，而是在服务器能够建立 pending transaction **之前**先建立一个可持久恢复的 stock rollback journal：

```text
当前 BankTransactionParam 已完整存在
        ↓
先写 Bank-local RecoveryRecord
status = 1
        ↓
本地保存成功
        ↓
才允许 RMC52 / Stage / PrepareUpdate
        ↓
游戏保存
        ↓
A 仍把 Bank-local record 保持为 status=1
        ↓
Complete 成功 -> stock cleanup
Complete 未成功 -> 下次 stock state18 自动 Rollback
```

因此 A 的原则不是“跳过校验”，而是**保证校验永远有一份 exact、可回滚的原生 recovery record 可用**。

## 2. 为什么要在 Stage 前写 journal

已从 NoCrypto Bank CIA 直接拆出并验证：

```text
Title ID      00040000000C9B00
.code size    0x2AC000
SHA-256       2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

`BankSave_SerializeAndStage @ 0x002B2320` 在真正发出远端请求前已经持有完整 tx：

```asm
0x002B2494  LDR r3,[r4,#0x28]   ; BankTransactionParam*
0x002B2498  LDRD r0,r1,[r4,#0x40]
0x002B249C  MOV r2,r11
0x002B24A0  BL  0x002A2504      ; BankRemote_StageFileUpdate / RMC52 path
```

`0x002A2504` 把这份 0x20-byte transaction 作为请求输入复制后才发起远端操作。因此危险窗口是：**服务器已经创建 pending，但 stock game/local recovery 还没持久化。**

A 在这个窗口之前先持久化 rollback journal。

## 3. A 的两个关键改造

### 3.1 Pre-Stage journal

Hook：

```text
0x002B1DE4  BankSave case1
0x002B2090  BankSave case8 local-save result
```

第一次进入 case1 时不立即调用 `BankSave_SerializeAndStage`，而是借用 stock case7：

```text
case7 @ 0x002B1FF8
    ↓
把 state+0x28 exact tx 写入 Bank-local RecoveryRecord
status = 1
    ↓
调用原版 local save
```

只有 local save callback 明确成功后，才回到 case1 发 RMC52。

临时使用 `state+0x48 = 7/8` 仅发生在 RMC52 发出之前；真正 Stage 前清回 0，因此不会污染原版远端 callback 的 0/1 状态。

### 3.2 保持 rollback-only

stock 在游戏保存成功后的 case5 会写：

```asm
0x002B1F50  MOV r1,#2
```

即把 Bank-local recovery 升级成 Commit record。

A 将这一条改成：

```asm
MOV r1,#1
```

后续字段复制、本地保存、远端 Complete 流程全部保留 stock。

因此只要 Complete 尚未真正成功，restart 后 local exact record 仍是：

```text
status=1 -> stock Rollback
```

这就是 A 与 B 的核心区别。

## 4. A 不修改的内容

A **不 Hook**：

```text
state18 game dataId BNE
state18 game curVersion BNE
Trainer/save mismatch UI funnel
Commit/Rollback RMC 实现
游戏 main raw bytes
```

真实换档、非本事务 mismatch 仍由 stock 校验保护。

## 5. 故障矩阵

| 故障窗口 | A 预期 |
|---|---|
| pre-journal local save 失败 | 不发 Stage，保存流程失败，不产生 server pending |
| journal 成功、Stage 请求尚未成功 | server 无 pending；残留 local status1 不会导致错误 Commit |
| server pending 后、game recovery 尚未落盘 | 下次 local exact status1 -> stock Rollback |
| game save 进行中断电/断网 | local status1 -> stock Rollback |
| game save 已成功、Complete 前断网 | local 仍为 status1 -> stock Rollback |
| Complete 已成功 | stock 后续 cleanup；不会再恢复旧 pending |
| unrelated game/save mismatch | 保留 stock mismatch 行为 |

## 6. 自动化验证

CI 当前检查：

- CIA/ExeFS/BLZ extraction helper；
- stock `.code` size + SHA；
- `0x002B1DE4 / 0x002B1F50 / 0x002B1FF8 / 0x002B2090 / 0x002B2494 / 0x002B24A0` 原始 bytes；
- Official Bulk Sync host regression；
- stock recovery model regression；
- ARM pre-stage shims 可编码；
- V3 production Thumb object = 1577 bytes；
- RX-tail 预算不超过 `0x6F0`。

当前尾部估算：

```text
V3 object     1577
ARM dispatch    36
A shims        108
-----------------
合计          1721 / 1776
```

`0x002B1F50` 是原地 4-byte 替换，不消耗 tail。

## 7. 首轮实机验证

首轮建议使用可备份测试档，分别在以下点人为断网：

1. 点击保存后立刻；
2. 等待远端上传时；
3. 游戏保存提示附近；
4. 游戏保存完成后、远端完成确认前。

每次记录：

```text
是否留下 server pending
下次是否进入 stock recovery
local recovery status/dataId/curVersion
是否调用 RollbackBankObject
Rollback 后能否正常重新联动
BankObject 是否回到事务前版本
游戏 main 是否仍能正常打开
```

A 的验收标准是：**网络故障最多损失本次尚未 Complete 的 Bulk 更新，但不能再因为该事务进入永久 Trainer/save mismatch 锁。**
