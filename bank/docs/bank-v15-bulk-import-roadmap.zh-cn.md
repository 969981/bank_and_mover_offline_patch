# Pokémon Bank v1.5 Bulk Import 研究与开发路线

本文定义 `research/saveboxes-transaction-analysis` 分支下一阶段的研究目标、技术方案、开发拆分与验收标准。

目标不是重写 Pokémon Bank 的联网协议，而是先把 **Bank v1.5 完整 `0xBB518` BankObject 的槽位数据与后半段 metadata 语义研究清楚**，实现一个可以离线验证的批量导入链；在离线闭环稳定后，再把同一套导入逻辑接到原版 Bank 的官方保存事务中。

相关基础分析：

- [`code-analysis.zh-cn.md`](./code-analysis.zh-cn.md)
- [`saveboxes-transaction-analysis.zh-cn.md`](./saveboxes-transaction-analysis.zh-cn.md)

---

## 1. 项目目标

最终希望实现以下工作流：

```text
PC / 离线准备
============
现有 bankdata.bin（0xBB518）
        |
        v
PC 端编辑 / 批量替换 100 Box
        |
        v
bulk_import.bin（完整 0xBB518 BankObject 镜像）

3DS 离线验证
============
Pokémon Bank Offline Mode
        |
        v
加载当前 BankObject
        |
        v
ApplyBulkImport()
        |
        v
进入原版 Bank Box UI 检查
        |
        v
正常离线保存
        |
        v
退出并重新加载验证

3DS 官方同步
============
Pokémon Bank Official Mode
        |
        v
原版登录 / transaction recovery / BankObject download
        |
        v
fresh server BankObject
        |
        v
ApplyBulkImport()
        |
        v
进入原版 Bank Box UI 检查
        |
        v
原版 BankSaveState 正常保存
        |
        +--> PrepareUpdateBankObject
        +--> HPP / HTTPS upload
        +--> CompleteUpdateBankObject
        `--> failure: RollbackBankObject
        |
        v
重新下载服务器 BankObject 做 round-trip 验证
```

最终用户体验应当是：

```text
最多 100 Box / 3000 Pokémon
        |
        v
一次 Bulk Import
        |
        v
一次 Pokémon Bank 官方保存事务
        |
        v
Pokémon HOME
```

这样可以避免为了大量 Pokémon 反复执行多轮 Mover / Bank 传送。

---

## 2. 项目边界

### 2.1 本阶段要做

1. 完善 Bank v1.5 文件地图，尤其是 `0x0ACA44 ~ 0x0BB518` current-format 扩展区。
2. 研究 3000 个 Bank 槽对应的：
   - format tag；
   - source software ID；
   - update timestamp；
   - clear / move / copy / overwrite 时的联动规则。
3. 判断以下 aggregate / summary 数据是否必须由导入器主动维护：
   - `8 × 0x44` source-game summaries；
   - `0x7260` Pokedex-like aggregate；
   - deposit / withdrawal counters；
   - `0x100` tail flags / reserved。
4. 实现 PC 端完整 Bank 镜像编辑与验证工具。
5. 实现 3DS 端统一 `ApplyBulkImport()`。
6. 先完成 Offline Mode 的完整 save / reload 闭环。
7. 离线验证通过后，再接入 Official Mode，复用原版 save / upload / commit / rollback。

### 2.2 本阶段不做

1. 不重写 Nintendo / NEX / HPP 服务器协议。
2. 不自行生成 `transactionPassword`、`curVersion`、`updateVersion` 等官方事务参数。
3. 不把旧 `bankdata.bin` 的远端身份字段或 transaction context 直接覆盖到 fresh server BankObject。
4. 不在第一版实现自动上传；先要求用户进入 Box UI 人工检查后再正常保存。
5. 不要求第一版完整命名 Pokedex aggregate 与 tail 的全部 bitfield；只研究是否阻塞安全导入。
6. 不在 format/tag/source/timestamp 尚未确认前实现正式 100 Box 上传。

---

## 3. 当前已经确认的技术基线

目标应用：

```text
Title ID    00040000000C9B00
Bank        v1.5
BankObject  0xBB518 bytes
```

原版 BankObject 运行时对象：

```text
obj_bank
  +0x00  vtable = 0x003626FC
  +0x08  serialized bank file body
