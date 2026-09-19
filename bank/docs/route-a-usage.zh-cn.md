# Pokémon Bank Route A Preview 使用文档

> 适用分支：`research/saveboxes-transaction-analysis`
>
> 当前实现阶段：Route A Offline Preview。它已经支持 `bulk_import.bin` 在 Pokémon Bank 离线模式中覆盖运行时的 100 个主 Bank Box，并继续使用原版 Bank UI 与本地保存流程。**当前版本尚未启用“本地修改后上传官方服务器”的 D6 Official Apply/Save 路线。**

## 1. 目标与工作流

Route A 的目的不是把 PKHeX 的 legacy Bank 文件直接当作完整 Bank 存档，而是始终保留一个完整的 Pokémon Bank v1.5 `0xBB518` 镜像作为模板：

```text
完整 bankdata.bin (0xBB518)
        ↓
导出 PKHeX 兼容视图 (0xACA48)
        ↓
PKHeX 查看 / 编辑主 100 Box
        ↓
安全回灌到完整 current 镜像
        ↓
bulk_import.bin (0xBB518)
        ↓
3DS Pokémon Bank Offline Mode
        ↓
只把主 100 Box 应用到 runtime BankObject
        ↓
原版 Bank Box UI 检查
        ↓
正常本地保存
        ↓
重新启动验证 bankdata.bin
```

Route A V0 只覆盖：

```text
0x00017C .. 0x0AAF14 (end-exclusive)
```

即 100 个主 Bank Box：

```text
100 × (
    30 × 0xE8 Pokémon slot
    + 0x26 box metadata
)
```

以下区域都保留当前 runtime `bankdata.bin`，不会从 `bulk_import.bin` 复制：

- Header / account-related data；
- Transfer Box；
- `0xACA44..0xACA47` legacy/current overlap；
- 3000 个 current-format tag；
- 3000 个 source software ID；
- 3000 个 timestamp；
- source summaries；
- opaque/NKZT block；
- counters；
- tail flags / reserved data。

这是一项有意的安全设计：当前对这些 current-only metadata 的语义和派生规则仍在继续研究，Preview 不会用离线模板盲目覆盖它们。

---

## 2. 安装 Route A Preview 补丁

Pokémon Bank Title ID：

```text
00040000000C9B00
```

将构建包中的完整目录复制到：

```text
SD:/luma/titles/00040000000C9B00/
```

最终目录应类似：

```text
SD:/luma/titles/00040000000C9B00/
├── code.ips
└── romfs/
    └── a/
        └── 0/
            ├── 0/4
            ├── 0/5
            ├── 0/6
            ├── 0/7
            ├── 0/8
            ├── 0/9
            ├── 1/0
            ├── 1/1
            ├── 1/2
            └── 1/3
```

然后：

1. 按住 `SELECT` 开机进入 Luma3DS 配置；
2. 启用 `Enable game patching`；
3. 保存并重启；
4. 在正式测试前备份整个 `SD:/3ds/Bank/`。

Route A Preview 使用：

```text
SD:/3ds/Bank/bankdata.bin
SD:/3ds/Bank/bulk_import.bin
```

其中：

- `bankdata.bin`：当前完整 Bank v1.5 本地镜像；
- `bulk_import.bin`：准备应用到主 100 Box 的完整 `0xBB518` 镜像。

---

## 3. 验证 bankdata.bin

在仓库根目录进入：

```powershell
cd ViewerForBankdata
```

先验证文件：

```powershell
python .\tools\bankbulk.py validate "D:\Bank\bankdata.bin"
```

查看基本信息：

```powershell
python .\tools\bankbulk.py inspect "D:\Bank\bankdata.bin"
```

Route A current-format 输入必须满足：

```text
size     = 0xBB518
version  = 2
boxCount = 100
```

不要把不同账号来源的 Bank 完整镜像随意混用。

---

## 4. 为什么完整 bankdata.bin 不能直接用 PKHeX 打开

当前 Pokémon Bank v1.5 完整镜像大小是：

