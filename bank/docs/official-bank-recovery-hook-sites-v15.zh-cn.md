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

原始 bytes @ `0x002A89D0`：`3E 00 00 1A`。

### curVersion compare

```text
0x002A89D4  E5911008  LDR r1,[r1,#8]          ; server curVersion
0x002A89D8  E5902010  LDR r2,[r0,#0x10]       ; game curVersion
0x002A89DC  E1510002  CMP r1,r2
0x002A89E0  1A00003A  BNE 0x002A8AD0          ; mismatch
```

原始 bytes @ `0x002A89E0`：`3A 00 00 1A`。

`0x002A8AD0` 同时被 invalid-status 等路径复用，因此不能粗暴 Hook 整个 funnel；recovery-only Hook 应只接两条真实 mismatch BNE。

## 3. state18 匹配后的真实 runtime 合同

在两条 mismatch BNE 附近：

```text
r4             = state18 object
[r4 + 0x28]    = current server BankTransactionParam*
r0             = current game GameRecoveryRecord*
```

stock game-record 匹配成功后，不是直接拿 GameRecoveryRecord 调远端，而是把它重新排布成标准 `BankTransactionParam` 到 `state+0x40`：

```text
state+0x40  dataId u64          <- game +0x00
state+0x48  curVersion u32      <- game +0x10
state+0x4C  updateVersion u32   <- game +0x14
state+0x50  size u32            <- game +0x18
state+0x54  padding
state+0x58  transactionPassword <- game +0x08
```

随后：

```text
state+0x88 = 1  ; game-source
status == 1 -> state6 -> stock Rollback
status == 2 -> state5 -> stock Commit
```

因此 synthetic recovery 不需要 raw-write 游戏 `main`。在 exact ownership 已证明时，可以直接把 **current server tx 的 0x20-byte BankTransactionParam** 复制到 `state+0x40`，把来源标成 game-source，然后跳回 stock `status 1/2` 分流。

## 4. state18 source flag / failure semantics

local recovery 匹配成功时：

```text
state+0x88 = 0
```

game recovery 匹配成功时：

```text
state+0x88 = 1
```

state5/6 分别发起 stock Commit/Rollback；state7 等待远端 callback。成功后统一进入 state11 完成恢复。失败时：

```text
source=local -> 回到 state4，再尝试 game recovery
source=game  -> 进入 mismatch/error path
```

因此 synthetic recovery 使用 `source=game` 有两个好处：

1. 成功时完全沿用 stock 完成路径；
2. 再次网络失败时不会进入无限 local↔game 重试，而是保留原版保护行为。

## 5. BankSaveState_Update（state7）关键阶段

函数：`0x002B1CF8`。

### 5.1 真正的 TX_BOUND：Stage 调用之前

`BankSave_SerializeAndStage @ 0x002B2320` 尾部：

```text
0x002B2494  LDR  r3,[r4,#0x28]  ; exact BankTransactionParam*
0x002B2498  LDRD r0,r1,[r4,#0x40]
0x002B249C  MOV  r2,r11
0x002B24A0  BL   0x002A2504     ; BankRemote_StageFileUpdate
```

原始 bytes @ `0x002B24A0`：

```text
17 C0 FF EB
```

进一步反汇编 `BankRemote_StageFileUpdate @ 0x002A2504` 证明：它把 `r3` 保存为 transaction 参数指针，并在真正调用远端接口之前从该结构读取并复制 transaction 字段到 request。也就是说：

> `state+0x28` 是 RMC52/Stage 的输入，不是 callback 的输出；完整 transaction 在网络请求发出前已经存在。

因此 OBRX 的 `BULK_APPLIED -> TX_BOUND` 必须前移到 `0x002B24A0` wrapper：

```text
BL OfficialRecovery_StageWrapper
```

wrapper：

1. 保留原 `r0-r3`；
2. `r3` 即本次 exact `BankTransactionParam*`；
3. 仅当 marker 为当前 profile 的 `BULK_PENDING/BULK_APPLIED` 时绑定 exact tx 并持久化；
4. 原样调用 stock `BankRemote_StageFileUpdate`；
5. 原样返回其结果。

如果请求同步失败或根本没有在服务器形成 pending transaction，下一次只会看到“marker 有 tx、server 无对应 pending”，进入 local marker cleanup，不会误 Commit/Rollback。

