# bankdata 查看器

本目录包含只读的 Python 标准库 GUI 查看器和少量 bankdata 诊断工具。
GUI 已固化十种语言选择所需的文本资源，运行时不依赖解包的 RomFS。

```powershell
cd ViewerForBankdata
python .\gui\bank_viewer.py
```

启动时不预设输入文件，请在文件选择窗口中自行打开 bankdata。GUI 参数见
`gui/README.zh-cn.md`，命令行诊断工具见 `tools/README.zh-cn.md`。