```text
0xBB518
```

而 PKHeX `Bank7` 兼容的 legacy 视图固定为：

```text
0xACA48
```

因此完整 current Bank 文件通常不会被 PKHeX 的 `Bank7` 入口直接接受。

Route A 提供 `export-pkhex` / `import-pkhex`，用来安全完成这两种格式之间的编辑工作流。

---

## 5. 导出只用于 PKHeX 的兼容视图

执行：

```powershell
python .\tools\bankbulk.py export-pkhex `
  "D:\Bank\bankdata.bin" `
  -o "D:\Bank\bankdata_pkhex_view.bin"
```

输出文件应为：

```text
bankdata_pkhex_view.bin
size = 0xACA48 = 707144 bytes
```

这个文件的用途只有：

- 在 PKHeX 中查看 Bank 主 100 Box；
- 使用 PKHeX 编辑主 Box；
- 保存后再由 Route A 工具回灌。

**不要：**

- 把 `bankdata_pkhex_view.bin` 直接改名成完整 `bankdata.bin`；
- 把它直接放到 3DS 当 current-format Bank 使用；
- 把它直接拿去做官方上传。

---

## 6. 用 PKHeX 编辑并回灌

### 6.1 在 PKHeX 中编辑

用 PKHeX 打开：

```text
bankdata_pkhex_view.bin
```

对主 100 Box 做需要的编辑并另存，例如：

```text
bankdata_pkhex_view_edited.bin
```

建议第一次只改 1 个 Pokémon 槽，先完成单槽验证，再扩大到 1 Box、10 Box、100 Box。

### 6.2 回灌为完整 bulk_import.bin

必须仍然使用原始完整 `bankdata.bin` 作为 current-format 模板：

```powershell
python .\tools\bankbulk.py import-pkhex `
  "D:\Bank\bankdata.bin" `
  "D:\Bank\bankdata_pkhex_view_edited.bin" `
  -o "D:\Bank\bulk_import.bin"
```

工具只会把 PKHeX 视图中的主 100 Box 区域回灌到完整模板；Header、Transfer Box 与 current-only metadata 都保持完整模板原值。

生成后再次校验：

```powershell
python .\tools\bankbulk.py validate "D:\Bank\bulk_import.bin"
```

---

## 7. 不经过 PKHeX 直接生成 bulk_import.bin

如果只是做 no-op、结构测试或后续由其它工具修改完整镜像，可以直接：

```powershell
python .\tools\bankbulk.py build `
  "D:\Bank\bankdata.bin" `
  -o "D:\Bank\bulk_import.bin"
```

这也是最安全的 T0 no-op 测试输入。

---

## 8. 在 PC 上预演 3DS Route A V0

在真正把文件放到 SD 卡之前，先生成理论 runtime 结果：

```powershell
python .\tools\bankbulk.py apply-v0 `
  "D:\Bank\bankdata.bin" `
  "D:\Bank\bulk_import.bin" `
  -o "D:\Bank\expected_after_apply.bin"
```

然后做结构化 diff：

```powershell
python .\tools\diff_bank_file.py `
  "D:\Bank\bankdata.bin" `
  "D:\Bank\expected_after_apply.bin" `
  --json "D:\Bank\expected_diff.json"
```

V0 正常情况下只有主 100 Box 应发生由 bulk 导致的变化。

---

## 9. 3DS Offline Mode 使用方法

将准备好的：

```text
bulk_import.bin
```

放到：

```text
SD:/3ds/Bank/bulk_import.bin
```

同时保留当前基线：

```text
SD:/3ds/Bank/bankdata.bin
```

然后启动 Pokémon Bank，进入 **Offline Mode**。

当前 V0 行为：

```text
读取 bankdata.bin
        ↓
验证完整本地 BankObject
        ↓
发现 bulk_import.bin
        ↓
验证 bulk size/version/boxCount
        ↓
读取 bulk 的 100 个主 Box
        ↓
覆盖 runtime BankObject 的主 Box 区
        ↓
