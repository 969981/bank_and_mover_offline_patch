# Official Bulk Sync V3：跳过宝可里程 / 奖励 UI

> 分支：`feature/official-bank-bulk-sync-skip-mileage`
>
> 基线：`feature/official-bank-bulk-sync`

## 1. 目标

这个分支只增加一个行为：普通 Pokémon Bank 联动游戏并完成官方 Bank 下载后，直接进入 Bank Box UI，不再进入宝可里程 / 奖励资格与领取状态。

因此以下类型的界面都不会出现：

- “至少要有 10 点宝可里程点数才能领取”；
- 已有足够里程、可以领取的提示；
- 进入奖励领取 UI；
- 与 state 12 / 13 相关的首次奖励 / 里程领取交互。

本分支 **不会自动领取，不会清零，不会修改服务器保存的里程或奖励数据**。

## 2. 原版状态链

普通 Bank 主路径：

```text
state 16  BankDataSync / 下载完整官方 BankObject
   ↓
state 12  RewardEligibility / 判断是否有待领取里程或奖励
   ├─ 无待领取 → state 25
   └─ 有待领取 → state 13 RewardReceive → state 25

state 25  Bank Box UI
```

其中：

```text
RewardEligibilityState_Update = 0x002AD1BC
RewardReceiveState_Update     = 0x002A9750
BankBoxUi_Update              = 0x002A7094
BankFlow_SelectNextState      = 0x002A5580
```

## 3. 为什么不直接 Hook state 12 / 13

如果直接修改 `RewardEligibilityState_Update` 或 `RewardReceiveState_Update`，会改变这些状态本身的语义，而且未来若存在其它合法调用路径，也会一并受影响。

本分支选择在外层状态转移处修改唯一的“普通 Bank 下载成功 → state 12”结果，因此 state 12 / 13 原代码完全保留。

## 4. 精确补丁

地址：

```text
BankFlow_SelectNextState + 0x248
= 0x002A57C8
```

原版指令：

```asm
moveq r0,#12
```

机器码（little-endian）：

```text
0C 00 A0 03
```

修改为：

```asm
moveq r0,#25
```

机器码：

```text
19 00 A0 03
```

所以新的普通 Bank 流程为：

```text
state 16
→ state 25 Bank Box UI
```

而不是：

```text
state 16
→ state 12
→ [state 13]
→ state 25
```

## 5. 与 Official Bulk Sync 的关系

Official Bulk Sync V3 的 `BankDataSyncState_Update @ 0x002AF460` Hook 完全保留。

因此完整路径变为：

```text
原版登录 / 选择游戏
→ state 16 下载 fresh server BankObject
→ V3 backup + bulk apply
→ BankFlow_SelectNextState
→ 直接 state 25
→ 原版 Bank Box UI
→ 用户原版保存
→ 原版 PrepareUpdate / HPP / CompleteUpdate / Rollback
```

本分支不改变：

- `bulk_import.bin` 只读契约；
- fresh BankObject 自动备份；
- slot-aware metadata writer；
- 原版 Bank 保存 / 上传事务；
- HOME 的 state 28 / 29 / 27 路径。

## 6. 数据语义

因为 state 12 / 13 根本不会创建，所以这次修改不是“领取后隐藏弹窗”，而是：

```text
不检查领取 UI
不执行领取 UI
不自动领取
不写回里程值
不清零
```

服务器上的里程 / 奖励数据保持原状，之后若换回未屏蔽版本，原版 Bank 仍可按自己的状态继续判断与显示。

## 7. 静态保护

`verify_official_bulk_sync.py` 在这个分支额外允许：

```text
0x002A57C8 .. 0x002A57CC
```

并强制验证：

```text
stock   = 0C 00 A0 03   ; MOVEQ r0,#12
patched = 19 00 A0 03   ; MOVEQ r0,#25
```

另外 `skip_mileage_contract_test.py` 强制：

- 必须在 `BankFlow_SelectNextState + 0x248` 做旁路；
- 必须选择 state 25；
- 禁止直接 `.org RewardEligibilityState_Update`；
- 禁止直接 `.org RewardReceiveState_Update`。

## 8. 实机验证

建议：

```text
H0
不放 bulk_import.bin
→ 正常登录
→ 选择游戏
→ 不出现任何里程/奖励提示
→ 直接进入 Bank Box

H1
放 bulk_import.bin
→ fresh Bank 下载/备份
→ bulk 显示
→ 同样直接进入 Bank Box
```

如果 H0/H1 都正常，再继续 Official Bulk Sync 的 1 Pokémon server round-trip 验证。
