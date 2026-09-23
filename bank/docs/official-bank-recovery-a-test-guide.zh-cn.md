# Official Bank Recovery A：Bulk-only Pre-RMC52 Rollback WAL 实机验证指南

> 分支：`feature/official-bank-recovery-auto-rollback`
>
> 状态：`EXPERIMENTAL / CIA + MACHINE-CODE + PRODUCTION-LINK CI VERIFIED / HARDWARE FAULT TEST PENDING`

## 1. 最终目标

A 的最终定义是：**只对本次确实成功应用 `bulk_import.bin` 的 Bank 会话增加事务保护；一旦该事务异常中断，优先安全 Rollback，不尝试保住本次尚未 Complete 的 Bulk 更新。**

A 不再等 Trainer/save mismatch 出现后绕过 state18，而是在服务器有机会创建 pending transaction **之前**先留下原版 Bank 自己就能理解的 durable rollback record：

```text
state16 fresh Bank download
        ↓
Bulk overlay 成功
        ↓
BulkSessionFlag = 1
        ↓
用户保存
        ↓
Pre-RMC52：先借用 stock case7
持久化 exact BankTransactionParam + status=1
        ↓
local save 明确成功
        ↓
清 BulkSessionFlag
        ↓
才允许 stock SerializeAndStage / RMC52
        ↓
后续完全 stock
```

因此 A 的恢复不是“伪造匹配”，而是**让 stock state18 始终有一份 exact、原生 `status=1` recovery record 可用于 Rollback**。

## 2. 已验证 Bank v1.5 基线

由 NoCrypto CIA 直接拆包并 BLZ 解压：

