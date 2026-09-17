# Pokémon Bank v1.5 legacy `0xACA48` → current `0xBB518` 升级分析

本文记录 R0 对 Pokémon Bank v1.5 `0x002BA490 BankFile_LoadLegacyBody` 的静态逆向结果，并把它与 `0x00116294 BankFile_InitializeEmpty`、现有 `0xBB518` 文件地图交叉起来。

本文只把原版代码能够直接证明的行为标为“确认”。由已确认文件偏移反推 literal / 结构成员的地方会明确标为“推导”。tag、source software、timestamp 的业务枚举仍属于后续 R1/R2/R3。

## 1. 结论摘要

`0x002BA490` **不是逐字段转换器**。它的升级策略非常简单：

```text
1. 按 current format 初始化一个完整 BankObject
2. 把 legacy serialized body 整体拷到 current body 的前缀
3. 把 current version 强制改成 2
```

等价伪代码：

```c
void BankFile_LoadLegacyBody(BankObject *obj, const void *legacy)
{
    allocator = GetAllocator(0x17);
    obj->vtable->InitializeCurrent(obj, allocator);  // +0x14 -> 0x00116294
    memcpy(obj + 8, legacy, LEGACY_SIZE);            // legacy serialized prefix
    *(uint16_t *)((uint8_t *)obj + 0x164) = 2;       // body + 0x15C
}
```

原版 Ghidra 导出对应：

```text
0x002BA490 BankFile_LoadLegacyBody
  -> FUN_00235BFC(0x17)
  -> vtable +0x14 == 0x00116294 BankFile_InitializeEmpty
  -> CopyBytesOptimized(obj + 8, legacy, legacy_size)
  -> *(u16 *)(obj + 0x164) = 2
```

其中 `obj + 8` 正是 serialized file body，因此最后一次写入对应：

```text
file + 0x15C = 2
```

即 current-format version 字段。

## 2. legacy size 与 4-byte overlap

项目当前基线把 legacy Bank7 长度识别为：

```text
LEGACY_SIZE = 0xACA48
```

而 current v1.5 已确认：

```text
Transfer Box Pokémon end = 0xACA44
BankTags[3000] start      = 0xACA44
```

因此 legacy prefix copy 与 current-format 新布局并不是在完全相同的边界切开：

```text
0x0ACA44                 0x0ACA48
|-----------------------|
       4 bytes

legacy:  旧文件最后 4 bytes
current: BankTags[0..3]
```

所以升级后的 current object 满足：

```text
0x000000 .. 0x0ACA47  <- legacy file copy
0x0ACA48 .. 0x0BB517  <- current initializer defaults
```

### 2.1 重要限制

这 **不等于** 已经证明 legacy 最后 4 bytes 的旧业务语义就是 `BankTags[0..3]`。

当前只确认 loader 会让这 4 bytes 覆盖 current tag 表的前四个物理字节。旧格式尾部 4 bytes 的原始含义仍需进一步静态/动态确认。

因此 R1 做 tag 实验时必须把：

```text
slot index 0..3
```

与：

```text
slot index >= 4
```

分开观察，不能只拿第一个槽作为全部 3000 槽的代表。

## 3. `BankFile_InitializeEmpty` 对 current object 的初始化

`0x00116294` 在 legacy copy 之前先建立一个完整 current-format 基线。

### 3.1 100 × 30 Bank Pokémon slots

初始化器遍历：

```text
box  = 0..99
slot = 0..29
```

目标地址符合：

```text
obj + 0x184
+ box * 0x1B56
+ slot * 0xE8
```

换成 serialized file offset：

```text
file + 0x17C
+ box * 0x1B56
+ slot * 0xE8
```

每个 `0xE8` 槽通过 `0x00127C8C` 写入同一类 blank/template Pokémon record。

`0x00127C8C` 本身最终执行：

```text
CopyBytesOptimized(destination, template + 8, 0xE8)
```

因此 current initializer 不是简单把 Pokémon 区域整块 memset；它使用原版 Pokémon 对象的 0xE8 serialized/template 内容初始化每一个槽。

### 3.2 Bank slot format tags

同一 100×30 循环对每个槽对应的并行 1-byte tag 写：

```text
0
```

文件地图对应：

```text
BankTags[index]
file + 0xACA44 + index
index = box * 30 + slot
```

因此在 legacy upgrade 中，除 legacy copy 覆盖窗口外，current initializer 提供的默认 tag 是 `0`。

由此可以得到一个很重要的研究约束：