进入原版 Bank UI
```

注意：

- `bulk_import.bin` 不存在时，继续使用原 `bankdata.bin`；
- bulk 文件明显无效时，不应用；
- 主 Box 大块读取发生 short/error 时，补丁会重新加载完整 `bankdata.bin`，避免半应用状态进入 UI；
- V0 **不会自动保存**；
- V0 **不会自动删除 `bulk_import.bin`**。

进入 Box UI 后先检查内容，再选择正常保存。

---

## 10. T0：最安全的 no-op 实机测试

第一轮强烈建议 `bulk_import.bin` 与 `bankdata.bin` 完全相同。

流程：

```text
1. 备份 SD:/3ds/Bank/
2. bankdata.bin 原样复制为 bulk_import.bin
3. 进入 Offline Mode
4. 确认 Bank UI 与原数据一致
5. 正常保存退出
6. 移走或重命名 bulk_import.bin
7. 重新启动 Offline Mode
8. 确认保存后的 bankdata.bin 仍能正常读取
9. 把保存后的 bankdata.bin 拉回 PC 验证
```

第 6 步非常重要。若不移走 `bulk_import.bin`，下一次启动还会再次应用 bulk，无法证明保存后的 `bankdata.bin` 本身已经正确持久化。

---

## 11. T1～T6 建议测试顺序

Route A 不建议第一轮就改满 100 Box。

按以下梯度：

```text
T0  no-op
T1  替换 1 个已有 Pokémon 的槽
T2  空槽 → Pokémon
T3  Pokémon → 空槽
T4  1 Box
T5  10 Boxes
T6  100 Boxes
```

每轮都保存：

```text
bankdata_before.bin
bulk_import.bin
expected_after_apply.bin
bankdata_saved.bin
```

这样发生异常时可以精确区分：

- bulk 生成错误；
- 3DS Apply 错误；
- Bank UI 操作产生额外变化；
- 原版本地 save 派生了 metadata。

---

## 12. 保存后自动验收

拿回 3DS 保存后的 `bankdata.bin`，例如保存为：

```text
bankdata_saved.bin
```

运行：

```powershell
python .\tools\bankbulk.py verify-v0 `
  "D:\Bank\bankdata_before.bin" `
  "D:\Bank\bulk_import.bin" `
  "D:\Bank\bankdata_saved.bin" `
  --json "D:\Bank\verify.json"
```

`verify-v0` 会把两类变化分开：

1. **主 100 Box**：必须与 Route A 理论 expected 一致；不一致会判 FAIL；
2. **current-only metadata**：如果原版 save 自己修改了 tag/source/timestamp/NKZT/counters/tail 等，会单独报告，但默认不把它直接判作 Bulk Apply 失败。

如果希望要求整个文件 byte-identical，可加：

```powershell
--strict
```

同时建议跑：

```powershell
python .\tools\diff_bank_file.py `
  "D:\Bank\bankdata_before.bin" `
  "D:\Bank\bankdata_saved.bin"

python .\tools\r456_classifier.py `
  "D:\Bank\bankdata_saved.bin" `
  --json "D:\Bank\r456_saved.json"