### 5.2 case2：Stage async callback success

```text
0x002B1DFC  LDRB r1,[r4,#0x48]
0x002B1E00  CMP  r1,#1
0x002B1E04  BNE  return
0x002B1E08  MOV  r1,#3
0x002B1E0C  clear callback byte
0x002B1E10  state=3
```

这只是确认 Stage async callback 成功；TX_BOUND 在此前网络请求发出前已经完成。

### 5.3 case3：开始写 GameRecoveryRecord

case3 入口：

```text
0x002B1E18  E5940008  LDR r0,[r4,#8]
```

此地址现在只定义为：

```text
GAME_RECOVERY_WRITE_BEGIN
```

不是 TX_BOUND。

case3 把 exact tx 写入 GameRecoveryRecord，`status=2`，然后发起游戏保存。

### 5.4 GAME_SAVE_STARTED

```text
0x002B1F18  BLX r2
0x002B1F1C  MOV r0,#4
```

B 可在该阶段记录 `GAME_SAVE_STARTED`。

### 5.5 GAME_SAVE_OK

```text
0x002B1F3C  CMP   r0,#1
0x002B1F40  MOVEQ r0,#5
0x002B1F44  MOVNE r0,#7
0x002B1F48  B     0x002B2174
```

在 `0x002B1F48` 前：

```text
r0 == 5 -> game save confirmed success
```

因此这里是 B 的可靠 `GAME_SAVE_OK` seam。

## 6. Bank-local recovery 是第二层保险

game save 成功后 case5 会把同一 transaction 写入 Bank-local recovery，`status=2`；game save 失败则 case7 写 local recovery `status=1`。

所以 stock 本身已有：

```text
GameRecoveryRecord
+
Bank-local recovery record
```

双保险。

结论：普通“Complete 阶段断网”理论上通常应被 stock recovery 接住。真正容易造成 Trainer/save mismatch 的，是更早的窗口，例如：

```text
server 已接受/留下 pending tx
但 case3 尚未把 exact tx 成功持久化进 game recovery
且 local recovery 也尚未写入
```

这正是 pre-Stage TX_BOUND marker 必须覆盖的窗口。

## 7. REMOTE_COMPLETE_STARTED / cleanup

Complete：

```text
0x002B20A0  LDR r0,[r4,#0x40]
0x002B20A4  LDR r1,[r4,#0x28]
0x002B20A8  MOV r2,#0
0x002B20AC  BL  0x001D5D74
```

B 在调用前可记录 `REMOTE_COMPLETE_STARTED`。

Complete callback success：

```text
0x002B20CC  MOV r1,#0x0D
```

是 marker DONE/cleanup 安全点。

Rollback callback success：

```text
0x002B210C  MOV r1,#0x10
```

同样是 cleanup 安全点。

## 8. A/B 修复策略

### A：Auto Rollback

只有当：

```text
OBRX exact tx == current server pending tx
```

才允许 synthetic recovery：

```text
server BankTransactionParam -> state18+0x40
state18+0x88 = 1
forced status semantics = 1
rejoin stock state6 Rollback
```

不匹配则保留 stock Trainer/save mismatch。

### B：Smart Commit / Rollback

ownership gate 与 A 完全一致；之后根据 marker stage：

```text
TX_BOUND / GAME_SAVE_STARTED
    -> status=1 -> stock Rollback

GAME_SAVE_OK / REMOTE_COMPLETE_STARTED
    -> status=2 -> stock Commit

DONE + server 仍 pending
    -> BLOCK
```

## 9. RX code-space

stock `.text`：

```text
0x00100000..0x00314000
```

唯一 >=64 bytes 连续全零洞：

```text
0x00313910..0x00314000
0x6F0 = 1776 bytes
```

现有 Official Bulk V3 已使用该 tail，因此 recovery runtime 必须极小，并尽量：

- 复用 stock remote functions；
- 复用已有 SD FS helpers；
- 使用小型 ARM trampoline + Thumb helper；
- 不复制 stock Commit/Rollback 状态机。

旧 combined/offline patch 曾通过禁用 stock state 再复用其函数体作 code cave；official-bulk 当前保留官方功能，不能直接采用这种破坏性策略。