```

BankObject vtable 已确认：

| Slot | 地址 | 作用 |
|---:|---:|---|
| `+0x08` | `0x002CB870` | 序列化当前格式 BankObject |
| `+0x0C` | `0x0023650C` | 把输入数据载入对象 `+8` |
| `+0x10` | `0x002CB864` | 返回 `0xBB518` |
| `+0x14` | `0x00116294` | 初始化当前格式 |
| `+0x18` | `0x002BA490` | 载入并升级 `0xACA48` legacy Bank 格式 |
| `+0x1C` | `0x002CB84C` | 当前格式版本检查 |

当前格式加载的最低检查包括：

```text
u16(data + 0x15C) == 2
u16(data + 0x15E) == 100
```

目前没有在 BankObject 这一层识别到完整文件级 checksum、MAC、压缩或加密流程。远端上传事务是另一层逻辑，不应与 BankObject 本体格式混为一谈。

---

## 4. Bank v1.5 当前文件地图

当前已确认的物理布局：

| 文件偏移 | 长度 | 内容 | 当前状态 |
|---:|---:|---|---|
| `0x000000` | `0x17C` | Header、名称、版本、状态字段 | 部分语义已知 |
| `0x00017C` | `100 × 0x1B56` | 100 个 Bank Box，每盒 30 个 `0xE8` Pokémon + box metadata | 主体已知 |
| `0x0AAF14` | `30 × 0xE8` | Transfer Box 30 槽 | 已知 |
| `0x0ACA44` | `3000` | Bank 3000 槽并行 format tag | **重点研究** |
| `0x0AD5FC` | `30` | Transfer Box 并行 tag | 已知存在，语义需继续映射 |
| `0x0AD61A` | `2` | reserved / alignment | 未阻塞 |
| `0x0AD61C` | `8 × 0x44` | source-game summaries | **需判断是否阻塞导入** |
| `0x0AD83C` | `0x7260` | Pokedex-like aggregate | **需判断是否自动派生** |
| `0x0B4A9C` | `4` | deposit / withdrawal counters | 需验证更新规则 |
| `0x0B4AA0` | `3000` | Bank 槽 source software ID | **重点研究** |
| `0x0B5658` | `3000 × 8` | Bank 槽 update timestamp | **重点研究** |
| `0x0BB418` | `0x100` | tail flags / reserved | 低优先级 |

### 4.1 legacy `0xACA48` 与 current `0xBB518` 的边界

需要特别注意：

- PKHeX 所识别的旧 Pokémon Bank `Bank7` 结构长度为 `0xACA48`；
- 当前 Bank v1.5 的扩展 tag 表实际从 `0x0ACA44` 开始；
- 因此不能简单把 `0xACA48 ~ 0xBB518` 称为“全部新增区”。

研究时应按 **current-format 实际字段边界 `0x0ACA44`** 处理，同时保留对 legacy loader `0x002BA490` 的静态分析，用于确认升级过程如何初始化新增 metadata。

---

## 5. 统一槽位索引模型

后续所有研究、PC 工具和 3DS 导入器必须使用同一套 slot-index 公式，禁止散落 magic offset。

```c
#define BANK_BOX_COUNT          100
#define BANK_SLOTS_PER_BOX      30
#define BANK_SLOT_COUNT         3000

#define BANK_BOX_BASE           0x00017C
#define BANK_BOX_STRIDE         0x001B56
#define BANK_PKM_SIZE           0x0000E8

#define BANK_TAG_BASE           0x0ACA44
#define BANK_SOURCE_BASE        0x0B4AA0
#define BANK_TIMESTAMP_BASE     0x0B5658
```

逻辑索引：

```c
slotIndex = box * 30 + slot;
```

对应字段位置：

```c
pkmOffset =
    BANK_BOX_BASE
    + box * BANK_BOX_STRIDE
    + slot * BANK_PKM_SIZE;

tagOffset =
    BANK_TAG_BASE
    + slotIndex;

sourceSoftwareOffset =
    BANK_SOURCE_BASE
    + slotIndex;

timestampOffset =
    BANK_TIMESTAMP_BASE
    + slotIndex * 8;
```

P0 阶段完成后，PC diff 工具和 3DS patch 都必须从统一定义生成这些地址。

---

## 6. Route A：完整 Bank 镜像方案

第一条正式实现路线固定为：

```text
现有 bankdata.bin
        |
        v
PC 编辑 / 批量替换
        |
        v
bulk_import.bin
完整 0xBB518 BankObject 镜像
        |
        v
3DS Offline / Official Bank
        |
        v
