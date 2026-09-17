# Pokémon Bank v1.5 R4 / R5 / R6 metadata 策略

本文记录 Route A 在 R4 / R5 / R6 阶段对 current-format 附属区域的研究结果与 Bulk Import V0 写入策略。

原则：**没有充分证据证明需要随主 Box 一起更新的区域，不从 `bulk_import.bin` 覆盖到 runtime BankObject。**

## 1. 当前研究对象

| 区域 | 偏移 | 长度 | 当前称呼 |
|---|---:|---:|---|
| source summaries | `0x0AD61C` | `8 × 0x44` | 来源游戏概要 / opaque summaries |
| opaque block | `0x0AD83C` | `0x7260` | 旧文档暂称 Pokedex-like；当前改称 opaque `NKZT` block |
| counters | `0x0B4A9C` | `4` | 本次存入 / 取出计数候选 |
| tail | `0x0BB418` | `0x100` | 尾部标志 / reserved |

相关工具：

```powershell
python .\ViewerForBankdata\tools\r456_classifier.py bankdata.bin
python .\ViewerForBankdata\tools\r456_classifier.py bankdata.bin --json r456.json
```

该工具只报告 raw 值、非零范围和整数视图，不把未证明的字段强行命名。

## 2. 真实 baseline 的观测

对 2026-09-17 的一份真实 `0xBB518` Bank v1.5 current image 做分类，得到：

### 2.1 `8 × 0x44` source summaries

整个 `0x220` 区只有 8 个非零字节。

每个 entry 都是：

```text
entry + 0x1A = 0x02
其它字节 = 0
```

因此当前样本没有显示它按 299 个现存 Pokémon、source software 32/33 或 1660 个历史槽做直接统计。

结论：

- `+0x1A = 2` 可能是 current-format 初始化值、版本值或 entry 状态；
- 当前证据不足以由 PC Builder 重建完整 `0x44` entry；
- V0 不从 bulk 镜像覆盖该区域。

**V0 policy: `PRESERVE_RUNTIME`.**

## 3. `0x7260` opaque / NKZT block

真实样本中：

```text
relative +0x0000..+0x0003 = 4E 4B 5A 54 = "NKZT"
```

整个 `0x7260` 只有 5 个非零字节：

```text
+0x0000..+0x0003 = "NKZT"
+0x4FD8            = 0x01
```

这与一个会随 299 只 Pokémon 大量变化的普通 Pokédex bitset/aggregate 表现并不一致。

因此旧文档里的 `Pokedex-like aggregate` 只是早期工作名，现阶段统一称为：

```text
opaque 0x7260 / NKZT block
```

需要后续通过原版代码引用与 before/after 实验确认实际用途。

**V0 policy: `PRESERVE_RUNTIME`.**

## 4. `0xB4A9C` counters

真实样本：

```text
raw = 3C 00 00 00
u16 little endian = [60, 0]
u32 little endian = 60
```

结合最近一次 Bank 操作里恰有 60 个槽被当前联动软件写入，这与“本次存入 / 取出计数”的既有静态命名一致。

但即使语义最终确认，这仍属于当前 runtime/session 的操作统计，不应从一份较旧的 PC bulk 模板覆盖 fresh runtime。

**V0 policy: `PRESERVE_RUNTIME`.**

## 5. `0x100` tail

真实样本只有：

```text
tail + 0x00 = 1
其它 0xFF bytes = 0
```

当前没有证据证明它属于 Box Pokémon 内容本身。

**V0 policy: `PRESERVE_RUNTIME`.**

## 6. Route A metadata writer V0

### 6.1 允许从 bulk 导入

V0 只导入：

```text
0x00017C .. 0x0AAF14
```

即：

```text
100 × Bank Box
  ├─ 30 × 0xE8 Pokémon slot payload
  └─ 0x26 Box metadata
```

这也是 PKHeX view 回灌唯一允许覆盖的区域。

### 6.2 V0 明确保留 runtime

以下区域不从 bulk 覆盖：

```text
Header
Transfer Box
BankTags[3000]
TransferTags[30]
source summaries
opaque NKZT block
counters
SourceSoftware[3000]
Timestamp[3000]
tail
```

这样避免：

- 把旧账户 / header 状态写进当前 Bank；
- 把 PKHeX legacy `0xACA48` 末尾 4 字节错误覆盖到 current `BankTags[0..3]`；
- 把旧会话 counters / tail 带入 fresh runtime；
- 在 R1/R2/R3 controlled experiment 完成前，对 tag/source/time 做未经证明的重建。

## 7. 为什么 V0 可以先做 boxes-only Offline 验证

R0 已确认 legacy `0xACA48` → current `0xBB518` 的升级本身会让很多 current-only metadata 保持 initializer 默认值，因此：

```text
source=0
timestamp=0
```

并不是 current loader 拒绝 Pokémon 的充分条件。

真实 baseline 还证明：大量已经为空的槽仍保留历史 `tag/source/timestamp`，这些字段不是 occupancy flag。

因此 Offline V0 的第一目标应当是：

```text
主 100 Box 是否可以被替换
→ Bank Box UI 是否正确显示
→ stock offline save 是否正常序列化
→ restart / reload 后主 Box 是否 byte-identical 保持
```

而不是在第一版就伪造全部附属 metadata。

## 8. R4/R5/R6 后续实验

需要继续做：

1. source summary：不同联动游戏 deposit 前后逐 entry diff；
2. NKZT：单 Pokémon deposit / clear / internal move 前后 diff；
3. counters：分别执行 `+1 deposit`、`+1 withdraw`、Bank 内 move；
4. tail：上述所有单一操作后的差分；
5. Offline save/reload：仅替换主 Box 后，观察 stock save 是否主动修改这些区域；
6. Official round-trip：仅在 D5 Offline 闭环完成后验证服务器是否派生/改写这些字段。

## 9. 当前决策表

| 区域 | V0 策略 | 原因 |
|---|---|---|
| 100 main boxes | `COPY_FROM_BULK` | Route A 核心内容 |
| BankTags | `PRESERVE_RUNTIME` | R1 未完成 controlled mapping |
| SourceSoftware | `PRESERVE_RUNTIME` | R2 有强线索但未完成写入规则 |
| Timestamp | `PRESERVE_RUNTIME` | epoch 基本确认，move/clear 规则仍待测 |
| source summaries | `PRESERVE_RUNTIME` | baseline 极稀疏，不足以重建 |
| opaque NKZT | `PRESERVE_RUNTIME` | 语义未知 |
| counters | `PRESERVE_RUNTIME` | runtime/session 统计 |
| tail | `PRESERVE_RUNTIME` | 语义未知 |

当 R1/R2/R3 的 controlled experiment 完成后，可以新增 Stage B writer，但 Stage A boxes-only 不需要推翻。
