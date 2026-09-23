# Pokémon Bank Official Bulk Sync 异常事务恢复 Hook 设计

> 分支：`feature/official-bank-recovery-research`
>
> 基线：`feature/official-bank-bulk-sync`
>
> 目标：解决 Official Bulk Sync 正常保存大多成功、但网络偶发失败后，同一份未恢复/未修改游戏存档再次联动时被 state 18 判定为 transaction mismatch 并显示 Trainer/save mismatch 的问题。

## 1. 已确认的根因边界

原版 Bank v1.5 的阻塞点不是普通 Trainer ID 比较。

state 18 `0x002A8760` 会取得服务器 pending `BankTransactionParam`，然后依次尝试：

1. Bank-local persistent recovery record；
2. 当前联动游戏 save 内的 recovery record。

核心匹配条件是：

```text
server.dataId == recovery.dataId
&&
server.curVersion == recovery.curVersion
```

匹配后再由 recovery record 的：

```text
status == 1 -> Rollback
status == 2 -> Commit
```

决定恢复方向。

若两份本地 recovery record 都不能和 server pending transaction 对上，才进入 state 18 case 8/9；case 9 使用服务器 metadata 里的训练家名称/ID 构造错误提示，因此 UI 看起来像“Trainer ID Error”。

## 2. 为什么不能直接 NOP state 18 mismatch

state 18 一旦认为 record 匹配，会继续使用该 record 内的：

```text
dataId
transactionPassword
curVersion
updateVersion
size
status
```

调用原版 Commit/Rollback。

因此以下改法均禁止：

```text
ValidateTrainer = true
NOP 所有 BNE
无条件把 game record 当 server record
无条件 force Complete
```

因为旧 record 的 `transactionPassword` 或版本号可能属于另一事务。

## 3. 安全目标：只恢复本工具产生的 bulk-only transaction

实验版只处理满足全部条件的 session：

```text
A. 本次普通游戏联动确实执行过 Official Bulk Sync Apply
B. 随后 stock PrepareUpdate 已生成真实 BankTransactionParam
C. 本工具持久化的 marker 已绑定该 exact transaction
D. 下一次启动 server pending transaction 与 marker 全字段匹配
E. state 18 正常 local/game recovery record 又无法匹配
```

只有 A-E 全部成立，才允许进入工具的 recovery-only 分支。

普通手动 Game ↔ Bank 移动、没有 bulk apply 的保存、不同 profile、不同 transaction、marker 损坏或旧 marker 均保持 stock 行为。

## 4. 两段式 marker 生命周期

### Phase 0：无 marker

```text
normal Bank session
```

不介入恢复。

### Phase 1：BULK_PENDING

Official Bulk Sync 在 state 16 成功 Apply `bulk_import.bin` 后：

```text
marker.magic   = OBRX
marker.profile = active profile
marker.flags   = BULK_PENDING
transaction fields = 0
checksum valid
```

此阶段只能证明“本次 session 发生过 bulk apply”，不能用于恢复，因为 PrepareUpdate 尚未生成 transactionPassword/version。

API：

```c
OfficialRecoveryMarker_EncodePending(marker, profile)
OfficialRecoveryMarker_IsPending(marker, profile)
```

### Phase 2：TX_BOUND / BULK_APPLIED

stock `BankSaveState_Update` 完成 Prepare/Stage 后，进入写游戏 recovery record 的 case 3 前，当前 transaction 已经存在于保存状态对象中。

此时把 pending marker 升级为 exact transaction marker：

```text
dataId
transactionPassword
curVersion
updateVersion
size
profile
flags = BULK_APPLIED
checksum
```

API：

```c
OfficialRecoveryMarker_BindTransaction(marker, serverTx, profile)
```

绑定要求：

```text
marker 必须是同 profile 的 BULK_PENDING
```

不能拿一个旧 marker 直接改绑给新 profile/新事务。

### Phase 3：正常保存成功

在 stock Complete 成功并完成 game recovery record 清理后：

```text
删除 / invalidate marker
```

不能把已经完成的 marker 留到下一次 session，否则会增加误恢复风险。

### Phase 4：网络失败后重启

启动查询得到 server pending transaction 后：

```text
OfficialRecoveryMarker_MatchesServer(marker, serverTx, profile)
```

要求 exact match：

```text
dataId
transactionPassword
curVersion
updateVersion
size
profile
BULK_APPLIED flag
```

任意一项不一致均不得启用工具恢复。

## 5. 两个最小 Runtime Hook 点

### Hook A：transaction bind

位置语义：

```text
BankSaveState_Update
case 2: Stage/Upload callback success
    -> case 3
case 3: write GameRecoveryRecord(status=2)
```

应在 case 3 已能访问当前 `BankTransactionParam`、但尚未依赖后续 Complete 结果的位置，把 `BULK_PENDING` marker 绑定成 `TX_BOUND`。

要求：

- 不修改 stock BankTransactionParam；
- 不修改 game recovery record；
- marker 写失败时继续 stock 保存，但不提供工具恢复能力；
- 不因 marker I/O 失败把一次本可成功的 Bank 保存变成失败。

### Hook B：state 18 mismatch recovery

