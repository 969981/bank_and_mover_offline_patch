# bankdata 诊断工具

该目录内的 Python 文件提供 GUI 和命令行分析所需的只读格式解析功能。
输入文件必须显式指定，工具不会自行搜索 bankdata 或 RomFS。

```powershell
python .\tools\parse_bank_file.py "D:\path\to\bankdata.bin"
python .\tools\list_bank_file.py --input "D:\path\to\bankdata.bin" --grid --range 0 3
python .\tools\find_species.py 698 --input "D:\path\to\bankdata.bin"
python .\tools\diff_bank_file.py "D:\before.bin" "D:\after.bin"
python .\tools\diff_bank_file.py "D:\before.bin" "D:\after.bin" --json "D:\diff.json"
```

`bank_v15_layout.py` 固化 Bank v1.5 `0xBB518` serialized body 的物理区域和
3000 个 Bank 槽的统一索引公式。`diff_bank_file.py` 会把同一槽的 Pokémon payload、
format tag、source software 和 timestamp 变化聚合在一起，同时单独列出 source summary、
Pokedex-like aggregate、counter、tail 等区域的变更范围。

这些工具只报告 raw 值与物理变化；tag/source/timestamp 的业务枚举由后续研究确认，
不会因为数值看起来合理就自动赋予业务名称。

## Route A：完整镜像与 PKHeX 兼容视图

`bankbulk.py` 用于完整 `0xBB518` Bank v1.5 镜像与 PKHeX `Bank7` 兼容视图之间的安全转换。
完整镜像始终是主模板；PKHeX 兼容视图固定为 legacy 长度 `0xACA48`，只用于 PKHeX 查看/编辑。

验证完整镜像：

```powershell
python .\tools\bankbulk.py validate "D:\Bank\bankdata.bin"
python .\tools\bankbulk.py inspect "D:\Bank\bankdata.bin"
```

导出只用于 PKHeX 的兼容视图：

```powershell
python .\tools\bankbulk.py export-pkhex `
  "D:\Bank\bankdata.bin" `
  -o "D:\Bank\bankdata_pkhex_view.bin"
```

输出文件长度必须为：

```text
0xACA48 = 707144 bytes
```

PKHeX 编辑并保存这个兼容视图以后，不要把它直接作为 Bank v1.5 文件或上传对象。使用原始完整
`bankdata.bin` 作为模板回灌：

```powershell
python .\tools\bankbulk.py import-pkhex `
  "D:\Bank\bankdata.bin" `
  "D:\Bank\bankdata_pkhex_view_edited.bin" `
  -o "D:\Bank\bulk_import.bin"
```

回灌只复制：

```text
0x00017C .. 0x0AAF14 (end-exclusive)
```

也就是 100 个主 Bank Box（每盒 30×`0xE8` Pokémon + `0x26` box metadata）。以下区域会保留完整
current template，不会从 PKHeX view 覆盖：

- Header；
- Transfer Box；
- `0xACA44..0xACA47` legacy/current overlap；
- current-format tag/source/timestamp 与后续 metadata。

如果不经过 PKHeX，只需要从一个已校验的完整镜像生成 `bulk_import.bin`：

```powershell
python .\tools\bankbulk.py build `
  "D:\Bank\bankdata.bin" `
  -o "D:\Bank\bulk_import.bin"
```

运行测试：

```powershell
python -m unittest discover -s .\tests -v
```

`text_resources.py` 只负责读取 GUI 的本地固化资源，不包含 RomFS 提取功能。
代码中的描述性字段名用于说明实测数据作用，不代表原程序符号。
