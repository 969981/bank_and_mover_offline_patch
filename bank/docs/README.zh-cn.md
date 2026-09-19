# Pokémon Bank 研究 / Route A 文档索引

本目录包含 Pokémon Bank v1.5 文件格式、事务、Route A Bulk Import 与实机验证相关文档。

## 使用入口

- **[Route A Preview 使用文档](route-a-usage.zh-cn.md)**：安装、`bankdata.bin` / `bulk_import.bin`、PKHeX 兼容视图、Offline Mode、T0～T6、`verify-v0` 与本地构建。
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

## 当前 Route A Preview 边界

当前 research 分支已经实现并自动测试：

```text
完整 0xBB518 Bank 镜像
→ PKHeX 0xACA48 兼容视图
→ 编辑后安全回灌
→ bulk_import.bin
→ 3DS Offline Mode 仅覆盖主 100 Box
→ 原版 Bank UI
→ 原版本地保存 / 重载
→ verify-v0
```

当前 **D6 Official Apply / Save 尚未启用**。也就是说，Preview 不能被描述为已经完成“离线修改后上传官方服务器”的方案；Official Mode 的 fresh BankObject apply、原版事务保存、重新下载 round-trip 仍属于下一阶段验证内容。
