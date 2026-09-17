# Pokémon Bank v1.5 R1/R2/R3 基线样本分析

本文记录一份真实 Pokémon Bank v1.5 `bankdata.bin` 的结构化分析结果，用作 R1（format tag）、R2（source software ID）、R3（timestamp）的联合实验基线。

> 仅提交结构统计与可复现实验结论。原始 `bankdata.bin`、UID、账户相关字段和其它可识别信息不进入仓库。

相关文档：

- [`bank-v15-bulk-import-roadmap.zh-cn.md`](./bank-v15-bulk-import-roadmap.zh-cn.md)
- [`bank-v15-legacy-upgrade-analysis.zh-cn.md`](./bank-v15-legacy-upgrade-analysis.zh-cn.md)
- [`bank-game-link-and-save-adapter-analysis.zh-cn.md`](./bank-game-link-and-save-adapter-analysis.zh-cn.md)

---

## 1. 样本格式确认

该样本是 current Bank v1.5 serialized body：

```text
size      = 0xBB518
version   = 2
box count = 100
```

因此它不是 PKHeX 当前 `Bank7` 直接识别的 legacy `0xACA48` 容器。

样本中的 100 个 Bank Box 从 `0x17C` 开始，每盒 `0x1B56`，每槽 Pokémon record 为 `0xE8`。3000 槽的并行 metadata 分布仍与 R0 文件地图一致：

```text
BankTags[3000]        @ 0x0ACA44
SourceSoftware[3000]  @ 0x0B4AA0
Timestamp[3000]       @ 0x0B5658
```

---

## 2. Pokémon payload 校验

使用 PKHeX `PokeCrypto.Decrypt67` 同等算法对全部 3000 个 `0xE8` record 解密并验证 checksum：

```text
有效 Pokémon（species != 0） : 299
空 Pokémon record             : 2701
checksum invalid              : 0
```

结论：

- 当前 `0xBB518` 样本的 3000 个 Pokémon record 结构完整；
- 不能使用 `tag != 0`、`source != 0` 或 `timestamp != 0` 作为“槽当前有 Pokémon”的判断；
- 当前占用状态应由实际 `0xE8` PKM record（解密后 `species != 0` / checksum 正常）判断。

---

## 3. R1：format tag 基线结果

3000 个 Bank tag 仅观察到：

```text
tag 0 : 1340 slots
tag 1 : 1660 slots
```

但实际有效 Pokémon 只有 299 只。

进一步交叉：

```text
有效 Pokémon：
    299 / 299 都是 tag = 1

空槽：
    1340 slots : tag=0, source=0, timestamp=0
    1361 slots : tag=1, source!=0, timestamp!=0
```

这直接证明：

> `tag == 1` 不是“当前 occupied”布尔值。

当前更合理的模型是：

- `tag=0`：从未被 current-format 写入/仍处于默认初始化状态；
- `tag=1`：该槽曾被 Bank 的 current-format 写入过，或者表示该 record 使用某种 current Pokémon format；
- Pokémon 被取出/清空后，tag 可以继续保留为 `1`。

但 **tag=1 是否具体代表 PK7/current-format，而 Gen6 直接 deposit 是否会产生其它 tag 值，仍需 controlled Gen6 experiment 确认**。

因此 R1 下一步的关键实验不是继续统计现有样本，而是对一个 `tag=0/source=0/time=0` 的“从未使用槽”分别做 Gen6 与 Gen7 deposit。

---

## 4. R2：source software ID 基线结果

3000 个 source byte 分布：

```text
0x00 : 1340 slots
0x20 : 1600 slots
0x21 :   60 slots
```

与 tag/time 的关系是严格一致的：

```text
(tag=0, source=0x00, timestamp=0) : 1340
(tag=1, source=0x20, timestamp!=0): 1600
(tag=1, source=0x21, timestamp!=0):   60
```

其中：

```text
0x20 = decimal 32
0x21 = decimal 33
```

这两个数值与 PKM `GameVersion` 的 3DS Gen7 枚举值精确对应：

```text
32 = Ultra Sun
33 = Ultra Moon
```

同时，样本中 `source=32` 的有效 Pokémon 原始版本并不只来自 Ultra Sun，而包括 Emerald、FireRed、White、VC Red、VC Silver、VC Crystal 等；`source=33` 的 Pokémon 原始版本也混合 Sun / Ultra Sun / Ultra Moon。

因此 source byte **不是 Pokémon origin game**。

当前最强解释是：

> `SourceSoftware[slot]` 记录“该槽最后一次由哪个当前联动游戏写入 Bank”，数值使用或兼容 PKM GameVersion ID。

本样本支持至少：

```text
0x20 -> Ultra Sun
0x21 -> Ultra Moon
```

后续使用 XY / ORAS / SM / USUM 做 controlled deposit 后，应检查是否得到：