```text
Title ID      00040000000C9B00
.code size    0x2AC000
SHA-256       2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

`BankSave_SerializeAndStage @ 0x002B2320` 在真正发出远端请求前已经持有完整 transaction：

```asm
0x002B2494  LDR r3,[r4,#0x28]   ; BankTransactionParam*
0x002B2498  LDRD r0,r1,[r4,#0x40]
0x002B249C  MOV r2,r11
0x002B24A0  BL  0x002A2504      ; BankRemote_StageFileUpdate / RMC52 path
```

所以可以在 RMC52 之前先把**同一份 exact tx**持久化成本地 recovery WAL，从结构上关闭：

```text
server pending 已建立
但 local/game recovery 都尚未 durable
```

这个危险窗口。

## 3. Bulk-only gate

运行时使用：

```text
0x003ABFFC  BulkSessionFlag
```

规则：

```text
state16 substate 0       -> flag = 0
bulk apply 真正成功       -> flag = 1
ordinary Bank save       -> flag = 0，完全 stock
pre-RMC52 WAL 已 durable  -> flag = 0，再开始 Stage
```

它只是运行时 scratch byte，不把代码放进 mapped data；最终 patch verifier 仍要求 `0x0036A000..0x003AC000` 文件镜像完全不变。

## 4. A 的 production hooks

A 最终只需要三个代码修改区：

```text
0x002AF460  BankDataSyncState_Update
            Official Bulk Sync V3 入口

0x002B1DE4  save case1
            pre-RMC52 WAL diversion

0x002B2090  save case8
            pre-journal local-save result
```

### 4.1 第一次进入 case1

若 `BulkSessionFlag != 1`：

```text
r0 = r4
return
0x002B1DE8 原版 BL BankSave_SerializeAndStage
```

普通 Bank 保存因此不改变语义。

若 flag=1，则先把 save substate 改到 stock case7：

```text
case7 @ 0x002B1FF8
    ↓
原版把 state+0x28 exact tx
写入 Bank-local RecoveryRecord
status = 1
    ↓
原版 local save
```

### 4.2 case8 确认 journal 持久化

local save 成功：

```text
返回 case1
清临时 state+0x48 journal marker
清 BulkSessionFlag
继续原版 SerializeAndStage / RMC52
```

local save 失败：

```text
不发 RMC52
进入原版失败/退出路径
```

因此不会出现“为了保护事务，反而先创建 server pending”的反向问题。

## 5. A 明确不修改 state18

这是当前 A 相比早期实验版最重要的收敛。

A **不再修改**：

```text
0x002B1FFC  stock case7 status=1
0x002B1F50  stock case5 status=2
0x002A8968  local recovery status decision
0x002A89D0  game dataId mismatch
0x002A89E0  game curVersion mismatch
Trainer/save mismatch UI
Commit/Rollback RMC 实现
游戏 main raw bytes
```

因为 pre-RMC52 WAL 本身就是原生 `status=1` record：

```text
exact local status=1
    ↓
stock state18
    ↓
stock Rollback
```

无需任何 recovery bypass。

注意：后续 stock case5 在正常流程中仍可能写 `status=2`。如果 game/local save 已完整推进到 stock 可 Commit 的阶段，仍允许原版自己的 recovery 逻辑工作；A 额外提供的是**Stage 之前一定存在的 rollback fallback**，不是永久把所有 record 锁成 status=1。

## 6. RX tail 与生产链接

唯一大 RX cave：

```text
0x00313910..0x00314000
size = 0x6F0 = 1776 bytes
```

最新 production CI 实际测得一版：

```text
Bulk Thumb object   1545 bytes
ARM dispatcher        36 bytes
A WAL Thumb            84 bytes
--------------------------------
总计                 1665 / 1776
剩余                  111 bytes
```

CI 已升级为：

```text
arm-none-eabi-gcc/as 编译真实 production objects
        ↓
Windows armips 导入真实 ELF objects
        ↓
组装真实 main_official.s
        ↓
检查 production hook writes / symbols / tail layout
```

不再使用假的 WAL stub 掩盖链接错误。

## 7. 最终静态安全门

release verifier 要求：

- stock `.code` SHA 必须精确匹配；
- 只允许 `0x002AF460 / 0x002B1DE4 / 0x002B2090 / RX tail` 发生变化；
- `0x002B1FFC` 与 state18 必须保持 stock；
- `0x0036A000..0x003AC000` mapped data image 必须完全不变；
- 所有新增符号必须位于 RX tail；
- IPS replay 必须逐字节重建 patched `.code`。

## 8. 故障矩阵

| 故障窗口 | A 预期 |
|---|---|
| 非 Bulk 普通 Bank 保存 | 完全 stock，不创建额外 WAL |
| pre-journal local save 失败 | 不发 RMC52，不产生 server pending |
| WAL durable、Stage 尚未建立 pending | server 无 pending；残留 status1 可安全清理/覆盖 |
| Stage 成功、game recovery 尚未 durable | 下次 exact local status1 -> stock Rollback |
| game save 中途失败 | stock/local rollback 机制处理 |
| game save 已成功、Complete 前网络失败 | 由当前 stock local/game recovery 状态决定；A 不伪造 Commit |
| Complete 成功 | stock cleanup |
| unrelated/foreign save | stock validation / mismatch，不自动绕过 |

## 9. 首轮实机 fault injection

使用可恢复的测试档，分别在以下窗口人为断网/终止：

1. 点击保存后、pre-journal local save 附近；
2. Stage/RMC52 请求期间；
3. Stage 已成功但游戏保存尚未完成；
4. 游戏保存过程中；
5. 游戏保存成功后、Complete 返回前。

每次记录：

```text
server pStatus / pending tx
local recovery dataId / curVersion / status
game recovery dataId / curVersion / status
是否进入 stock Rollback
下次是否可正常重新联动 Bank
Bulk 更新是否回滚
游戏 main 是否仍可正常使用
```

A 的实机验收标准：

> **Bulk 保存遇到网络异常时允许牺牲本次尚未可靠完成的更新，但不能再因为“server pending 先于 durable recovery”而进入永久 Trainer/save mismatch 锁。**
