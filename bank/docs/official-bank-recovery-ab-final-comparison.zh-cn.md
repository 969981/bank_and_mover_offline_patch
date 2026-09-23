# Official Bank Recovery A/B 最终架构对照（2026-09-23）

## 1. 结论

本轮研究已经从“Trainer ID Error 表面现象”推进到 Bank v1.5 的实际事务恢复机制：

```text
真正需要保护的不是 Pokémon Box，也不是 Trainer ID 本身，
而是 server pending transaction 与 durable recovery record 的一致性。
```

根本性改造不是 NOP mismatch，而是：

```text
在 RMC52 / Stage 可能建立 server pending 之前
先把同一 BankTransactionParam 持久化到 Bank-local recovery。
```

这样服务器不再能够先于 durable recovery 进入 pending。

## 2. 验证基线

```text
Pokémon Bank Title ID  00040000000C9B00
.code image base       0x00100000
.code size             0x2AC000
SHA-256                2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
RX tail cave           0x00313910..0x00314000 (0x6F0 bytes)
```

CIA 已确认 NoCrypto，可直接：

```text
CIA -> NCCH -> ExeFS -> compressed .code -> BLZ -> verified stock .code
```

## 3. 为什么 TX_BOUND 必须在 Stage 前

`BankSave_SerializeAndStage @ 0x002B2320`：

```asm
0x002B2494  LDR r3,[r4,#0x28]   ; BankTransactionParam*
0x002B2498  LDRD r0,r1,[r4,#0x40]
0x002B249C  MOV r2,r11
0x002B24A0  BL  0x002A2504      ; BankRemote_StageFileUpdate / RMC52
```

因此 exact tx 在网络请求发出前已经存在。

旧思路是在 case3 / Stage callback 后记录 marker；最终设计前移为：

```text
Pre-RMC52 durable WAL
        ↓
WAL save success
        ↓
才允许 Stage/RMC52
```

## 4. Bulk-only gate

A/B 都只保护 Official Bulk Sync 自己产生的保存事务。

运行时：

```text
0x003ABFFC = BulkSessionFlag
```

```text
state16 start        -> 0
bulk apply success   -> 1
pre-WAL durable      -> clear to 0 before real Stage
```

普通非 Bulk Bank session 保持 stock。

## 5. Variant A：安全 Rollback 优先

分支：

```text
feature/official-bank-recovery-auto-rollback
```

A 使用原版 `status=1` 作为 pre-RMC52 WAL：

```text
Bulk applied
  -> case1 diversion
  -> stock case7 writes exact local RecoveryRecord status=1
  -> local save success
  -> real Stage
```

若之后事务异常：

```text
stock state18 sees exact local status=1
  -> stock Rollback
```

A 最终不需要 state18 Hook。

Production 修改区：

```text
0x002AF460  Bulk V3 entry
0x002B1DE4  pre-WAL case1
0x002B2090  WAL local-save result
0x00313910..0x00314000 RX tail
```

特点：

```text
实现最小
最大化复用 stock recovery
异常时倾向放弃未可靠完成的 Bulk transaction
```

## 6. Variant B：智能 Commit / Rollback

分支：

```text
feature/official-bank-recovery-smart
```

B 使用私有 `status=3` 标识“durable pre-Stage fallback，但尚未决定最终 Commit/Rollback”：

```text
Bulk applied
  -> pre-WAL exact tx status=3
  -> durable local save
  -> real Stage
```

state18 中，stock 已先匹配：

```text
dataId
curVersion
```

B 再匹配：

```text
updateVersion
size
transactionPassword low/high
```

全部 exact 才建立 trusted fallback。

随后查看 stock GameRecoveryRecord：

```text
exact game status=2
  -> stock Commit

没有 durable exact status=2 / game mismatch
  + trusted exact status3 WAL
  -> stock Rollback

foreign/stale WAL
  -> 不授权自动远端操作，保留 stock protection
```

Production 修改区：

```text
0x002AF460
0x002B1DE4
0x002B1FFC
0x002B2090
0x002A8968
0x002A89D0
0x002A89E0
0x002A8A64..0x002A8A7C
0x00313910..0x00314000
```

## 7. A/B 对照

| 场景 | A | B |
|---|---|---|
| 普通非 Bulk 保存 | stock | stock |
| Stage 前 durable fallback | native status=1 | private status=3 |
| Stage 后、game 尚未 durable | Rollback | Rollback |
| game exact status2 已 durable | 不主动智能提升 | Commit |
| foreign/stale recovery | stock protection | stock protection |
| 真正不同存档 | stock protection | stock protection |
| 复杂度 | 低 | 高 |
| 保住已成功 game save 的 Bulk transaction | 较保守 | 更强 |

## 8. 为什么不直接 NOP Trainer mismatch

state18 真正 game recovery mismatch：

```asm
0x002A89D0  BNE  ; dataId mismatch
0x002A89E0  BNE  ; curVersion mismatch
```

直接跳过只能绕过客户端 gate，却不能证明：

```text
transactionPassword
updateVersion
size
```

属于当前 server pending transaction。

因此最终实现坚持：

```text
先恢复/建立事务一致性
再让 stock Commit/Rollback
而不是关闭一致性校验
```

## 9. 自动化验证层

A/B 当前都具备：

1. CIA/ExeFS/BLZ extraction tests；
2. verified stock hook bytes；
3. host recovery-policy regression；
4. real `arm-none-eabi-gcc/as` production objects；
5. real ELF objects imported by Windows armips；
6. RX tail budget gate；
7. production hook-write smoke；
8. final patched-image whitelist verifier；
9. mapped-data image unchanged verifier；
10. IPS replay verifier。

研究过程中 production-object smoke 曾真实捕获：

```text
Undefined external symbol __aeabi_lmul
```

随后 `%60` 算法改成只使用 Thumb-1 友好的 32-bit 运算，避免 libgcc runtime dependency。

## 10. 实机 A/B 对照建议

推荐测试顺序：

```text
先 A
  -> 验证 pre-RMC52 WAL 是否确实消除永久锁

再 B
  -> 在相同故障窗口验证是否能利用 durable game status2 保留事务
```

故障注入窗口：

1. pre-WAL local save 前/中；
2. Stage/RMC52 网络阶段；
3. Stage success -> game recovery 未 durable；
4. game save 中途；
5. game save durable -> local follow-up 未完成；
6. Complete request/response 阶段。

记录：

```text
server pStatus / BankTransactionParam
local recovery 全字段 + status
game recovery dataId/curVersion/status
最终 Commit/Rollback
下次能否正常联动
Bulk 数据最终是否保留
```

当前结论边界：**静态逆向、production build/link、patched-image/IPS 一致性均已验证；真实 3DS 网络故障注入仍需实机确认。**