> `tag == 0` 不能在没有动态证据时解释成“空槽”。legacy 升级能够让已有 Pokémon 与默认 tag 共存，因此 `0` 至少是一个被原版迁移路径接受的默认/legacy 状态。

它具体表示 PK6、legacy/default 或其他枚举，留给 R1 验证。

### 3.3 Transfer Box

初始化器同样遍历 30 个 Transfer Box 槽：

```text
file + 0xAAF14 + slot * 0xE8
```

每个 Pokémon record 使用同一类原版 blank/template 初始化；对应 Transfer tag 初始化为：

```text
0
```

Transfer tag 区：

```text
0xAD5FC .. 0xAD619
```

### 3.4 Box group / order metadata

对 100 个 Box，初始化器写入：

```text
box.group = 0
box.order = physical_box_index
```

根据 `0x1B56` Box stride 和已确认 box metadata 布局，对应每个 Box 内：

```text
+0x1B53  group byte
+0x1B54  order u16
```

这与 `0x002BA3E0` 中维护 group/order 的代码一致。

### 3.5 Version / Bank Box count

初始化器直接写：

```text
file + 0x15C : u16 = 2
file + 0x15E : u16 = 100
```

legacy copy 会覆盖 legacy header 中的旧值，因此 `0x002BA490` 最后再次强制：

```text
file + 0x15C = 2
```

注意：loader 最后只显式重写 version；Box count 最终值取决于 legacy prefix 中的对应字段。现有受支持 legacy 文件应为 Bank 的 100 Box 结构，但工具仍应独立校验该字段。

## 4. current-only metadata 的默认来源

由于升级顺序是：

```text
InitializeCurrent
    -> legacy prefix copy
```

所以 `legacy_size` 之后没有被 copy 覆盖的区域，保留 initializer 写入的 current defaults。

### 4.1 Source-game summaries

区域：

```text
0xAD61C
8 × 0x44
```

initializer 明确遍历 8 条记录并做结构化清零，同时对每条记录写一个 `u16 = 2` 的版本/类型样字段。该字段的正式业务名称尚未确认。

结论：legacy loader 没有从旧文件逐条构造这些 summary；它们来自 current initializer。

### 4.2 Deposit / withdrawal counters

区域：

```text
0xB4A9C .. 0xB4A9F
```

initializer 对这里的两个 `u16` 显式写 `0`，等价于 4-byte counters 清零。

### 4.3 Source software IDs

区域：

```text
0xB4AA0
3000 bytes
```

initializer 调用零填充 helper 初始化该数组。

因此正常 legacy migration 后：

```text
SourceSoftware[index] = 0
```

至少对于没有被其他后续流程再次更新的槽成立。

这意味着 `source software == 0` 同样不能仅凭数值解释成“空槽”；它可以是合法的 legacy/default 来源状态。

### 4.4 Per-slot update timestamps

区域：

```text
0xB5658
3000 × 8 bytes
```

initializer 零填充完整 timestamp 数组：

```text
Timestamp[index] = 0
```

所以 legacy migration 不会为旧 Pokémon 伪造“当前迁移时间”。旧槽可以带 `timestamp == 0` 进入 current-format BankObject。

这说明 timestamp 至少不是“Bank 能否载入/显示旧 Pokémon”的强制非零条件；它的实际业务意义仍需 R3 动态实验确认。

### 4.5 Tail

区域：

```text
0xBB418 .. 0xBB517
```

initializer 在尾部存在一个显式单字节 `1` 初始化以及一个 255-byte zero-fill。结合 `0x002BA574` 对 current object `+0xBB420` 的布尔访问，这与：

```text
tail[0] = 1
tail[1..255] = 0
```

高度一致。

但由于 Ghidra pseudocode 中目的地址仍通过 literal 表达，R0 将这个映射标为 **高置信度推导**，在得到真实 before/after 文件前不把 tail[0] 的业务名称固定下来。

## 5. 对 Bulk Import 路线 A 的直接影响

R0 得出的最大工程结论是：

### 5.1 不必假设所有 occupied slot 都必须拥有非零 source/time

原版 legacy upgrade 本身就允许：

```text
已有 Pokémon record
+ sourceSoftware = 0
+ timestamp = 0
```

进入 current-format 对象。

因此 R2/R3 应研究“这些字段什么时候由原版更新”，而不是先假设 Builder 必须人为生成一个看起来合理的值。

### 5.2 tag=0 必须按 legacy/default 候选解释

current initializer 对 3000 tags 全部写 0，而 legacy loader 不会根据每只 Pokémon 逐槽计算 tag。