```

这些结果也用于 R4/R5/R6 判断哪些 metadata 是原版派生的。

---

## 13. 当前 metadata 策略

Route A Preview 当前采取保守策略：

| 区域 | V0 策略 |
|---|---|
| 主 100 Box Pokémon payload | `COPY_FROM_BULK` |
| 每 Box metadata | `COPY_FROM_BULK` |
| Header | `PRESERVE_RUNTIME` |
| Transfer Box | `PRESERVE_RUNTIME` |
| Bank tag[3000] | `PRESERVE_RUNTIME` |
| SourceSoftware[3000] | `PRESERVE_RUNTIME` |
| Timestamp[3000] | `PRESERVE_RUNTIME` |
| Source summaries | `PRESERVE_RUNTIME` |
| opaque/NKZT block | `PRESERVE_RUNTIME` |
| counters | `PRESERVE_RUNTIME` |
| tail | `PRESERVE_RUNTIME` |

现阶段已知：tag/source/timestamp 不是简单的“当前槽占用标志”。真实样本中存在大量空 Pokémon record 仍保留非零历史 metadata，因此 Preview 不会在清槽时简单把这些 current-only 字段归零。

---

## 14. 源码构建

需要：

- GNU Make；
- Python 3；
- devkitARM；
- armips；
- Floating IPS；
- 用户自己合法取得的 Pokémon Bank v1.5 解密、解压 `.code`；
- 完整 RomFS。

Bank v1.5 `.code` 应放置为：

```text
bank/rom/exefs/00040000000C9B00.dec.code
```

支持基线：

```text
size:   2,801,664 bytes = 0x2AC000
SHA-256:
2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF
```

RomFS 放在：

```text
bank/rom/romfs/
```

构建：

```bash
make -C bank clean
make -C bank
```

输出：

```text
release/00040000000C9B00/
├── code.ips
└── romfs/
```

当前 Route A split-payload 构建会把：

- `patch-base.o` 放在 OptionalReward 的已验证 code cave；
- `bulk_import.o` 单独放在 executable tail cave；

避免把合并后的 payload 塞爆单一 `.area`。

---

## 15. 当前 Preview 的明确限制

当前版本**已经支持**：

- 完整 Bank v1.5 `0xBB518` parse/validate；
- PKHeX `0xACA48` 兼容视图导出；
- PKHeX 编辑结果安全回灌；
- Route A V0 PC expected-image 模拟；
- 3DS Offline Mode 应用 `bulk_import.bin` 的主 100 Box；
- 原版 Bank UI 检查；
- 原版本地保存与重新加载；
- 自动 `verify-v0` 验收；
- R4/R5/R6 raw metadata 分析工具。

当前版本**尚未声称完成**：

- 自动生成完整 tag/source/timestamp metadata；
- 对所有 source summaries / NKZT / counters / tail 字段的完整业务命名；
- Official Mode 下载 fresh BankObject 后自动应用 bulk；
- 将本地修改通过原版官方事务上传到服务器；
- HOME 端到端 Bulk Sync 验证。

D6 Official Apply/Save 必须等 Offline T0～T6 中至少关键梯度真实通过后再启用。

---

## 16. 数据安全建议

1. 始终保留未修改的 `bankdata_before.bin`；
2. 每次实机测试前备份 `SD:/3ds/Bank/`；
3. 第一次只做 T0/no-op；
4. 不要把不同账号的完整 Bank 镜像直接互换；
5. PKHeX legacy view 只作为编辑视图，不作为完整 Bank 文件；
6. 完成保存测试后移走 `bulk_import.bin` 再重新启动验证；
7. 不要公开分享包含账号、训练家与时间信息的私人 `bankdata.bin`；
8. Official/D6 未完成验证前，不把 Offline Preview 当作已验证的官方云端上传方案。

## 17. 相关研究文档

- [`bank-v15-bulk-import-roadmap.zh-cn.md`](bank-v15-bulk-import-roadmap.zh-cn.md)：总体研究与开发路线；
- [`bank-v15-legacy-upgrade-analysis.zh-cn.md`](bank-v15-legacy-upgrade-analysis.zh-cn.md)：legacy `0xACA48` → current `0xBB518` 升级分析；
- [`r1-r3-baseline-bankdata-analysis.zh-cn.md`](r1-r3-baseline-bankdata-analysis.zh-cn.md)：tag/source/timestamp 真实样本基线；
- [`r4-r6-metadata-strategy.zh-cn.md`](r4-r6-metadata-strategy.zh-cn.md)：summary/NKZT/counter/tail 策略；
- [`route-a-device-test-protocol.zh-cn.md`](route-a-device-test-protocol.zh-cn.md)：D5 实机分级测试协议；
- [`../../ViewerForBankdata/tools/README.zh-cn.md`](../../ViewerForBankdata/tools/README.zh-cn.md)：`bankbulk.py`、diff 与 classifier 命令详解。
