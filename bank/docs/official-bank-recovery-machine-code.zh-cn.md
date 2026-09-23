# Pokémon Bank v1.5 异常事务恢复：CIA 直拆与机器码级地址

> 分支：`feature/official-bank-recovery-research`
>
> 目标：从用户提供的 `00040000000C9B00(pokemon bank).cia` 直接提取 stock `.code`，并把 state 7 / state 18 的异常事务恢复路径从 Ghidra 伪代码推进到可用于 IPS Hook 设计的精确 ARM 指令地址。

## 1. CIA 可直接拆：NCCH 是 NoCrypto

本次实际 CIA 结构：

```text
CIA header size     0x2020
certificate size    0x0A00
ticket size         0x0350
TMD size            0x0B64
meta size           0x3AC0
content total       0x03FFF000
first content       0x3940
```

第一 content 的 `+0x100` 为：

```text
NCCH
```

NCCH flags（content `+0x188`）：

```text
00 00 00 00 01 03 00 04
```

最后一字节包含 `0x04` NoCrypto 标志，因此无需 common key 或 NCCH 解密。

ExeFS：

```text
NCCH ExeFS media-unit offset = 0x16
absolute ExeFS offset        = 0x6540
ExeFS size                   = 0x1BF200
```

ExeFS entries：

```text
.code   offset 0x000000  size 0x1776F4
banner  offset 0x177800  size 0x043FF8
icon    offset 0x1BB800  size 0x0036C0
```

`.code` 不是加密，而是 BLZ/code compression。

BLZ footer：

```text
encodedInfo    0x0A177680
additionalSize 0x0013490C
```

因此：

```text
0x1776F4 + 0x13490C = 0x2AC000
```

解压结果：

```text
size   0x2AC000
SHA256 2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

与仓库既有 Bank v1.5 stock baseline 完全一致。

可复现工具：

```text
bank/tools/extract_bank_cia.py
bank/tools/test_extract_bank_cia.py
```

用法：

```bash
python bank/tools/extract_bank_cia.py \
  '00040000000C9B00(pokemon bank).cia' \
  --output bank/rom/exefs/00040000000C9B00.dec.code