位置语义：

```text
0x002A8760 state18 case4
server.dataId/curVersion vs game recovery record
    match    -> stock commit/rollback selection
    mismatch -> case8/case9 Trainer/save error
```

实验 Hook 不应简单把 compare 改为成功。

正确流程：

```text
stock local record mismatch
stock game record mismatch
        ↓
read TX_BOUND marker
        ↓
marker exact-match current server pending tx ?
        ├─ no  -> stock case8/9
        └─ yes -> build recovery record from CURRENT SERVER TX
                 status = 1 (Rollback)
                 ↓
                 return to stock rollback path
```

关键原则：**transaction context 来自当前 server pending transaction，不来自不匹配的旧 game/local record。**

## 6. 为什么第一版优先 Rollback，不优先 Commit

当 state 18 已经证明本地两份 record 都无法确认事务方向时，工具没有足够证据证明 game-side Pokémon/content 已与 staged BankObject 达到可安全 Commit 的状态。

对 bulk-only session，优先目标是：

```text
解除 server pending transaction
恢复 Bank 可使用性
避免把不确定 staged object 正式提交
```

所以第一版实验策略是：

```text
exact marker match + stock mismatch -> Rollback
```

而不是：

```text
exact marker match -> Commit
```

后续只有在实机故障注入证明某个窗口可安全判定“game save 已成功且 staged Bank 应提交”时，才考虑细分 Commit。

## 7. Marker 文件的持久化要求

建议独立文件，例如：

```text
/3ds/Bank/official_bulk_recovery.bin
```

大小固定：

```text
48 bytes
```

写入必须：

```text
open/create
set exact size
write all bytes
flush
close
```

读取必须校验：

```text
magic
version
profile
flags
checksum
exact transaction match
```

损坏 marker 的行为永远是：

```text
忽略工具恢复 -> 回到 stock mismatch
```

而不是尝试修复猜测字段。

## 8. 正常完成与失败后的 marker 清理

必须覆盖：

| 场景 | marker 行为 |
|---|---|
| bulk 未 Apply | 不创建 |
| bulk Apply 后用户不保存退出 | 删除/失效 pending marker |
| Prepare 前保存失败 | 删除/失效 pending marker |
| transaction 已绑定但 stock 正常 Complete | 删除/失效 bound marker |
| transaction 已绑定且网络异常 | 保留 bound marker供下次 recovery |
| 下次 recovery Rollback 成功 | 删除/失效 bound marker |
| marker 与 server tx 不匹配 | 不使用；可保留诊断副本，但不能自动执行 |

## 9. 当前实现状态

已实现并 host-test：

```text
official_recovery_probe.*
    stock recovery decision model

official_recovery_marker.*
    48-byte OBRX marker
    checksum
    exact transaction match
    BULK_PENDING -> exact transaction bind
```

当前 marker API：

```c
OfficialRecoveryMarker_EncodePending
OfficialRecoveryMarker_IsPending
OfficialRecoveryMarker_BindTransaction
OfficialRecoveryMarker_MatchesServer
```

仍未接入 production runtime：

```text
state16 marker file write
state7 transaction bind
state18 recovery-only rollback
normal Complete/rollback marker cleanup
```

## 10. 机器码级阻塞项

生成可实机安装的 IPS 前，还必须从已验证 stock `.code`：

```text
size   = 0x2AC000
SHA256 = 2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

取得：

1. state 7 case 3 的精确 ARM 指令边界；
2. state 18 case 4 的三项 compare / mismatch branch 精确地址与原始 bytes；
3. 可安全 branch 到 shim 的覆盖长度；
4. 回跳地址与寄存器/flags 约束；
5. patch whitelist。

研究分支已有：

```text
bank/tools/disassemble_recovery_gate.py
```

用于 hash/size 校验后对 `0x002A8760..0x002A8D30` 做机器码反汇编。

## 11. 代码空间约束

现有 V3 text-tail：

```text
0x00313910 .. 0x00314000
```

只有 `0x6F0` bytes，并且原 bulk payload 已接近 CI 的 1680-byte text budget。

因此正式实现前必须重新核算：

- marker/runtime helper 是否能与现有 FS helper 复用；
- recovery shim 是否可主要写成极小 ARM assembly；
- 是否存在静态确认不可达、且 RX 的 stock function body 可复用。

禁止再次把 mapped `.data` 当 code cave。

## 12. 第一版实机验证成功标准

网络故障后出现原版 mismatch 时，实验 build 必须满足：

1. 无 marker：仍显示原版 mismatch；
2. pending-only marker：仍显示原版 mismatch；
3. marker profile 不同：仍显示原版 mismatch；
4. marker transaction 任一字段不同：仍显示原版 mismatch；
5. exact TX_BOUND marker：进入受控 stock Rollback；
6. Rollback 成功后 marker 清理；
7. 随后重新联动可正常进入 state 16/Bank UI；
8. 下一次正常 bulk save 可正常 Complete；
9. 普通手动 Game ↔ Bank 操作不受影响。

在以上实机矩阵完成前，所有 runtime recovery patch 必须标记：

```text
EXPERIMENTAL / STATICALLY VERIFIED ONLY
```
