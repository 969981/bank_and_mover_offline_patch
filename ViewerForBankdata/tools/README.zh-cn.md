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

运行测试：

```powershell
python -m unittest discover -s .\tests -v
```

`text_resources.py` 只负责读取 GUI 的本地固化资源，不包含 RomFS 提取功能。
代码中的描述性字段名用于说明实测数据作用，不代表原程序符号。