ApplyBulkImport()
```

### 6.1 为什么 `bulk_import.bin` 仍然使用完整 `0xBB518`

完整镜像有三个优势：

1. 可以直接从 Download Mode / Offline Mode 取得真实 Bank v1.5 模板；
2. PC 工具可以在不理解全部未知字段时原样保留它们；
3. 后续可以直接做 `before / bulk / after` 三方 binary diff。

但它的角色是 **编辑模板和导入数据源**，不是“直接原样上传的服务器对象”。

### 6.2 3DS 端禁止整文件覆盖

联网场景下禁止：

```c
memcpy(runtimeBank, bulkImport, 0xBB518);
```

正确设计：

```text
fresh server BankObject
        |
        +--> 保留 server/account/header/unknown identity state
        |
        v
ApplyBulkImport()
        |
        +--> 复制允许覆盖的 Pokémon / box 数据
        +--> 同步已确认的 per-slot metadata
        +--> 必要时更新已验证 aggregate
        |
        v
runtime BankObject
```

这样可以避免把旧镜像中的 account identity、remote content ID 或其他未知会话状态重新写回当前官方对象。

---

## 7. ApplyBulkImport 的目标接口

Offline Mode 和 Official Mode 必须共用同一个核心实现：

```c
bool ApplyBulkImport(
    BankObject *runtimeBank,
    const BankV15Image *bulkImage,
    BulkImportMode mode
);
```

第一版仅实现：

```text
REPLACE_ALL_BOXES
```

语义：

```text
bulk Box 1 Slot 1    -> runtime Box 1 Slot 1
...
bulk Box 100 Slot30 -> runtime Box 100 Slot30

bulk occupied slot   -> replace
bulk empty slot      -> clear runtime slot
```

第一版不做：

```text
APPEND
MERGE_BY_EMPTY_SLOT
DEDUPE
AUTO_UPLOAD
```

这些属于后续体验优化。

---

## 8. Offline 与 Official 的统一架构

### 8.1 Offline

```text
load local bankdata.bin
        |
        v
ApplyBulkImport()
        |
        v
stock Bank Box UI
        |
        v
existing local stage / commit / rollback
        |
        v
bankdata.bin
```

### 8.2 Official

```text
stock authentication
        |
        v
stock transaction recovery
        |
        v
stock BankObject download
        |
        v
fresh server BankObject loaded
        |
        v
ApplyBulkImport()
        |
        v
stock Bank Box UI
        |
        v
stock state 7 save
        |
        +--> SerializeAndStage
        +--> PrepareUpdateBankObject
        +--> HPP upload
        +--> CompleteUpdateBankObject
        `--> RollbackBankObject on failure
```

核心原则：

> 离线和联网只允许最后的 commit backend 不同；BankObject mutation 逻辑必须完全共用。

这样 Offline Mode 可以承担绝大部分格式与导入测试，Official Mode 只验证服务器 round-trip。

---

## 9. 研究任务拆分

## R0：固化 current-format 文件地图

### 目标

建立统一、可执行的 Bank v1.5 layout 定义。

### 任务

- [ ] 把现有 offset / size / stride 整理为 C/C++ 与 PC 工具共享常量。
- [ ] 验证 3000 个 `PKM / tag / source / timestamp` 索引一一对应。
- [ ] 静态分析 `0x002BA490` legacy upgrade，记录 `0xACA48 -> 0xBB518` 时新增区初始化方式。
- [ ] 确认 box metadata `0x26` 字节内部的 name/index 等现有语义。
- [ ] 输出一份字段可信度表：Confirmed / Inferred / Unknown。

### 验收

给任意 `(box, slot)`，工具可以准确定位其 Pokémon、tag、source software、timestamp，不存在 magic-offset 分叉。

---

## R1：Bank format tag 语义

### 核心问题

- 空槽 tag 是什么？
- PK6、PK7 是否使用不同 tag？
- Gen5 经 Mover、VC Gen1/2 经 Bank 后分别是什么 tag？
- Bank 内 move/copy 是否保持 tag？
- clear 时 tag 是否清零或写特殊值？

### 实验矩阵

- [ ] 空槽 -> 存入 XY/ORAS Pokémon -> 下载 diff。
- [ ] 删除上述 Pokémon -> 下载 diff。
- [ ] 空槽 -> 存入 SM/USUM Pokémon -> 下载 diff。
- [ ] Gen5/Mover Pokémon 测试。
- [ ] VC Gen1/2 Pokémon 测试。
- [ ] Bank Box A -> Bank Box B move 测试。
- [ ] occupied slot overwrite 测试。

