# Pokémon Bank 研究 / Route A 文档索引

本目录包含 Pokémon Bank v1.5 文件格式、事务、Route A Bulk Import、Official Bulk Sync 与实机验证相关文档。

## Official Bulk Sync（当前 feature 分支）

- **[Official Bulk Sync 详细技术文档 V3](official-bank-bulk-sync-technical-v3.zh-cn.md)**：2026-09-19 当前版本；记录 V2 `undefined instruction` 的 ARM/Thumb interworking relocation 根因、机器码证据、V3 command-buffer 参数传递、RX text-tail payload、静态边界与实机验证顺序。
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
```

旧 Preview 与 official-only 版是两个不同验证阶段；不要把 Offline Preview 已验证的“本地 save/reload”直接等同于 official server round-trip。