```text
X             24 / 0x18
Y             25 / 0x19
AlphaSapphire 26 / 0x1A
OmegaRuby     27 / 0x1B
Sun           30 / 0x1E
Moon          31 / 0x1F
UltraSun      32 / 0x20
UltraMoon     33 / 0x21
```

在 controlled experiment 完成前，除 `0x20/0x21` 外不要把整张映射标成已确认。

---

## 5. R3：timestamp 编码基本锁定

样本中非零 timestamp 共 1660 个，和 `tag=1/source!=0` 槽数量完全一致。

原始值例如：

```text
812983597
842957994
842957997
```

按以下公式转换：

```text
UTC = 2000-01-01 00:00:00 + timestamp seconds
```

得到：

```text
812983597 -> 2025-10-05 12:46:37 UTC
842957994 -> 2026-09-17 10:59:54 UTC
842957997 -> 2026-09-17 10:59:57 UTC
```

同一样本 header 的 Bank 日期字段为：

```text
2026-09-17 10:58
```

而最近两组 30 槽 timestamp 分别是：

```text
Box 5 : 2026-09-17 10:59:54 UTC, 30 slots
Box 6 : 2026-09-17 10:59:57 UTC, 30 slots
```

它们与样本生成时间高度一致。

因此当前可以把 R3 的编码结论标为 **强确认候选**：

```c
unix_like = seconds_since_2000_01_01_UTC;
```

还需 controlled single-slot deposit 做最后确认，并确认：

- Bank 内 move 是否保留旧 timestamp；
- clear / withdraw 是否保留 timestamp；
- overwrite/redeposit 是否刷新 timestamp；
- 是否每次 mutation 调一次 clock，还是同一 box/batch 共用同一个 timestamp。

现有样本已经显示整盒 30 槽可以共享同一个时间值。

---

## 6. 一个非常重要的“历史 metadata”现象

存在 1361 个槽：

```text
Pokémon record = empty
Tag            = 1
SourceSoftware = 32
Timestamp      != 0
```

这意味着 Pokémon 被取出/清空后，至少在该历史路径中：

```text
PKM payload 被清空
但 tag/source/timestamp 没有归零
```

因此 Bulk Import 的设计必须把两个概念分开：

```text
当前 occupancy
    -> 由 Pokémon record 决定

slot provenance/history metadata
    -> tag/source/timestamp
```

不能写成：

```c
if (tag == 0) empty;
if (tag != 0) occupied;
```

也不能因为 bulk image 中一个 slot 为空，就默认必须把 source/timestamp 清零。

后续 controlled clear 实验决定正式 writer 应采用“保留历史 metadata”还是“按原版其它路径更新”。

---

## 7. Counters 的提前线索

`0x0B4A9C` 四字节在该样本中为：

```text
3C 00 00 00
```

按两个 `u16`：

```text
first  = 60
second = 0
```

同时最新 `source=33` 恰好是两个完整 Box：

```text
30 + 30 = 60 slots
```

因此第一 `u16` 很可能是当前 save/session 中的 deposit count，而第二 `u16` 可能是 withdrawal count。

此结论暂列为 **强推断**，放到 R6 再通过单次 deposit / withdrawal 验证。

---

## 8. Source summaries 与大块 aggregate 的基线

### 8.1 `8 × 0x44` source summaries

该样本虽然已经包含大量历史 Bank 操作，但 8 个 entry 几乎仍是 initializer 默认值：每个 entry 仅在 `+0x1A` 保留 current version `2`，其余基本为 0。

这说明 source summaries 至少不是“3000 槽当前来源的完整汇总表”。

对 Bulk Import 来说这是好消息：V1 很可能不需要根据 3000 槽主动重建这 8 个 entry。

### 8.2 `0x7260` 区域

该区域在本样本中也几乎为空，仅观察到：

```text
+0x0000 : ASCII "NKZT"
+0x4FD8 : 0x01
```

因此此前把整个 `0x7260` 简称为 “Pokedex-like aggregate” 需要继续谨慎；至少从该真实样本看，它不是随着 299 只存储 Pokémon 大量变化的普通 per-species aggregate。

建议后续文档改称：

```text
0xAD83C..0xB4A9C opaque NKZT block
```

直到静态引用或 controlled diff 证明具体用途。

---

## 9. PKHeX 为什么打不开完整 current `bankdata.bin`

PKHeX 当前 Bank7 检测条件是：

```text
SIZE_G7BANK = 0xACA48
IsBank7(data) = data.Length == 0xACA48 && data[0] != 0
```

而本项目 current Bank v1.5 是：

```text
0xBB518
```

所以 PKHeX 拒绝完整文件是 **长度检测不匹配**，并不说明该 `bankdata.bin` 损坏。

