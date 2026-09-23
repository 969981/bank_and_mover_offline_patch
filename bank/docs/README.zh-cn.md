# Pokémon Bank 研究 / Route A 文档索引

本目录包含 Pokémon Bank v1.5 文件格式、事务、Route A Bulk Import、Official Bulk Sync 与实机验证相关文档。

## Official Bulk Sync 异常保存 / Recovery 研究

> 研究分支：`feature/official-bank-recovery-research`，由 `feature/official-bank-bulk-sync` 派生。

- **[Trainer mismatch / 异常事务恢复研究](official-bank-recovery-research.zh-cn.md)**：解释网络保存失败后，同一份未恢复存档仍可能被判“不一致”的根因；记录当前已闭环结论与开发边界。
- **[Recovery 地址图与事务记录结构](official-bank-recovery-address-map.zh-cn.md)**：`0x002B1CF8 / 0x002A93F4 / 0x002A8760 / 0x002A8D30` 完整数据流，Game/Local recovery record 布局，`dataId + curVersion` mismatch gate，以及 Commit/Rollback 选择逻辑。
- **[Recovery 实机故障注入矩阵](official-bank-recovery-test-matrix.zh-cn.md)**：Prepare 前、Upload、Game Save、Local Save、Complete/Rollback 等窗口的实验方法与 SERVER/LOCAL/GAME 三方记录采集要求。

当前最重要的新结论：state 18 的 blocking predicate 不是普通 Trainer ID/OT 比较，而是 server pending `BankTransactionParam` 与 Local/Game recovery record 的 `dataId + curVersion` 一致性校验；UI 中显示的 Trainer Name/ID 来自额外 metadata 查询，用于提示上一次关联对象。

研究分支还新增：

```text
bank/tools/extract_recovery_chain.py
bank/tools/recovery_targets.txt
bank/src/official_recovery_probe_core.c
bank/src/official_recovery_probe_host_test.c
.github/workflows/official-bank-recovery-research-ci.yml
```

其中 recovery probe 目前只是 host-testable 的 stock 事务判定模型，不改变实机 Bank 行为。机器码级实验 Hook 必须在取得并校验 stock `.code` 后单独生成，不能根据 Ghidra 伪代码猜 CMP/BNE 地址。

## Official Bulk Sync（当前 feature 分支）

- **[Official Bulk Sync V3 使用文档](official-bank-bulk-sync-usage-v3.zh-cn.md)**：安装、`bulk_import.bin`、自动 fresh backup、H0 / H1-preview / 1 Pokémon server round-trip、HOME 隔离验证、回退与常见问题。
- **[Official Bulk Sync V3 编译与发布指南](official-bank-bulk-sync-build-release-guide-v3.zh-cn.md)**：stock `.code` 基线、devkitARM/armips/flips、host/ARM/IPS verifier、打包、SHA-256、GitHub prerelease 与发布后检查清单。
- **[Official Bulk Sync V3 原理解析与端到端技术说明](official-bank-bulk-sync-principles-v3.zh-cn.md)**：从原版 state gate、ARM/Thumb dispatcher、fresh BankObject 备份、只读 bulk、slot-aware metadata writer、原版 Save/Upload 到 H0/H1 round-trip 的完整工作原理与维护规则。
- **[Official Bulk Sync 详细技术文档 V3](official-bank-bulk-sync-technical-v3.zh-cn.md)**：2026-09-19 当前版本；重点记录 V2 `undefined instruction` 的 ARM/Thumb interworking relocation 根因、机器码证据、V3 command-buffer 参数传递、RX text-tail payload、静态边界与实机验证顺序。
- [Official Bulk Sync 详细技术文档 V2](official-bank-bulk-sync-technical-v2.zh-cn.md)：记录上一阶段 `.data cave` 修复和单 Hook/native-state gate 架构；其中 Thumb→ARM `OfficialBulk_CommandBuffer` bridge 已在 V3 废弃。
- [Official Bulk Sync 设计契约](official-bank-bulk-sync-design.zh-cn.md)：不可变只读 `bulk_import.bin`、data-only 输入、原版上传事务保持不变、HOME 排除等硬性设计约束。
- [旧 V1 技术记录](official-bank-bulk-sync-technical.zh-cn.md)：保留作为开发历史；其中“双 Hook + data/scratch cave”已经被 V2 废弃，**不要再按 V1 构建或判断安全边界**。

当前 `feature/official-bank-bulk-sync` 的 V3 架构：

```text
原版 Bank 联网/游戏识别
→ BankDataSyncState_Update 单 Hook
→ ARM dispatcher 直接获取 TLS / FS command buffer
→ Thumb OfficialBulkSync_Process(state, commandBuffer)
→ fresh BankObject backup
→ 只读 bulk_import.bin
→ slot-aware Pokémon merge
→ stock-derived tag/source/timestamp
→ 原版 Bank UI
→ 用户原版保存流程
```

当前只修改一个原版执行点和真正的 RX text 尾部；不再向 mapped `.data` / BSS 写入代码，也不再生成 Thumb→ARM external helper relocation。

**尚未完成的关键证据是官方服务器 Save → redownload round-trip。** 必须先从 1 Pokémon 开始验证，再扩大到 30 / 300 / 3000。

当前 GitHub prerelease：

```text
official-bulk-sync-v3-preview-20260919
```

使用/编译发布时以 V3 文档为准，不要继续使用旧 V1/V2 的安装布局或 code cave 假设。

## Route A Preview / 离线研究入口

- [Route A Preview 使用文档](route-a-usage.zh-cn.md)：安装、`bankdata.bin` / `bulk_import.bin`、PKHeX 兼容视图、Offline Mode、T0～T6、`verify-v0` 与本地构建。
- [Route A 实机测试协议](route-a-device-test-protocol.zh-cn.md)：D5 分级实机测试与证据保留规范。
- [ViewerForBankdata 工具说明](../../ViewerForBankdata/tools/README.zh-cn.md)：`bankbulk.py`、结构化 diff、R4/R5/R6 classifier 的命令行说明。

## 设计与开发

- [Bank v1.5 Bulk Import 总路线](bank-v15-bulk-import-roadmap.zh-cn.md)
- [Route A Bulk Import 设计](route-a-bulk-import-design.zh-cn.md)
- [Route A D1–D6 实施计划](route-a-d1-d6-implementation-plan.zh-cn.md)
- [R0/D0 实施计划](r0-d0-implementation-plan.zh-cn.md)

## 文件格式与 metadata 研究

- [Legacy `0xACA48` → Current `0xBB518` 升级分析](bank-v15-legacy-upgrade-analysis.zh-cn.md)
- [R1–R3：tag / source / timestamp 基线分析](r1-r3-baseline-bankdata-analysis.zh-cn.md)
- [R4–R6：summary / NKZT / counter / tail 策略](r4-r6-metadata-policy.zh-cn.md)

## 分支关系

```text
research/saveboxes-transaction-analysis
    └─ Route A Offline / Download Preview、PKHeX direct bulk、格式与事务研究

feature/official-bank-bulk-sync
    └─ 基于 research 成果的 official-only 联网实现
       不再依赖用户可见 Offline / Download Mode

feature/official-bank-recovery-research
    └─ 从 official-bank-bulk-sync 派生
       专门研究网络异常后的 transaction recovery / Trainer mismatch
```

旧 Preview、official-only 版与 recovery research 是不同验证阶段；不要把 Offline Preview 已验证的“本地 save/reload”直接等同于 official server round-trip，也不要把 recovery 实验 Hook 混入正常 V3 发布包。