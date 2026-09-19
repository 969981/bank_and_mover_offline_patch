# Official Bank Bulk Sync 设计（feature/official-bank-bulk-sync）

## 目标

在不保留用户可见 Offline / Download Mode 的最终路线中，完全沿用 Pokémon Bank 原版联网流程：

1. 正常登录官方服务；
2. 正常选择任意兼容游戏；
3. state 16 下载官方 fresh BankObject；
4. 在进入原版 Bank Box UI 前自动备份 fresh BankObject；
5. 若存在 `SD:/3ds/Bank/bulk_import.bin`，将其中的 100 个主 Bank Box Pokémon/Box 数据合并到 runtime BankObject；
6. 用户在原版 Bank UI 中检查；
7. 用户执行原版“保存并退出”；
8. 完全沿用原版 PrepareUpdate / HPP upload / CompleteUpdate / rollback；
9. 后续正常进入 HOME transfer 路径。

## 强制契约

### 1. `bulk_import.bin` 是只读输入

`bulk_import.bin` 永远只读。

无论：

- Apply 成功；
- 保存成功；
- 保存失败；
- rollback；
- 用户退出；
- 重启 Bank；

补丁都不得：

- 删除 `bulk_import.bin`；
- 重命名 `bulk_import.bin`；
- 覆盖 `bulk_import.bin`；
- 向 `bulk_import.bin` 回写任何 metadata；
- 生成 `bulk_import_uploaded_*.bin` 之类归档副本。

用户可长期保留同一个 `bulk_import.bin` 并重复使用。

### 2. `bulk_import.bin` 只提供主 100 Box 数据

支持两种输入大小：

- `0xACA48`：PKHeX `Bank7` 兼容视图；
- `0xBB518`：完整 Bank v1.5 镜像。

但无论输入是哪一种，联网路线都只信任并读取：

```text
0x00017C .. 0x0AAF14
```

即 100 个主 Bank Box：

- 30 × `0xE8` Pokémon slot；
- 每盒 `0x26` Box metadata。

`bulk_import.bin` 中下列 current-only metadata 一律不作为权威来源：

- Bank slot format tag；
- source software ID；
- per-slot timestamp；
- Transfer Box metadata；
- source summaries；
- NKZT block；
- counters；
- tail flags；
- account/header/remote identifiers。

## runtime BankObject 合并模型

```text
fresh server BankObject
        +
bulk_import main 100 Boxes
        +
metadata writer (runtime/session derived)
        =
runtime candidate BankObject
```

### 永远保留 fresh server/runtime 的区域

- Header / identity-bound fields；
- remote content identifiers；
- Transfer Box；
- source summaries；
- NKZT block；
- counters；
- tail；
- 所有未知 account/session-bound 数据。

### 主 Box Pokémon/Box metadata

由 `bulk_import.bin` 覆盖。

## slot-aware metadata writer

对每个 slot 比较：

```text
fresh server slot
vs
bulk slot
```

V1 策略：

### unchanged

Pokémon payload 完全相同：

- Pokémon：保持；
- tag：保持 fresh server；
- source：保持 fresh server；
- timestamp：保持 fresh server。

### empty -> occupied

- 写入 bulk Pokémon；
- tag：按 stock-like insert 规则生成；
- source：取当前联动游戏 software ID；
- timestamp：取当前时间，编码采用已研究的 Bank timestamp 格式。

### occupied -> occupied（payload changed）

- 写入 bulk Pokémon；
- tag：按 stock-like replace 规则生成；
- source：更新为当前联动游戏 software ID；
- timestamp：刷新为当前时间。

### occupied -> empty

- 清 Pokémon payload；
- V1 默认保留 fresh server 的 tag/source/timestamp，符合现有真实样本中“空槽仍保留历史 metadata”的观察；
- 如后续 stock 行为实验得到更精确规则，再替换此策略。

### empty -> empty

- 保留 fresh server metadata，不主动清零。

## 官方流程 Hook 原则

### Apply 仅允许 normal game-linked Bank 路径

允许：

```text
state 16
```

禁止：

```text
state 28 / HOME transfer full download
```

因此 HOME 路径绝不再次 Apply `bulk_import.bin`。

### 不在 async download callback 中执行 SD I/O

`BankRemote_DownloadSuccessCallback (0x002D11B0)` 只作为“官方下载完成”的证据点。

实际 backup + bulk apply 应放在：

```text
BankDataSyncState_Update (0x002AF460)
```

中，位于：

```text
fresh BankObject 已装载
→ stock sync 完成
→ [custom backup/apply substate]
→ state 25 Bank Box UI
```

## fresh server Bank 自动备份

每次 state 16 官方 BankObject 下载成功、且在任何 bulk 修改之前，保存完整 `0xBB518`：

```text
SD:/3ds/Bank/bankdata_YYYYMMDD_HHMMSS.bin
```

并可额外维护：

```text
SD:/3ds/Bank/bankdata_server_latest.bin
```

备份文件来源必须是“刚下载、尚未 Apply bulk”的 fresh server BankObject。

## 原版上传事务保持完全不变

补丁不得生成、复用或持久化：

- `dataId`；
- `curVersion` / `updateVersion`；
- `transactionPassword`；
- `applicationId`；
- signed URL；
- HTTP headers/form fields；
- login/auth/session state。

用户执行原版保存后继续走 stock：

```text
BankSaveState_Update
→ BankSave_SerializeAndStage
→ BankRemote_StageFileUpdate
→ PrepareUpdateBankObject
→ stock HTTP/HPP upload
→ CompleteUpdateBankObject
→ Commit / Rollback
```

## `bulk_import.bin` 生命周期

由于该文件强制只读：

```text
Apply 前存在
→ Apply
→ 保存成功
→ 仍保持原样存在
```

所以每次重新进入 normal game-linked Bank，如果该文件仍存在，将再次执行相同 Apply。

这属于设计行为，不是错误。

如果用户不希望下次再次 Apply，应由用户自行移走/删除/改名；补丁绝不自动处理该文件。

## D6 开发拆分

- D6A：恢复/保持原版联网入口，不依赖 Offline/Download Mode UI；
- D6B：state 16 fresh BankObject 自动备份；
- D6C：state 16 → custom BulkApply substate；
- D6D：slot-aware metadata writer；
- D6E：保证 state 7 原版保存事务不变；
- D6F：明确 `bulk_import.bin` 全生命周期只读；
- D6G：明确排除 state 28 / HOME；
- D6H：官方服务器 round-trip 分级验证：1 → 30 → 300 → 3000。

## 第一阶段验收

在不自动执行官方保存的情况下：

1. 正常联网进入 Bank；
2. state 16 下载官方 Bank；
3. SD 产生 fresh server timestamp backup；
4. runtime Bank UI 显示 bulk 的主 100 Box；
5. `bulk_import.bin` SHA-256 前后完全一致；
6. HOME/state 28 路径不触发 Apply。

完成后再进行单 Pokémon 的官方 Save + redownload round-trip。
