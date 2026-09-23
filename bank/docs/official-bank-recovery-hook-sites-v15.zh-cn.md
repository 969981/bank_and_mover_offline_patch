# Pokémon Bank v1.5 Recovery Hook Sites（CIA 实机基线验证）

## 1. 基线来源

输入：`00040000000C9B00(pokemon bank).cia`

CIA 主 content 可直接读取 NCCH，NCCH flags 为 NoCrypto。ExeFS 中 `.code`：

```text
compressed .code size = 0x1776F4
BLZ footer            = 0x0A177680 / 0x0013490C
```

按 3DS backwards BLZ 解压后：

```text
size   = 0x2AC000
SHA256 = 2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
image base = 0x00100000
```

与仓库既有 stock baseline 完全一致。

## 2. state18 game recovery mismatch gate

函数：`0x002A8760`

case4 中先取得当前游戏 recovery record，然后比较当前 server pending transaction。

### dataId 64-bit compare

```text
0x002A89B8  E5941028  LDR   r1,[r4,#0x28]     ; server tx pointer
0x002A89BC  E8901020  LDMIA r0,{r5,r12}       ; game dataId low/high
0x002A89C0  E1C120D0  LDRD  r2,r3,[r1]        ; server dataId low/high
0x002A89C4  E0222005  EOR   r2,r2,r5
0x002A89C8  E023300C  EOR   r3,r3,r12
0x002A89CC  E1922003  ORRS  r2,r2,r3
0x002A89D0  1A00003E  BNE   0x002A8AD0        ; mismatch
```

原始 bytes @ `0x002A89D0`：

```text
3E 00 00 1A
```

### curVersion compare

```text
0x002A89D4  E5911008  LDR r1,[r1,#8]          ; server curVersion
0x002A89D8  E5902010  LDR r2,[r0,#0x10]       ; game curVersion
0x002A89DC  E1510002  CMP r1,r2
0x002A89E0  1A00003A  BNE 0x002A8AD0          ; mismatch
```

原始 bytes @ `0x002A89E0`：

```text
3A 00 00 1A
```

`0x002A8AD0` 并非“纯 mismatch block”，它只是：

```text
0x002A8AD0  E3A00008  MOV r0,#8
0x002A8AD4  EAFFFFA9  B   state-store
```

同时还被“game recovery status 不是 1/2”等路径复用。因此 recovery-only Hook 应优先改两条 mismatch `BNE` 本身，不能粗暴重定向整个 `0x002A8AD0`。

## 3. state18 stock recovery action

匹配后读取 game recovery `status @ +0x1C`：

```text
0x002A8A50  LDRB r0,[r0,#0x1C]
0x002A8A54  CMP  r0,#1
0x002A8A58  BEQ  0x002A8AC0  ; state6 -> Rollback
0x002A8A5C  CMP  r0,#2
0x002A8A60  BEQ  0x002A8AC8  ; state5 -> Commit
```

远端调用：

```text
0x002A8AE4  BL 0x001D5D74    ; CommitStagedUpdate
0x002A8B08  BL 0x001D5C28    ; RollbackStagedUpdate
```

## 4. BankSaveState_Update（state7）关键阶段

函数：`0x002B1CF8`

### 4.1 TX-bound 最早稳定点（当前已确认）

case2 callback success 后切换 state3：

```text
0x002B1E00  CMP r1,#1
0x002B1E04  BNE 0x002B22B4
0x002B1E08  MOV r1,#3
0x002B1E0C  STRB r0,[r4,#0x48]
0x002B1E10  STR  r1,[r4,#0x10]
0x002B1E14  B    0x002B22B4
```

下次 update 的 case3 从：

```text
0x002B1E18  E5940008  LDR r0,[r4,#8]
```

开始。此时 `state+0x28` 已包含本次真实 `BankTransactionParam`，且 stock 尚未把它写入 game recovery record。

原始 bytes @ `0x002B1E18`：

```text
08 00 94 E5
```

### 4.2 game recovery record 写入

case3 把 transaction 写入当前游戏 recovery record：

```text
status = 2
+0x00 dataId
+0x08 transactionPassword
+0x10 curVersion
+0x14 updateVersion
+0x18 size
+0x1C status
```

关键写入区域：`0x002B1E48..0x002B1E90`。

### 4.3 GAME_SAVE_STARTED

case3 尾部触发 stock game/local save：

```text
0x002B1F08  LDR r0,[r4]
0x002B1F0C  MOV r1,#1
0x002B1F10  LDR r2,[r0,#0x18]
0x002B1F14  MOV r0,r4
0x002B1F18  BLX r2
0x002B1F1C  MOV r0,#4
0x002B1F20  B   0x002B2174
```

B 方案可在 `0x002B1F1C` 之后/等价安全点标记 `GAME_SAVE_STARTED`。

