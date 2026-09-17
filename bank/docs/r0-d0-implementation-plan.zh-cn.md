# Bank v1.5 R0 + D0 实施计划

> 本计划执行 `bank/docs/bank-v15-bulk-import-roadmap.zh-cn.md` 中的 R0 与 D0。先把 legacy/current 边界和槽位物理映射固化，再提供可重复运行的 binary diff 工具。后续 R1/R2/R3 的 tag/source/timestamp 实验都依赖本阶段产物。

**Goal:** 完成 `0x002BA490 BankFile_LoadLegacyBody` 的字段级静态分析，并实现只依赖 Python 标准库的 Bank v1.5 结构化 diff 工具。

**Architecture:** R0 文档以原版 Ghidra 导出和已确认的 `0xBB518` 文件地图为唯一静态事实来源。D0 在 `ViewerForBankdata/tools` 中新增共享布局模块和 diff CLI，按 Bank 区域及 3000 个槽聚合变化，不修改输入文件。

**Tech Stack:** Python 3 标准库、`unittest`、现有 Ghidra pseudocode export。

**Spec:** `bank/docs/bank-v15-bulk-import-roadmap.zh-cn.md`

## Global Constraints

- 当前 Bank v1.5 serialized body 必须严格为 `0xBB518` bytes。
- legacy Bank7 输入按 `0xACA48` bytes 处理。
- 所有工具默认只读，不自动搜索或修改用户 bankdata。
- 未确认语义的字段保持 opaque；输出允许使用 `unknown` / raw hex，但不得把推断标成原版正式字段名。
- 研究工具必须能够对单个 slot 同时报告 Pokémon payload、format tag、source software 和 timestamp 的变化。
- Official/NEX/HPP 上传不属于 R0/D0 实现范围。

---

### Task 1: R0 legacy upgrade 静态分析

**Files:**
- Create: `bank/docs/bank-v15-legacy-upgrade-analysis.zh-cn.md`

**Interfaces:**
- Consumes: `0x002BA490 BankFile_LoadLegacyBody`、`0x00116294 BankFile_InitializeEmpty`、现有 Bank v1.5 文件地图。
- Produces: legacy→current 的确定执行顺序、legacy 覆盖边界、current-only 区域的默认初始化结论，以及待动态验证项。

- [x] 记录 `0x002BA490` 的完整伪代码和对象/文件偏移换算。
- [x] 证明执行顺序为 current initializer → legacy prefix copy → version=2。
- [x] 标出 `0xACA44~0xACA47` 这个 legacy/current 4-byte 重叠窗口，禁止把 `0xACA48` 简化成 current 扩展区起点。
- [x] 从 `0x00116294` 提取 100×30 Bank slots、Transfer Box、tag、version/box count、source summaries、counter/source/timestamp/tail 的默认初始化行为。
- [x] 把“已确认”“由文件地图推导”“仍需动态验证”分开记录。

### Task 2: D0 layout module — TDD

**Files:**
- Create: `ViewerForBankdata/tools/bank_v15_layout.py`
- Create: `ViewerForBankdata/tests/test_bank_v15_layout.py`

**Interfaces:**
- Produces:
  - `BankV15Layout` constants
  - `slot_index(box, slot) -> int`
  - `slot_offsets(box, slot) -> SlotOffsets`
  - `region_for_offset(offset) -> str`
  - `validate_current(data) -> list[str]`

- [x] 先写测试：文件总长、所有区域首尾连续、Box 1/100 与 Slot 1/30 地址、tag/source/timestamp 与同一 slot index 对齐。
- [x] 运行测试并确认因 `bank_v15_layout` 尚不存在而失败。
- [x] 实现最小布局模块。
- [x] 运行测试至全部通过。

### Task 3: D0 structured diff — TDD

**Files:**
- Create: `ViewerForBankdata/tools/diff_bank_file.py`
- Create: `ViewerForBankdata/tests/test_diff_bank_file.py`

**Interfaces:**
- Consumes: `bank_v15_layout.py`。
- Produces:
  - `compare_bank_images(before: bytes, after: bytes) -> dict`
  - text report
  - optional JSON report

- [x] 先写合成镜像测试：只改一个 Pokémon byte 时归到正确 Box/Slot；只改 tag/source/timestamp 时归到同一 slot；aggregate/tail 修改归到独立 region。
- [x] 运行测试并确认失败原因是 diff 实现尚不存在。
- [x] 实现 slot-level change aggregation 和 region-level changed ranges。
- [x] 增加 CLI：`python diff_bank_file.py BEFORE AFTER [--json OUT] [--only-changed-slots]`。
- [x] 运行全部 tests。

### Task 4: 文档与使用说明

**Files:**
- Modify: `ViewerForBankdata/tools/README.zh-cn.md`
- Modify: `ViewerForBankdata/tools/README.md`
- Modify: `bank/docs/bank-v15-bulk-import-roadmap.zh-cn.md`

- [x] 增加 diff 工具命令示例。
- [ ] 在 roadmap 中记录 R0/D0 当前状态和产物链接。
- [x] 明确工具不解释 tag/source/timestamp 的业务枚举，只报告 raw change；R1/R2/R3 再给语义。

### Task 5: Verification

- [x] `python -m unittest discover -s ViewerForBankdata/tests -v` 全通过。
- [x] 对合成 `0xBB518` before/after 镜像运行 CLI，确认文本和 JSON 都能生成。
- [x] 再次检查 legacy 文档中不存在把推断写成已确认值的问题。
- [x] 核对所有 offset 边界最终闭合到 `0xBB518`。

## 当前状态

R0 静态分析与 D0 核心 diff 工具已经完成。roadmap 的状态回写未阻塞任何研究或代码路径；后续可在 R1/R2/R3 启动时统一更新 roadmap 的进度表。