```

工具会同时校验：

- CIA section bounds；
- NCCH magic；
- NoCrypto flag；
- Program ID `00040000000C9B00`；
- ExeFS `.code`；
- BLZ 结构；
- 解压大小 `0x2AC000`；
- stock SHA-256。

## 2. state 18：Trainer mismatch 的精确 ARM gate

函数：

```text
0x002A8760  state 18 recovery update
```

当前游戏 recovery record 与服务器 pending transaction 的比较位于：

```asm
0x002A89B8  LDR   r1,[r4,#0x28]     ; server BankTransactionParam *
0x002A89BC  LDM   r0,{r5,r12}       ; game.dataId
0x002A89C0  LDRD  r2,r3,[r1]        ; server.dataId
0x002A89C4  EOR   r2,r2,r5
0x002A89C8  EOR   r3,r3,r12
0x002A89CC  ORRS  r2,r2,r3
0x002A89D0  BNE   0x002A8AD0        ; dataId mismatch
0x002A89D4  LDR   r1,[r1,#0x08]     ; server.curVersion
0x002A89D8  LDR   r2,[r0,#0x10]     ; game.curVersion
0x002A89DC  CMP   r1,r2
0x002A89E0  BNE   0x002A8AD0        ; curVersion mismatch
```

匹配后，stock 把 game recovery record 转成 state 18 内部 canonical transaction context：

```text
state +0x40  dataId
state +0x48  curVersion
state +0x4C  updateVersion
state +0x50  size
state +0x58  transactionPassword
```

随后：

```asm
0x002A8A50  LDRB r0,[r0,#0x1C]      ; game record status
0x002A8A54  CMP  r0,#1
0x002A8A58  BEQ  0x002A8AC0
0x002A8A5C  CMP  r0,#2
0x002A8A60  BEQ  0x002A8AC8

0x002A8AC0  MOV  r0,#6              ; Rollback substate
0x002A8AC8  MOV  r0,#5              ; Commit substate
0x002A8AD0  MOV  r0,#8              ; mismatch / error substate
```

`0x002A8AD0` 原始机器码：

```text
08 00 A0 E3    ; mov r0,#8
```

这是目前最干净的 recovery-only Hook 汇合点：

- local/game stock match 已经失败后才会到这里；
- dataId mismatch 和 curVersion mismatch 都汇合到这里；
- `r4` 仍然是 state18 object；
- 当前服务器 transaction 仍可由 `[r4+0x28]` 取得；
- fail-closed 时只需执行原始 `mov r0,#8`；
- 工具确认 exact ownership 时，可从**当前 server tx**构造 `state+0x40/+0x58` context，再选择 stock substate 5/6。

stock remote operation：

```asm
; Commit
0x002A8AD8  LDR r0,[r4,#0x3C]
0x002A8ADC  MOV r2,#0
0x002A8AE0  ADD r1,r4,#0x40
0x002A8AE4  BL  0x001D5D74

; Rollback
0x002A8AFC  LDR r0,[r4,#0x3C]
0x002A8B00  MOV r2,#0
0x002A8B04  ADD r1,r4,#0x40
0x002A8B08  BL  0x001D5C28
```

因此不需要自己重写网络协议；恢复 shim 的目标应是重建 stock 所需的 canonical context，然后回到原版 Commit/Rollback 子状态。

## 3. BankSave state 7 精确 case 图

函数：

```text
0x002B1CF8 BankSaveState_Update
```

已从 stock `.code` 确认主要 case：

```text
case 0   0x002B1D7C
case 1   0x002B1DE4   Serialize + Stage start
case 2   0x002B1DFC   wait remote Stage/upload callback
case 3   0x002B1E18   write GameRecoveryRecord(status=2), start game save
case 4   0x002B1F24   wait game save
case 5   0x002B1F4C   game save success -> write Bank-local status=2
case 6   0x002B1FCC   wait Bank-local persistence
case 7   0x002B1FF8   game save failure -> Bank-local status=1
case 8   0x002B2078   wait rollback record persistence
case 9   0x002B20A0   start CompleteUpdate
case 10  0x002B20C0   wait Complete
case 11  0x002B20DC   start Rollback
case 12  0x002B2100   wait Rollback
case 13  0x002B211C   post-Commit game recovery cleanup
```

### 3.1 case 3：game recovery record 先于 game save 持久化

关键机器码：

```asm
0x002B1E48  MOV  r1,#2
0x002B1E4C  STRB r1,[r0,#0x1C]      ; status=2
```

随后从当前 `BankTransactionParam *` 写：

```text
dataId
curVersion
updateVersion
size
transactionPassword
```

再调用对应游戏 family 的 save writer。

发出 game save 后：

```asm
0x002B1F1C  MOV r0,#4                ; enter wait-game-save case
```

原始 bytes：

```text
04 00 A0 E3
```

这是 B 方案可用的 `GAME_SAVE_STARTED` 精确语义点。

### 3.2 case 4：明确的 game-save success 判定

```asm
0x002B1F3C  CMP   r0,#1
0x002B1F40  MOVEQ r0,#5
0x002B1F44  MOVNE r0,#7
```

case 5 入口：

```text
0x002B1F4C
```

只有 `saveResult == 1` 才会进入，因此 case 5 是可靠的 `GAME_SAVE_OK` 语义点。

### 3.3 case 5：成功后再写 Bank-local recovery record

case 5 写：

```text
status = 2
transactionPassword
dataId
curVersion
updateVersion
size
```

然后持久化 Bank-local record。

### 3.4 Complete / Rollback

```text
0x002B20A0  case 9  -> CompleteUpdateBankObject
0x002B20DC  case 11 -> RollbackBankObject
```

B 方案若保留阶段研究，可把 `0x002B20A0` 视为 `REMOTE_COMPLETE_STARTED` 的语义点。

## 4. 对根因窗口的新收敛

机器码让“网络失败后为什么会 Trainer mismatch”进一步收敛。

如果已经执行到：

```text
case 3
 -> GameRecoveryRecord = exact server tx, status=2
 -> game main 保存成功
```

那么即使最终 `CompleteUpdateBankObject` 的网络请求失败，下次启动时 stock state18 理论上至少可以从 **game recovery record** 找到：

```text
server.dataId == game.dataId
server.curVersion == game.curVersion
status == 2
```

并进入 stock Commit recovery。

因此：

> **“最终 Complete 阶段断网”本身并不是 Trainer mismatch 的最佳解释。**

更符合 stock 时序的危险窗口是：

```text
PrepareUpdateBankObject 在服务器建立 pending T1
          ↓
客户端已经取得/服务器已经持有 T1
          ↓
HPP / Stage upload 或其回调发生网络失败
          ↓
state7 仍停在 case 1/2
          ↓
case3 从未执行
          ↓
GameRecoveryRecord 没写 T1
Bank-local record 也没写 T1
          ↓
下一次 state18
server = T1
local/game = old / empty
          ↓
mismatch -> Trainer/save error
```

这仍需通过实机 fault injection 确定具体断点，但静态代码已经证明：**只把工具 marker 的 TX_BOUND 放在 state7 case3 太晚，无法覆盖这个最重要的窗口。**

## 5. 对 A / B 方案的修正

### A：Auto Rollback

A 的核心策略不变：

```text
stock local/game mismatch
+
exact tool-owned server transaction
    -> 从 CURRENT server tx 重建 context
    -> status/方向 = Rollback
    -> 进入 stock state18 substate 6
```

但 `TX_BOUND` 必须前移：

```text
旧设计：state7 case3 才 bind       ❌ 太晚
新设计：PrepareUpdate response 后 bind ✅
```

这样才能处理：

```text
server pending 已建立
但 game/local recovery record 尚未写
```

的真实锁死窗口。

### B：Smart Commit / Rollback

B 的阶段模型仍可用于研究，但需要降低 Commit 路径的默认可信度。

因为：

```text
GAME_SAVE_OK
```

意味着 game recovery record 理应已经以 exact tx/status=2 持久化。若下一次 stock state18 仍然完全无法匹配这份 game record，本身就属于更异常的状态。

因此当前建议：

- `TX_BOUND / GAME_SAVE_STARTED` mismatch：Rollback；
- `GAME_SAVE_OK / REMOTE_COMPLETE_STARTED` mismatch：保留为 fault-injection 实验分支；
- 在实机证明这种组合真实存在之前，不把自动 Commit 当成默认生产行为；
- A 仍是第一优先的安全解锁实现。

## 6. 仍待定位的唯一关键机器码点

目前 state18 mismatch hook、state7 game-save 阶段和 Complete/Rollback 入口都已精确定位。

尚需继续定位：

> **RMC 52 `PrepareUpdateBankObject` 成功返回新的 `BankTransactionParam`，但 HPP/HTTP upload 尚未完成的最早客户端回调点。**

`0x002A2504 BankRemote_StageFileUpdate` 已确认调用远端对象 vtable `+0x170`，并把 transaction storage 传入该异步组合操作。下一步要把 `+0x170` 内部 PrepareUpdate response callback 与 HPP launch 之间的边界钉死。

这个地址一旦确认，就可以：

1. 在最早时刻把 tool `BULK_PENDING` marker 升级为 exact `TX_BOUND`；
2. 覆盖“服务器 pending 已建立、case3 尚未执行”的网络失败窗口；
3. 配合 `0x002A8AD0` recovery-only hook 完成 A 的端到端实机补丁。

## 7. 可执行空间约束仍然存在

stock `.text` 唯一明显的大型尾部 RX padding：

```text
0x00313910 .. 0x00314000 = 0x6F0 bytes
```

现有 Official Bulk Sync V3 已接近占满该区域，因此 recovery patch 不能假设还能完整塞入一套独立 C runtime。

后续实现必须优先：

- 复用 Bulk Sync 已有 FS helper；
- recovery shim 尽可能使用小型 ARM assembly；
- 或寻找经静态 XREF / CFG 证明不可达的原函数体作为独立 code cave；
- 不得把 `.rodata` / `.data` / `.bss` 当可执行空间。
