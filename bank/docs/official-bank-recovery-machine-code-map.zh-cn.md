# Pokémon Bank Recovery A：verified machine-code map

> 分支：`feature/official-bank-recovery-auto-rollback`
>
> 来源：直接解析用户提供的 NoCrypto `00040000000C9B00(pokemon bank).cia`，从 CIA → NCCH → ExeFS → BLZ `.code` 解压得到 stock image。

## 1. Stock image 验证

```text
Title ID                 00040000000C9B00
CIA first content        0x3940
ExeFS                    0x6540
compressed .code         0x1776F4 bytes
decompressed .code       0x2AC000 bytes
image base               0x00100000
SHA-256                  2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

NCCH header的 NoCrypto bit 已确认，拆包不需要 common key。

## 2. state18 mismatch funnel

函数入口：

```text
0x002A8760  state18 recovery update
```

### Bank-local recovery compare

```asm
0x002A88E8  BL    local_get_dataId
...
0x002A8900  ORRS  R0,R0,R1
0x002A8904  BNE   0x002A897C      ; local record mismatch -> fallback game record
...
0x002A8918  CMP   R0,R1
0x002A891C  BNE   0x002A897C      ; curVersion mismatch -> fallback game record
```

### Game recovery compare

```asm
0x002A89BC  LDM   R0,{R5,R12}      ; game recovery dataId
...
0x002A89CC  ORRS  R2,R2,R3
0x002A89D0  BNE   0x002A8AD0      ; dataId mismatch
...
0x002A89DC  CMP   R1,R2
0x002A89E0  BNE   0x002A8AD0      ; curVersion mismatch
```

两种 game mismatch 全部汇聚到：

```asm
0x002A8AD0  MOV R0,#8              ; bytes: 08 00 A0 E3
0x002A8AD4  B   0x002A8980
0x002A8980  STR R0,[R4,#0x10]      ; substate = 8 (error path)
```

因此 A 的 recovery-only Hook 应覆盖 **`0x002A8AD0` 单条 4-byte 指令**，而不是 NOP 两条 BNE。

### Hook 返回合同

Hook 入口时：

```text
R4 = state18 object
[state+0x28] = CURRENT server BankTransactionParam*
```

工具若不能证明 marker exact-match：

```text
return R0 = 8
-> 0x002A8AD4
-> stock mismatch/error unchanged
```

工具若能证明 exact ownership：

```text
copy CURRENT server BankTransactionParam (0x20 bytes)
from [state+0x28]
to   state+0x40

return R0 = 6              ; stock Rollback substate
-> 0x002A8AD4
-> 0x002A8980 stores substate
-> case6 @ 0x002A8AFC
-> RollbackBankObject @ 0x001D5C28
```

这里不需要把旧 game/local recovery record 强制判为 match，也不需要先 raw-write 游戏 `main`。

## 3. state7 transaction bind

函数入口：

```text
0x002B1CF8  BankSaveState_Update
```

jump-table case3：

```text
0x002B1E18
```

原始首指令：

```asm
0x002B1E18  LDR R0,[R4,#8]         ; bytes: 08 00 94 E5
```

进入 case3 时，`state+0x28` 已经持有 Prepare/Stage 返回的真实 transaction。随后 stock 立即把：

```text
status = 2
dataId
transactionPassword
curVersion
updateVersion
size
```

写入当前 game recovery record，并启动游戏保存。

因此 `0x002B1E18` 是 A 将 `BULK_PENDING` marker 绑定为 exact `TX_BOUND` 的最早可靠 Hook 点。

Hook 必须：

1. fail-open：marker I/O/校验失败不能让正常 Bank save 失败；
2. 执行完工具逻辑后重放原始 `LDR R0,[R4,#8]`；
3. 回跳 `0x002B1E1C`。

## 4. 既有 state16 Hook

V3 已经 Hook：

```text
0x002AF460
original bytes: 70 40 2D E9    ; PUSH {R4-R6,LR}
```

A 不需要新增 state16 branch；只需在 `OfficialBulkSync_Process()` 确认 bulk apply 成功后持久化 `BULK_PENDING` marker。

## 5. A 最小 Hook surface

```text
existing:
0x002AF460  bulk apply dispatch

new:
0x002B1E18  bind exact transaction
0x002A8AD0  mismatch -> exact marker check -> stock Rollback
```

这比早期“改 state18 compare/BNE”方案更小，也不会弱化普通 Trainer/save validation。

## 6. Build guard

`bank/tools/verify_recovery_hook_sites.py --variant A` 必须在生成 IPS 前校验：

```text
.code size
.code SHA-256
0x002AF460 original bytes
0x002B1E18 original bytes
0x002A8AD0 original bytes
```

任一不符都必须拒绝构建。