### 4.4 GAME_SAVE_OK / failed

case4 poll：

```text
0x002B1F24  ... call state vtable +0x1C
0x002B1F34  CMP r0,#0       ; pending
0x002B1F38  BEQ return
0x002B1F3C  CMP r0,#1
0x002B1F40  MOVEQ r0,#5     ; game save OK
0x002B1F44  MOVNE r0,#7     ; game save failed
0x002B1F48  B 0x002B2174
```

在 `0x002B1F48` 前，`r0==5` 可作为 `GAME_SAVE_OK` 的可靠判据。

## 5. Bank-local recovery record

stock 并非只写 game recovery；game save 成功后 case5 会把相同 transaction 复制到 Bank-local recovery record，`status=2`；game save 失败后 case7 写 `status=1`。

因此原版具有双层恢复：

```text
game recovery record
Bank-local recovery record
```

这意味着“一般 Complete 阶段断网”理论上 stock 自己应该可以恢复。若最终进入 Trainer/save mismatch，说明故障更可能处于更早/更特殊的窗口，或 server pending transaction 已与此前保存的 tx 不同。A/B 自动恢复必须继续使用 exact transaction ownership gate，不能根据“网络错误”字样猜恢复方向。

## 6. REMOTE_COMPLETE_STARTED

case9：

```text
0x002B20A0  LDR r0,[r4,#0x40]
0x002B20A4  LDR r1,[r4,#0x28]
0x002B20A8  MOV r2,#0
0x002B20AC  BL  0x001D5D74   ; CompleteUpdateBankObject
```

B 方案可在调用前标记 `REMOTE_COMPLETE_STARTED`。

## 7. Complete callback success / cleanup

case10：

```text
0x002B20C0  LDRB r1,[r4,#0x48]
0x002B20C4  CMP  r1,#1
0x002B20C8  BNE  0x002B22B4
0x002B20CC  MOV  r1,#0x0D
0x002B20D0  STRB r0,[r4,#0x48]
0x002B20D4  STR  r1,[r4,#0x10]
```

`0x002B20CC` 是 server Complete callback 已确认成功后的第一个稳定位置，可用于 marker DONE/cleanup。

## 8. Rollback call / callback success

case11：

```text
0x002B20DC  LDR r0,[r4,#0x40]
0x002B20E0  LDR r1,[r4,#0x28]
0x002B20E4  MOV r2,#0
0x002B20E8  BL  0x001D5C28   ; RollbackBankObject
```

case12 callback success：

```text
0x002B2100  LDRB r1,[r4,#0x48]
0x002B2104  CMP  r1,#1
0x002B2108  BNE  0x002B22B4
0x002B210C  MOV  r1,#0x10
0x002B2110  STRB r0,[r4,#0x48]
0x002B2114  STR  r1,[r4,#0x10]
```

`0x002B210C` 是 Rollback callback 已确认成功后的 cleanup 安全点。

## 9. BankSave_SerializeAndStage

函数：`0x002B2320`

实际 remote stage call：

```text
0x002B2494  LDR r3,[r4,#0x28]
...
0x002B24A0  BL 0x002A2504  ; BankRemote_StageFileUpdate
```

仓库旧 combined patch 也曾在 `BankSave_SerializeAndStage + 0x180 == 0x002B24A0` 替换该调用，说明该点是稳定的 stage seam。

仍需继续确认：`state+0x28` 中完整 transactionPassword/updateVersion 是在 `0x002A2504` 同步返回时写入，还是在其异步 callback 后才完整可用。这个结论决定 marker 的最早可靠 `TX_BOUND` 是 `0x002B24A4` 还是 state7 case3 `0x002B1E18`。

## 10. RX code-space

stock `.text` mapped：

```text
0x00100000..0x00314000
```

扫描整个 text 映射后，唯一 >=64 bytes 的连续全零洞：

```text
0x00313910..0x00314000
length = 0x6F0 = 1776 bytes
```

这正是现有 Official Bulk Sync V3 使用的 RX tail。不存在第二个天然大零洞。

旧 combined/offline patch 曾通过“先禁用某些状态，再复用其函数体”为额外 RX code cave；当前 official-bulk 分支保留 stock 功能，不能无条件复用该策略。

## 11. 第一版 Hook 原则

A：

- exact marker/server ownership；
- 两条 state18 mismatch BNE → recovery shim；
- shim 从 current server tx 重建 `status=1` runtime record；
- rejoin stock Rollback；
- Rollback success 后 cleanup。

B：

- 复用 A ownership gate；
- TX_BOUND / GAME_SAVE_STARTED → `status=1` Rollback；
- GAME_SAVE_OK / REMOTE_COMPLETE_STARTED → `status=2` Commit；
- Complete/Rollback callback success 后 cleanup；
- 未证明 exact ownership 一律保留 stock mismatch。