### 产物

```text
BankSlotFormatTag enum / mapping table
```

### 验收

PC 工具可以根据 Pokémon 上下文确定正确 tag，且 Offline save/reload 不产生 tag 异常。

---

## R2：Source Software ID 映射

### 核心问题

`0x0B4AA0 + slotIndex` 的 1-byte source software ID 需要建立来源映射。

### 实验来源

- [ ] XY
- [ ] ORAS
- [ ] SM
- [ ] USUM
- [ ] BW/B2W2 via Mover
- [ ] VC RGBY
- [ ] VC GSC

### 行为测试

- [ ] Bank 内 move 是否保持 source。
- [ ] clear 时 source 是否归零。
- [ ] overwrite 时 source 如何更新。
- [ ] 从 Bank 取回游戏再重新 deposit 是否改变 source。

### 验收

得到稳定 `sourceSoftwareId -> origin context` 映射，并能解释 before/after diff。

---

## R3：Update Timestamp

### 核心问题

`0x0B5658 + slotIndex * 8` 的 64-bit timestamp：

- 编码；
- 字节序；
- epoch / packed datetime；
- 更新时机。

### 实验

- [ ] 在已知主机时间存入 Pokémon，记录原始 `u64`。
- [ ] 间隔固定时间后存入第二只，比较 delta。
- [ ] move 测试。
- [ ] copy 测试。
- [ ] clear 测试。
- [ ] overwrite 测试。
- [ ] 从游戏 deposit 与 Bank 内整理行为对比。

### 验收

能够从 raw timestamp 得到稳定的人类时间解释，并确定每类 mutation 是否应更新它。

---

## R4：Source-game summaries

区域：

```text
0x0AD61C
8 × 0x44
```

### 目标

不是第一时间完全命名所有字段，而是判断 **Bulk Import 是否必须主动维护它们**。

### 实验

- [ ] 仅修改 slot/tag/source/time 后执行 Offline save/reload。
- [ ] 比较 summary 是否由原版保存流程自动变化。
- [ ] 不同来源游戏 deposit 时比较 8 个 entry 的变化。
- [ ] 确认 entry 与 source software / connected game 的关系。

### 决策

若原版会重新派生，则 V1 Builder 不生成；若不派生且缺失会破坏逻辑，再补对应 writer。

---

## R5：Pokedex-like aggregate

区域：

```text
0x0AD83C
size = 0x7260
```

### 目标

优先回答：是否阻塞 Bulk Import。

### 实验

- [ ] 在服务器原本不存在某 species/form 的情况下仅修改槽数据。
- [ ] Offline save/reload 后比较 aggregate。
- [ ] Official round-trip 后比较 aggregate。
- [ ] 查找 Bank Box mutation / deposit 路径中对此区域的写引用。

### 决策

如果原版 UI/save 会重新计算，则 V1 不实现 aggregate generator；否则再单独逆结构与更新函数。

---

## R6：Counters 与 Tail

### Counters

```text
0x0B4A9C
4 bytes
```

研究 deposit / withdrawal / Bank-internal move 是否修改，以及它是否只用于当前操作统计。

### Tail

```text
0x0BB418
0x100 bytes
```

优先做引用扫描与差分分类，不要求 V1 完整命名所有 bit。

### 验收

明确哪些字节必须由 Bulk Apply 维护，哪些必须保留 fresh server 值。

---

## 10. 开发任务拆分

## D0：Binary Diff / Research Tooling

优先实现研究工具，而不是先做正式导入器。

功能：

```text
inspect
validate
diff
slot-diff
metadata-diff
```

输出应按 slot 聚合：

```text
Box 01 Slot 00
  Pokémon  changed
  Tag      0x?? -> 0x??
  Source   0x?? -> 0x??
  Time     0x???????????????? -> ...
```

并单独显示：

```text
source summary changes
aggregate changed ranges
counter changes
tail changed ranges
```

完成后，R1/R2/R3 的实验效率会明显提升。

---

## D1：BankV15Image PC 模型

建立：

```text
BankV15Image
├── Header
├── Boxes[100][30]
├── BoxMetadata[100]
├── TransferBox[30]
├── BankTags[3000]
├── TransferTags[30]
├── SourceSummaries[8]
├── PokedexAggregate
├── Counters
├── SourceSoftware[3000]
├── UpdateTimestamp[3000]
└── Tail
```

要求：

