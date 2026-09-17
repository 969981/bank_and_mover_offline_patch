# Pokémon Bank Route A 完整镜像批量导入设计

本文定义 `research/saveboxes-transaction-analysis` 分支中 Route A 的正式设计。目标是利用完整 `0xBB518` Bank v1.5 镜像作为 PC 端编辑模板，通过白名单方式把主 100 个 Bank Box 应用到运行时 BankObject；先完成 Offline Mode 的保存/重载闭环，再在最后阶段复用原版 Official save transaction 做服务器 round-trip 验证。

## 1. 设计目标

最终工作流：

```text
完整 bankdata.bin (0xBB518)
        |
        +--> 导出 PKHeX 兼容视图 (0xACA48)
        |        |
        |        `--> PKHeX 查看/编辑 100 Box
        |                    |
        |                    v
        |             edited_pkhex_view.bin
        |                    |
        `--------------------+
                 |
                 v
          PC 白名单合并
                 |
                 v
          bulk_import.bin
          完整 0xBB518
                 |
                 v
          3DS Offline Mode
                 |
                 v
          ApplyBulkImport()
                 |
                 v
          原版 Bank Box UI
                 |
                 v
          原版离线 save path
                 |
                 v
          restart + reload
```

Offline 闭环稳定以后，Official Mode 只把数据源从本地 `bankdata.bin` 换成 fresh server BankObject，保存仍完全复用原版 `BankSaveState` / `SerializeAndStage` / `PrepareUpdate` / HPP / Commit/Rollback。

## 2. 核心原则

### 2.1 `bulk_import.bin` 是完整镜像，但不是整文件覆盖源

`bulk_import.bin` 固定为 `0xBB518` current-format BankObject body，便于：

- 保留未知字段；
- 做 before/bulk/after 三方 diff；
- PC 端 round-trip；
- 后续直接保存为长期 master bank image。

3DS 端禁止：

```c
memcpy(runtimeBankBody, bulkImport, 0xBB518);
```

必须按区域策略应用。

### 2.2 当前区域策略

每个区域使用以下四种策略之一：

```text
COPY_FROM_BULK      从 bulk_import.bin 复制到运行时对象
PRESERVE_RUNTIME    保留当前运行时对象，不从 bulk 覆盖
REGENERATE_STOCK    依赖原版 Bank 后续 mutation/save 路径生成
UNKNOWN_PRESERVE    语义未证明，保守保留 runtime
```

V0 默认：

| 区域 | V0 策略 | 说明 |
|---|---|---|
| Header `0x000000..0x00017B` | `PRESERVE_RUNTIME` | 防止覆盖账户/版本/日期等运行时信息 |
| 主 100 Box `0x00017C..0x0AAF13` | `COPY_FROM_BULK` | 含 `0xE8` PKM 与每盒 `0x26` metadata |
| Transfer Box | `PRESERVE_RUNTIME` | 不属于 Route A 主箱目标 |
| Bank tags `[3000]` | 研究后分槽写入 | R1；不能作为 occupancy flag |
| Transfer tags | `PRESERVE_RUNTIME` | 不属于 Route A |
| source summaries `8×0x44` | `UNKNOWN_PRESERVE` | R4 判定是否必须维护 |
| `0x7260` opaque/NKZT block | `UNKNOWN_PRESERVE` | R5，不再预设为普通 Pokédex aggregate |
| counters `0xB4A9C..0xB4A9F` | `UNKNOWN_PRESERVE` | R6 |
| source software `[3000]` | 研究后分槽写入 | R2；当前证据指向“最后写入 Bank 的联动软件” |
| timestamp `[3000]` | 研究后分槽写入 | R3；当前证据指向 2000-01-01 UTC epoch seconds |
| tail `0xBB418..0xBB517` | `UNKNOWN_PRESERVE` | R6 |

## 3. PKHeX 兼容视图

PKHeX 当前 `Bank7` 使用 `0x17C` 作为主 Box 起点，并针对 legacy `0xACA48` Bank7 结构识别。current v1.5 完整文件为 `0xBB518`，因此不能直接作为 PKHeX Bank7 输入。

### 3.1 导出

```text
full bankdata.bin (0xBB518)
        |
        `--> bytes[0:0xACA48]
                  |
                  v
        bankdata_pkhex_view.bin
