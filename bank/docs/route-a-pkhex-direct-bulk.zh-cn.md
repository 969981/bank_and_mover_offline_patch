# Route A：直接使用 PKHeX Bank7 视图作为 bulk_import.bin

## 背景

早期 Route A Preview 只接受完整 Pokémon Bank v1.5 current 镜像：

```text
0xBB518
```

因此，把 PKHeX 保存出来的 Bank7 兼容视图：

```text
0xACA48
```

直接命名为 `SD:/3ds/Bank/bulk_import.bin` 时，旧 Preview 会因为文件长度不匹配而跳过导入，Bank UI 仍显示原来的 `bankdata.bin` 内容。

## 当前行为

从本修复开始，Offline Route A 同时接受两种 `bulk_import.bin`：

```text
0xBB518  完整 current Bank v1.5 镜像
0xACA48  PKHeX Bank7 兼容视图
```

两种输入都必须满足：

```text
version  = 2
boxCount = 100
```

实际应用范围保持不变：

```text
0x00017C .. 0x0AAF14 (end-exclusive)
```

也就是主 100 个 Bank Box。Header、Transfer Box、tag/source/timestamp、source summaries、NKZT、counters 和 tail 都继续保留当前 runtime `bankdata.bin` 的值。

## 使用方法

如果已经用 PKHeX 编辑并保存出：

```text
bankdata_pkhex_view.bin
size = 0xACA48
```

可以直接重命名为：

```text
bulk_import.bin
```

放到：

```text
SD:/3ds/Bank/bulk_import.bin
```

同时保留完整：

```text
SD:/3ds/Bank/bankdata.bin
```

进入 Pokémon Bank 的 Offline Mode，选择任意兼容游戏后，补丁会先载入完整 `bankdata.bin`，再把 `bulk_import.bin` 的主 100 Box 覆盖到运行时 BankObject。游戏本身只用于进入原版 Bank Box UI，不决定 bulk 的内容。

## 兼容旧 Preview

如果仍使用只接受 `0xBB518` 的旧 Preview，可继续使用 PC 工具：

```powershell
python .\tools\bankbulk.py import-pkhex `
  "D:\Bank\bankdata.bin" `
  "D:\Bank\bankdata_pkhex_view_edited.bin" `
  -o "D:\Bank\bulk_import.bin"
```

它会生成完整 `0xBB518` bulk 镜像。

## 测试建议

第一次建议只修改一个槽或一个盒子。进入 Box UI 后确认 upper Bank side 已显示 bulk 内容，再执行正常本地保存。保存完成后移走 `bulk_import.bin`，重新启动确认 `bankdata.bin` 已真正持久化。