因此：

```text
0 == empty
```

这个假设目前没有依据，而且与迁移路径不相容。

后续 R1 的首要实验应是比较：

```text
legacy/default occupied Pokémon
Gen6 newly deposited Pokémon
Gen7 newly deposited Pokémon
empty slot
```

对应 tag，而不是仅比较“有/空”。

### 5.3 完整镜像编辑器仍应 preserve unknown current metadata

虽然 migration 证明很多 current-only metadata 可以为默认值，但 Route A 的安全策略不变：

```text
PC bulk_import.bin
  = 完整 0xBB518 编辑镜像

Official Apply
  = fresh server BankObject
    + 白名单覆盖的 bulk Box/slot metadata
```

不应因为 legacy loader 能初始化默认值，就把旧镜像的 header/identity/unknown state 整体 memcpy 到 fresh official object。

## 6. D0 工具需要特别暴露的边界

`bank_v15_layout.py` 固化：

```text
CURRENT_SIZE       0xBB518
LEGACY_SIZE        0xACA48
BANK_TAGS_START    0xACA44
LEGACY_OVERLAP     0xACA44..0xACA47 (4 bytes)
CURRENT_ONLY_START 0xACA48
```

结构化 diff 对每个 Bank slot 同时关联：

```text
PKM        file + 0x17C + box*0x1B56 + slot*0xE8
Tag        file + 0xACA44 + index
Source     file + 0xB4AA0 + index
Timestamp  file + 0xB5658 + index*8
index      box*30 + slot
```

这样 R1/R2/R3 做一次真实操作，就可以直接看到同一 slot 的四组变化，而不是手工在十六进制文件中来回跳转。

## 7. R0 已完成与仍待研究

### 已完成

- [x] `0x002BA490` 完整函数体恢复。
- [x] 确认 initializer → prefix copy → force version 的升级顺序。
- [x] 确认 current initializer 对 3000 Bank tag、30 Transfer tag 的默认值为 0。
- [x] 确认 source software / timestamp current-only 数组由 initializer 零初始化。
- [x] 确认 counters 初始化为 0。
- [x] 标出 `0xACA44..0xACA47` legacy/current 4-byte overlap。
- [x] 确认 100 Box 的 group/order 默认规则。

### 继续进入 R1/R2/R3

- [ ] legacy 文件最后 4 bytes 的旧格式原始语义。
- [ ] Bank format tag 完整枚举；重点验证 `0` 的含义。
- [ ] source software ID 枚举及 mutation 规则。
- [ ] timestamp 编码、单位和 mutation 规则。
- [ ] Box move/copy/clear/overwrite 对四联字段的联动。

## 8. 关键函数

| 地址 | 当前命名 | 与 R0 的关系 |
|---:|---|---|
| `0x00116294` | `BankFile_InitializeEmpty` | 建立 current-format 默认对象 |
| `0x00127C8C` | slot/template copy helper | 把原版 0xE8 template 写入 Bank/Transfer 槽 |
| `0x002322F8` | zero-fill helper | 结构清零 |
| `0x002363B8` | zero-fill helper | 结构清零 |
| `0x0023653C` | `CopyBytesOptimized` | 固定长度 byte copy |
| `0x002BA3E0` | Box group/order maintenance | 佐证 box metadata 布局 |
| `0x002BA490` | `BankFile_LoadLegacyBody` | legacy → current 升级入口 |
| `0x002BA574` | tail leading-flag accessor | 佐证 current tail 首部存在布尔字段 |

## 9. 当前结论的可信度

| 结论 | 可信度 |
|---|---|
| loader 先 current initialize，再 copy legacy prefix，最后 version=2 | 确认 |
| runtime object header 为 8 bytes、serialized body 从 obj+8 开始 | 确认 |
| current size `0xBB518` | 确认 |
| legacy size `0xACA48` | 已有项目基线 / 高置信度 |
| Bank tags 从 `0xACA44` 开始 | 已有项目基线 / 高置信度 |
| legacy/current 存在 4-byte 物理 overlap | 由上述两个已确认/高置信度边界直接推导 |
| source software / timestamp 在 migration 后默认全 0 | 确认其 initializer 零填充；后续流程是否立即改写需动态验证 |
| tail[0]=1、其余 255 bytes=0 | 高置信度推导，业务名称未确认 |
| tag 0 的具体业务含义 | 未确认；R1 |
| source ID 枚举 | 未确认；R2 |
| timestamp 编码 | 未确认；R3 |