- [ ] 严格验证文件长度 `0xBB518`；
- [ ] 检查 current format version / box count；
- [ ] round-trip parse/serialize 必须 byte-identical；
- [ ] 未知字段默认 opaque preserve；
- [ ] 禁止自动“修复”未知字节。

---

## D2：PC 端 BankBulkBuilder V1

第一版只支持完整 Bank 模板：

```text
bankdata.bin
    -> edit
    -> bulk_import.bin
```

最小命令建议：

```text
bankbulk inspect bankdata.bin
bankbulk validate bankdata.bin
bankbulk diff before.bin after.bin
bankbulk replace-slot ...
bankbulk clear-slot ...
bankbulk copy-box ...
bankbulk export bulk_import.bin
```

V1 不要求 GUI。

PKHeX.Core `.pk6/.pk7` 导入属于后续 D7，不应阻塞核心闭环。

---

## D3：3DS ApplyBulkImport Core

实现统一核心：

```c
ApplyBulkImport(runtimeBank, bulkImage, REPLACE_ALL_BOXES)
```

第一版只允许白名单字段覆盖。

建议白名单按研究结果逐步开放：

```text
Stage A
- Pokémon slot payload
- box metadata

Stage B
- format tag
- source software
- timestamp

Stage C
- only proven required aggregate fields
```

禁止覆盖：

```text
account identity
remote content identifiers
transaction descriptors
unknown server/session state
```

---

## D4：Offline Mode Bulk Import UI

流程：

```text
load bankdata.bin
        |
        v
find bulk_import.bin
        |
        v
validate
        |
        v
显示数量 / 模式 / 风险提示
        |
        +--> B: cancel -> stock flow
        |
        `--> A: ApplyBulkImport
                    |
                    v
              stock Bank Box UI
                    |
                    v
              manual inspect
                    |
                    v
              normal offline save
```

第一版不自动保存。

建议提示：

```text
Bulk Import detected
Mode: Replace All 100 Boxes
Pokémon: N

A: Apply
B: Cancel
```

---

## D5：Offline Regression Suite

必须在联网前完成。

测试梯度：

- [ ] 无修改 round-trip；
- [ ] 1 Pokémon；
- [ ] 1 occupied -> empty；
- [ ] 1 empty -> occupied；
- [ ] overwrite；
- [ ] Bank internal move；
- [ ] 1 Box；
- [ ] 10 Boxes；
- [ ] 100 Boxes；
- [ ] 3000 occupied slots；
- [ ] PK6 / PK7 mixed；
- [ ] restart + reload；
- [ ] save twice；
- [ ] cancel without save；
- [ ] invalid `bulk_import.bin`；
- [ ] short file / wrong version / wrong box count。

M2 前不得跳过这些测试直接做大规模官方上传。

---

## D6：Official Mode Integration

只在 Offline 闭环稳定后实现。

Hook 位置应当在：

```text
state 16 BankDataSyncState_Update
        |
        v
complete server BankObject loaded
        |
        v
accompanying metadata sync complete
        |
        v
[Bulk Apply substate]
        |
        v
Bank Box UI
```

不要在 `0x002D11B0` HTTP/network callback 内执行完整 SD 文件读取和 3000 槽 mutation。

保存路径保持 stock：

```text
0x002B1CF8 BankSaveState_Update
        |
        v
0x002B2320 BankSave_SerializeAndStage
        |
        v
0x002A2504 BankRemote_StageFileUpdate
        |
        +--> HPP upload
        |
        +--> 0x001D5D74 Commit
        `--> 0x001D5C28 Rollback
```

---

## D7：PKHeX / PK6 / PK7 Import

这是 Route A 稳定后的第二阶段体验功能。

PC 端使用 PKHeX.Core 解析：

```text
.pk6
.pk7
PKHeX exported box folders
```

统一转成 BankV15Image，再输出 `bulk_import.bin`。

不要假设 `.pk6/.pk7` 文件一定已经是可以直接 memcpy 的 `0xE8` encrypted stored representation；导入器应通过 PKHeX.Core 正规解析后重新生成适合 Bank slot 的表示。

---

## 11. 验证策略

## 11.1 Offline 是主要开发验证环境

Bulk Import 本身全部先在 Offline Mode 测：

```text
source bankdata.bin
        |
        v
ApplyBulkImport
        |
        v
Bank UI
        |
        v
local save
        |
        v
restart
        |
        v
reload
        |
        v
binary / semantic diff
```

只要 M2 没完成，就不进入大规模官方上传测试。

## 11.2 Official 只验证服务器接受与 round-trip

