# Pokémon Bank Recovery B：verified machine-code map

> 分支：`feature/official-bank-recovery-smart`
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

Bank-local mismatch 先回退到 game recovery；game recovery 的 dataId / curVersion 任一不匹配，最终都汇聚到：

```asm
0x002A8AD0  MOV R0,#8              ; bytes: 08 00 A0 E3
0x002A8AD4  B   0x002A8980
0x002A8980  STR R0,[R4,#0x10]
```

因此 B 同样只需 Hook **`0x002A8AD0` 单条 4-byte 指令**。

Hook 入口：

```text
R4 = state18 object
[state+0x28] = CURRENT server BankTransactionParam*
```

若 marker 不 exact-match：

```text
R0=8 -> stock mismatch/error
```

若 exact-match：

```text
copy [state+0x28] 的 CURRENT server BankTransactionParam (0x20 bytes)
to state+0x40
```

再根据 staged marker 返回：

```text
TX_BOUND / GAME_SAVE_STARTED       -> R0=6 -> stock Rollback case6
GAME_SAVE_OK / REMOTE_COMPLETE_STARTED -> R0=5 -> stock Complete case5
```

stock case5：

```text
0x002A8AD8 -> CompleteUpdateBankObject @ 0x001D5D74
```

stock case6：

```text
0x002A8AFC -> RollbackBankObject @ 0x001D5C28
```

不需要伪造旧 game/local recovery record，也不需要 raw-write `main` 才能进入 stock recovery。

## 3. state7 exact transaction / stage Hook 点

函数：

```text
0x002B1CF8  BankSaveState_Update
```

### 3.1 case3：TX_BOUND + GAME_SAVE_STARTED

入口：

```asm
0x002B1E18  LDR R0,[R4,#8]         ; bytes: 08 00 94 E5
```

进入 case3 时 `state+0x28` 已是 Prepare/Stage 返回的真实 transaction。随后 stock 立即把 recovery record `status=2` 与 transaction fields 写入游戏 model，并启动游戏保存。

因此 B 在此点：

```text
BULK_PENDING -> TX_BOUND -> GAME_SAVE_STARTED
```

Hook 后重放原始 `LDR R0,[R4,#8]`，回跳 `0x002B1E1C`。

### 3.2 case4 → case5：GAME_SAVE_OK

case4：

```asm
0x002B1F24  ... poll game-save callback
0x002B1F3C  CMP R0,#1
0x002B1F40  MOVEQ R0,#5
```

只有 callback 明确返回 `1` 才进入 case5。

case5 入口：

```asm
0x002B1F4C  LDR R0,[R4,#8]         ; bytes: 08 00 94 E5
```

所以 `0x002B1F4C` 是 `GAME_SAVE_OK` 的可靠阶段 Hook；进入这里已经能证明游戏保存成功。

Hook 后重放原始指令并回跳 `0x002B1F50`。

### 3.3 case9：REMOTE_COMPLETE_STARTED

入口：

```asm
0x002B20A0  LDR R0,[R4,#0x40]      ; bytes: 40 00 94 E5
0x002B20A4  LDR R1,[R4,#0x28]
0x002B20A8  MOV R2,#0
0x002B20AC  BL  0x001D5D74         ; CompleteUpdateBankObject
```

因此 `0x002B20A0` 在调用 Complete 之前把 stage 推进到：

```text
REMOTE_COMPLETE_STARTED
```

Hook 后重放 `LDR R0,[R4,#0x40]`，回跳 `0x002B20A4`。

## 4. 既有 state16 Hook

V3 已经 Hook：

```text
0x002AF460
original bytes: 70 40 2D E9
```

B 不需要再增加第二个 state16 branch；只需在 bulk apply 成功后持久化 staged marker 初始态 `BULK_APPLIED`。

## 5. B 最小 Hook surface

```text
existing:
0x002AF460  bulk apply dispatch

new:
0x002B1E18  TX_BOUND + GAME_SAVE_STARTED
0x002B1F4C  GAME_SAVE_OK
0x002B20A0  REMOTE_COMPLETE_STARTED
0x002A8AD0  mismatch -> exact marker + stage -> stock Complete/Rollback
```

## 6. 为什么不用改 BNE

原版两条 game mismatch branch：

```text
0x002A89D0
0x002A89E0
```

已经自然汇聚到 `0x002A8AD0`。在 funnel 处 Hook：

- 只覆盖 1 条 stock 指令；
- fail-closed 时仍回原版 error；
- 不破坏 local/game compare 本身；
- 可以根据 marker stage 选择 case5/6。

## 7. Build guard

`bank/tools/verify_recovery_hook_sites.py --variant B` 必须在生成 IPS 前校验：

```text
.code size / SHA-256
0x002AF460 bytes
0x002B1E18 bytes
0x002B1F4C bytes
0x002B20A0 bytes
0x002A8AD0 bytes
```

任一不符都拒绝生成 IPS。