PKHeX `Bank7` 对 100 个主 Bank Box 的访问仍从：

```text
BoxStart = 0x17C
```

开始，并按 30×`0xE8` + Box metadata 的 stride 读取。

因此可以制作一个只用于 PKHeX 查看/编辑主 Box 的 compatibility view：

```text
current bankdata.bin[0 : 0xACA48]
```

但在 R1/R2/R3 尚未完成前，**不要把 PKHeX 保存出的 `0xACA48` 文件直接当成 current `0xBB518` 上传文件**。

正确方向仍是：

```text
PKHeX legacy-size view
    -> 只提供主 Box 编辑
    -> 把已修改的 Box payload 合并回原 0xBB518 template
    -> 使用研究确认后的 tag/source/timestamp writer
    -> 得到 bulk_import.bin
```

---

## 10. 下一轮 controlled experiment 固定槽位

为了避免历史 metadata 干扰，优先使用当前样本中确认的“从未使用槽”：

```text
Box 60 Slot 1..5
```

当前状态均为：

```text
PKM species = 0
Tag         = 0
Source      = 0
Timestamp   = 0
```

建议每个实验都从同一个 baseline 恢复，避免串扰。

### E1 — Gen6 deposit

```text
baseline
-> 用 X/Y/ORAS 联动
-> 只往 Box60 Slot1 放 1 只 Pokémon
-> 正常保存
-> dump E1_gen6_deposit.bin
```

观察：

```text
PKM
Tag
SourceSoftware
Timestamp
Counters
NKZT block
```

核心问题：Gen6 是否产生不同于 `tag=1` 的 format tag。

### E2 — Gen7 deposit

```text
restore baseline
-> 用 SM/USUM 联动
-> 只往 Box60 Slot1 放 1 只 Pokémon
-> 正常保存
-> dump E2_gen7_deposit.bin
```

用于和 E1 直接比较 tag/source/time。

### E3 — clear / withdraw

```text
restore E2 deposit state
-> 把 Box60 Slot1 Pokémon 取回游戏
-> 保存
-> dump E3_clear.bin
```

验证 payload 为空后：

```text
tag 是否保留
source 是否保留
timestamp 是否保留/刷新
withdraw counter 是否 +1
```

### E4 — Bank internal move

```text
restore E2 deposit state
-> Box60 Slot1 -> Box60 Slot2
-> 不经过游戏
-> 保存
-> dump E4_move.bin
```

验证：

```text
source slot 的 metadata 怎么处理
destination 的 tag/source/time 是搬过去还是刷新
```

### E5 — redeposit 到历史空槽

```text
restore E3 clear state
-> 再把 1 只 Pokémon deposit 到 Box60 Slot1
-> 保存
-> dump E5_redeposit.bin
```

验证旧历史 metadata 是否被新 linked-game source/time 覆盖。

---

## 11. 当前对 Bulk Import 的直接影响

基于本样本，现在 Route A 的 writer 设计应修改为：

1. **Occupancy 只看 PKM payload，不看 tag/source/time。**
2. 对“导入 occupied slot”：
   - 写入 `0xE8` PKM；
   - 写入正确 format tag；
   - source 使用“导入策略”或模拟 linked game，而不是 Pokémon origin game；
   - timestamp 使用 current Bank clock 语义。
3. 对“导入 empty slot”：
   - 不能先假设 tag/source/time 必须清零；
   - 等 E3/E4 确认原版 clear/move 规则后再实现。
4. source summaries 和 NKZT block 第一版优先保持 fresh runtime BankObject 原值，不从 bulk template 整块覆盖。
5. counters 由原版 mutation/save 路径能否自动维护，需要单独验证；若 Bulk Apply 直接 memcpy slot，则可能需要显式模拟。

---

## 12. 当前可信度表

| 结论 | 可信度 |
|---|---|
| current serialized size = `0xBB518` | 已确认 |
| version=2 / 100 boxes | 已确认 |
| 299 occupied + 2701 empty，全部 checksum 正常 | 已确认 |
| tag/source/time 不能作为 occupancy 判定 | 已确认 |
| `tag=1` 在 clear/withdraw 后可以残留 | 样本强证据，待 controlled E3 最终确认 |
| `source=32/33` 对应 linked Ultra Sun/Ultra Moon，而非 Pokémon origin | 强确认候选 |
| timestamp = seconds since `2000-01-01 UTC` | 强确认候选 |
| 一整 Box 的 slots 可共享同一 timestamp | 已观察确认 |
| first counter `60` 是 deposit count | 强推断，待 E1/E3 |
| `0x7260` 是普通 Pokedex aggregate | 当前证据不支持，需重新命名/继续逆向 |

下一步优先执行 E1~E5，所有实验均使用 `ViewerForBankdata/tools/diff_bank_file.py` 对 baseline / after 做结构化 diff。