第一次官方测试严格限制为 1 Pokémon：

```text
server_before.bin
        |
        v
Official login / download
        |
        v
ApplyBulkImport
        |
        v
manual inspect
        |
        v
stock save / upload / commit
        |
        v
Download Mode re-download
        |
        v
server_after.bin
```

保存：

```text
server_before.bin
bulk_import.bin
runtime_expected.bin
server_after.bin
```

比较：

```text
Pokémon slot
format tag
source software
timestamp
source summaries
Pokedex aggregate
counters
tail
```

验证成功后再扩大：

```text
1 -> 30 -> 300 -> 1500 -> 3000 Pokémon
```

---

## 12. 里程碑

## M0：文件地图可执行化

完成 R0 + D0。

验收：

- 任意槽位 metadata 地址可自动计算；
- diff 工具可以按槽位报告变化；
- current/legacy 边界已经明确记录。

## M1：Per-slot metadata 已掌握

完成 R1 + R2 + R3。

验收：

- format tag 映射明确；
- source software ID 映射明确；
- timestamp 编码与 mutation 行为明确；
- clear / move / overwrite 的联动可以复现。

## M2：100 Box Offline Bulk Import 闭环

完成 D1 + D2 + D3 + D4 + D5，以及必要的 R4/R5/R6。

验收：

```text
bulk_import.bin
    -> Offline Apply
    -> Box UI
    -> local save
    -> restart
    -> reload
```

100 Box 稳定，无跨槽 metadata 污染，空槽、覆盖槽和 mixed PK6/PK7 正常。

到 M2 时，“100 Box 一次导入”的核心技术已经成立。

## M3：Official Server Round-trip

完成 D6。

验收：

```text
1 Pokémon
-> official stock save
-> commit
-> re-download
-> expected == server result
```

然后逐步扩大到 100 Box。

## M4：PKHeX Bulk Builder

完成 D7。

验收：

```text
PKHeX .pk6/.pk7 / box folders
        -> BankBulkBuilder
        -> bulk_import.bin
        -> Offline verification
        -> Official sync
```

---

## 13. 优先级

### P0：必须先完成

```text
R0 文件地图固化
D0 Binary diff 工具
R1 format tag
R2 source software ID
R3 timestamp
slot clear/move/overwrite 联动
```

### P1：M2 前必须判断是否阻塞

```text
R4 source-game summaries
R5 Pokedex aggregate
R6 counters / tail
D1 BankV15Image
D2 BankBulkBuilder V1
D3 ApplyBulkImport
D4 Offline UI
D5 Offline regression
```

### P2：离线稳定后

```text
D6 Official Mode integration
server round-trip tests
```

### P3：体验增强

```text
PKHeX.Core .pk6/.pk7 import
box-folder import
GUI
APPEND / MERGE modes
automated post-upload verification
```

---

## 14. 推荐的项目结构

现阶段建议先保持研究与实现分离：

```text
bank/
├── docs/
│   ├── code-analysis.zh-cn.md
│   ├── saveboxes-transaction-analysis.zh-cn.md
│   └── bank-v15-bulk-import-roadmap.zh-cn.md
│
├── include/
│   └── bank_v15_layout.inc / .h      # 后续实现
│
└── src/
    ├── bulk_import.c                 # 后续实现
    └── ...

tools/
└── bankbulk/                         # 后续 PC 工具
    ├── inspect
    ├── diff
    ├── validate
    └── builder
```

不应在格式研究尚未稳定时提前建立大量实现文件。

---

## 15. 当前下一步

当前最值得立刻执行的任务顺序：

```text
1. R0：静态分析 legacy upgrade + current metadata layout
2. D0：实现 Bank v1.5 binary/slot diff 工具
3. R1：format tag 实验与映射
4. R2：source software ID 实验与映射
5. R3：timestamp 编码与 mutation 实验
6. 判断 R4/R5/R6 是否由 stock Bank 自动派生
7. D1/D2：PC 完整镜像工具
8. D3/D4/D5：Offline Bulk Import 闭环
9. D6：Official Mode + 1 Pokémon round-trip
10. 扩展到 100 Box
```

当前阶段的主瓶颈不再是 SaveBoxes 网络协议，而是：

> **Bank v1.5 3000 个槽位的 Pokémon payload 与 tag / source / timestamp / aggregate metadata 的一致性规则。**

只要这些规则通过 Offline Mode 被可靠复现，官方同步部分就可以继续复用已经确认的 stock Bank save / stage / upload / commit / rollback 链。