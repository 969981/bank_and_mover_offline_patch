# bankdata 诊断工具

该目录内的 Python 文件提供 GUI 和命令行分析所需的只读格式解析功能。
输入文件必须显式指定，工具不会自行搜索 bankdata 或 RomFS。

```powershell
python .\tools\parse_bank_file.py "D:\path\to\bankdata.bin"
python .\tools\list_bank_file.py --input "D:\path\to\bankdata.bin" --grid --range 0 3
python .\tools\find_species.py 698 --input "D:\path\to\bankdata.bin"
```

`text_resources.py` 只负责读取 GUI 的本地固化资源，不包含 RomFS 提取功能。
代码中的描述性字段名用于说明实测数据作用，不代表原程序符号。
