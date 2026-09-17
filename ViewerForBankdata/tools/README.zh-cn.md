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
opaque/NKZT block、counter、tail 等区域的变更范围。

这些工具只报告 raw 值与物理变化；tag/source/timestamp 的业务枚举由后续研究确认，
不会因为数值看起来合理就自动赋予业务名称。

## R4/R5/R6 raw metadata classifier

```powershell
python .\tools\r456_classifier.py "D:\Bank\bankdata.bin"
python .\tools\r456_classifier.py "D:\Bank\bankdata.bin" --json "D:\Bank\r456.json"
```

它只统计 `8×0x44` source summaries、`0x7260` opaque/NKZT block、4-byte counters 和
`0x100` tail 的 raw 值与非零范围，不把未知字段强行命名。Route A V0 对这些区域一律
`PRESERVE_RUNTIME`。

## Route A：完整镜像与 PKHeX 兼容视图

`bankbulk.py` 用于完整 `0xBB518` Bank v1.5 镜像与 PKHeX `Bank7` 兼容视图之间的安全转换。
完整镜像始终是主模板；PKHeX 兼容视图固定为 legacy 长度 `0xACA48`，只用于 PKHeX 查看/编辑。

验证完整镜像：

```powershell
python .\tools\bankbulk.py validate "D:\Bank\bankdata.bin"
python .\tools\bankbulk.py inspect "D:\Bank\bankdata.bin"
```

### 1. 导出只用于 PKHeX 的兼容视图

```powershell
python .\tools\bankbulk.py export-pkhex `
  "D:\Bank\bankdata.bin" `
  -o "D:\Bank\bankdata_pkhex_view.bin"
```

输出文件长度必须为：

```text
0xACA48 = 707144 bytes
```

本质上它是完整 current 文件的前 `0xACA48` 字节；PKHeX `Bank7` 从 `0x17C` 开始读取
100 个主 Box。这个文件只用于 PKHeX 查看/编辑，不应直接替代 current `bankdata.bin`，
也不应直接用于官方上传。

### 2. PKHeX 编辑以后回灌到完整 current 镜像

PKHeX 保存后，使用原始完整 `bankdata.bin` 作为模板：

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

也就是 100 个主 Bank Box（每盒 30×`0xE8` Pokémon + `0x26` box metadata）。以下区域会保留
完整 current template，不会从 PKHeX view 覆盖：

- Header；
- Transfer Box；
- `0xACA44..0xACA47` legacy/current overlap；
- current-format tag/source/timestamp；
- source summaries、opaque/NKZT、counters、tail。

### 3. 不经过 PKHeX 时生成 bulk_import.bin

```powershell
python .\tools\bankbulk.py build `
  "D:\Bank\bankdata.bin" `
  -o "D:\Bank\bulk_import.bin"
```

### 4. 在 PC 上模拟 3DS Route A V0 白名单应用

3DS V0 不是整文件 memcpy，而是把 `bulk_import.bin` 的 100 个主 Box 覆盖到当前 runtime，
其它区域全部保留 runtime。可以先在 PC 生成理论 expected image：

```powershell
python .\tools\bankbulk.py apply-v0 `
  "D:\Bank\bankdata.bin" `
  "D:\Bank\bulk_import.bin" `
  -o "D:\Bank\expected_after_apply.bin"
```

然后用结构化 diff 检查：

```powershell
python .\tools\diff_bank_file.py `
  "D:\Bank\bankdata.bin" `
  "D:\Bank\expected_after_apply.bin" `
  --json "D:\Bank\expected_diff.json"
```

## 3DS Offline Mode V0

把完整 `bulk_import.bin` 放到：

```text
sd:/3ds/Bank/bulk_import.bin
```

Offline Mode 先正常读取：

```text
sd:/3ds/Bank/bankdata.bin
```

随后检查 `bulk_import.bin`。只有当其长度为 `0xBB518`、version=`2`、boxCount=`100` 时，
才把 `0x17C..0xAAF14` 直接读到运行时 BankObject。缺失或明显无效的 bulk 文件不会改动当前
Bank；如果主 Box 大块读取发生 short/error、可能已经部分覆盖 runtime，则补丁重新加载
`bankdata.bin` 恢复完整对象后再进入 Bank UI。

V0 **不会自动保存**。进入原版 Bank Box UI 后先检查内容，再使用正常 Bank 保存流程。
如果不保存退出，`bankdata.bin` 不会被安装为新版本；`bulk_import.bin` 本身也不会被删除，
所以下次启动仍会再次应用，测试完成后应自行移走或重命名。

运行 PC 测试：

```powershell
python -m unittest discover -s .\tests -v
```

Host C 白名单核心测试：

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror \
  bank/src/bulk_import_host_test.c -o bulk_import_host_test
./bulk_import_host_test
```

`text_resources.py` 只负责读取 GUI 的本地固化资源，不包含 RomFS 提取功能。
代码中的描述性字段名用于说明实测数据作用，不代表原程序符号。