```

该文件只用于 PKHeX 查看/编辑，不作为官方上传对象。

### 3.2 回灌

PKHeX 编辑后的 `0xACA48` 文件只允许把主 Bank Box 区回灌到完整 current image：

```text
copy range = 0x00017C .. 0x0AAF14 (end-exclusive)
```

即完整 100 Box，包括每盒 30×`0xE8` PKM 与 `0x26` box metadata。

明确禁止直接 memcpy `0x000000..0x0ACA48`，原因：

- Header 应保留完整 current template；
- Transfer Box 不属于 Route A；
- legacy 结束 `0xACA48` 与 current BankTags 起点 `0xACA44` 存在 4-byte overlap，直接回灌会污染 current tag 表前四字节。

## 4. PC 端模型

建立 `BankV15Image`，职责只包括：

- 严格校验 `0xBB518`；
- 校验 `version=2`、`boxCount=100`；
- 提供主 Box、box metadata、tag、source、timestamp、summary、opaque block、counter、tail 的只读/受控切片；
- parse→serialize 必须 byte-identical；
- 未知字段 opaque preserve。

不在此层做 Pokémon 合法性判断。

## 5. Metadata writer V0

R1–R3 已有基线事实：

- `tag/source/timestamp` 在 Pokémon 被取出后可能保留历史值，因此不能用它们判断槽是否 occupied；
- 基线中有效 Pokémon 的 `tag=1`，但大量空槽同样保留 `tag=1`；
- `source=0x20/0x21` 与 Ultra Sun/Ultra Moon 联动软件相符，而槽内 Pokémon 的原始来源游戏可以完全不同；
- timestamp 与 `2000-01-01 00:00:00 UTC` 起的秒数高度吻合。

因此 V0 writer 不允许依据 occupancy 粗暴清零三张并行表。

第一版策略：

1. 如果 PC 编辑仅改变主 Box payload，而 bulk 中对应 tag/source/time 与模板一致，则保持模板 metadata。
2. 如果用户明确从一份真实 current Bank 模板编辑，bulk 自身携带的对应 metadata 可以作为候选值，但 3DS Online 路径是否复制仍由区域策略控制。
3. R1/R2/R3 controlled experiments 完成前，不自动从 Pokémon origin 推导 source，也不把 `tag=1` 硬编码为某一世代。
4. 新增槽位若无法证明 metadata 生成规则，Offline 测试允许进入“payload-only experimental mode”，Official Mode 禁止使用该模式。

## 6. R4/R5/R6 研究目标

### R4 source summaries

区域 `0x0AD61C`, `8×0x44`。

目标不是立即命名每一字段，而是确认：

- Bank Box UI 是否读取它；
- deposit/withdraw/move/save 哪些路径写它；
- payload-only Offline save/reload 是否自动重建；
- 若不更新，陈旧 summary 是否会影响 Bank 主功能。

### R5 opaque/NKZT block

区域 `0x0AD83C`, size `0x7260`。真实样本前部存在 `NKZT` magic，因此现阶段称为 opaque/NKZT block，不预设为普通 Pokédex aggregate。

研究重点：引用扫描、before/after changed ranges、是否在 stock save 中自动派生。

### R6 counters/tail

- counters: `0x0B4A9C..0x0B4A9F`
- tail: `0x0BB418..0x0BB517`

真实基线的第一个 counter 与最近一次 60 槽批量写入高度相关，但在 controlled experiment 前只标记为候选 deposit counter，不作为确认语义。

V0 对 counters/tail 一律 `PRESERVE_RUNTIME`。

## 7. 3DS Offline Apply

现有 Offline Mode 已能：

```text
/3ds/Bank/bankdata.bin
    -> object+8
    -> 原版 metadata continuation
    -> Bank Box UI
    -> local stage/commit/rollback
```

新增流程只插在 local BankObject 成功加载之后、进入 Box UI 前：

```text
load bankdata.bin
        |
        v
validate runtime BankObject
        |
        v
if /3ds/Bank/bulk_import.bin exists:
        read + validate
        apply whitelist
        record apply status
        |
        v
resume stock BankDataSync substate 6+
```

第一版不自动保存。

## 8. Offline 验收门槛

必须在 Official Mode 前完成：

- no-op round-trip；
- 1 occupied→empty；
- 1 empty→occupied；
- overwrite；
- Bank internal move；
- 1 Box；
- 10 Boxes；
- 100 Boxes；
- PKHeX export→edit→import；
- restart + reload；
- save twice；
- cancel/no-save；
- invalid bulk file、short file、wrong version、wrong box count。

其中 PC 层测试必须自动化；3DS UI 行为由实机/模拟器验证清单记录。

## 9. D6 Official Mode 边界

D6 只在 Offline 闭环通过后开启。第一轮限制为 1 Pokémon：

```text
server_before.bin
    -> stock login/download
    -> ApplyBulkImport whitelist
    -> manual inspect
    -> stock save transaction
    -> restart/download
    -> server_after.bin
    -> structured diff
```

Official Mode 不允许使用 payload-only experimental metadata 模式。

## 10. 成功标准

Route A 的核心成功标准不是“能够生成一个文件”，而是：

1. 完整 current Bank image 可以 byte-identical round-trip；
2. PKHeX 兼容视图可以安全导出并只回灌主 100 Box；
3. `bulk_import.bin` 能在 Offline Mode 白名单应用；
4. Offline 正常保存后重启重载仍保持 100 Box 内容；
5. 未确认 metadata 不被误覆盖；
6. 最后用 1 Pokémon 的 Official round-trip 证明服务器保存链兼容。