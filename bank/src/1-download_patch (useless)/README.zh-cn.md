# Bank 下载补丁

目标：Pokemon Bank `00040000000C9B00` v1.5。

## 行为

1. 开机、账户初始化、首次用户数据创建和进入功能选单前的联网全部保留原流程。
2. 原版功能选单及排列不变，只把第一项的显示名称改为“下载银行数据到本地”。
3. 点击第一项后仍执行原版游戏检测、游戏选择、事务恢复和服务器连接；普通 Bank 下载显示新增的本地下载提示。
4. 远端成功回调取得完整 `0xBB518` BankObject 后，先检查共用状态的模式字节；只有第一项使用的普通 Bank 模式 `0` 才将其一次性保存到 `/3ds/Bank/bankdata.bin`。HOME 的模式 `1` 及其他模式不执行任何本地文件操作。
5. 载荷按需创建 `/3ds` 和 `/3ds/Bank`，写入并 flush `bankdata.tmp`，检查文件大小设置、写入返回值和实际写入量，把旧文件轮换为 `bankdata.bak`，再重命名为 `bankdata.bin`；失败时尽量保留或恢复旧文件。
6. state 12 的结果 `5`、`6` 和 `12` 改到原版 state 19，从而跳过里程/礼物、盒子和保存界面，并执行原版“不保存并结束”的事务释放与断网流程。
7. 只有第一项完成后的断网界面显示：“已下载银行数据到本地，正在断开互联网……请关闭游戏并更换补丁。”其他退出路径继续使用原版断网文本。
8. 原 Pokémon HOME 入口改名为“选择语言”，并把它的外层流程结果从 HOME 状态 28 重定向到原版语言选择状态 1。重定向会先隐藏当前选单的通用 UI 图层，避免旧的上屏文本残留在语言提示下方。选择完成后仍由原版 state 21 执行并等待会话清理，但显示新增的空白消息行，避免新字库绘制旧语言断网文本。流程不会进入 HOME 确认页、联网或盒子界面；所有共用确认文本和按钮行为均保持原版。

选单名称、下载状态和完成提示均已分别本地化到软件自带的十套消息资源：日文假名、日文汉字、英文、法文、意大利文、德文、西班牙文、韩文、简体中文和繁体中文。

作为第二层隔离，远端成功回调仍只允许普通 Bank 模式 `0` 写入本地；HOME 模式 `1` 及其他模式都会跳过本地保存。

## 源码结构

- `main.s`：hook、trampoline、可执行边界和 `.importobj`。
- `download_patch.c`：目录创建和完整文件写入。
- `patch_messages.py`：重建并复核十套 LayeredFS 消息档案。
- `Makefile`：devkitARM 编译、armips 注入与符号导出，以及 Flips IPS 生成。
- `../../include/symbol.inc`：精简后的 Bank、联网、HTTP 和 FS 符号。

## 构建环境

使用标准 `DEVKITARM` 环境变量指定 devkitARM 安装目录。工具路径不包含平台专用的可执行文件后缀；默认使用 `tools/armips/armips` 和 `tools/flips/flips`。各平台可在对应路径放置原生程序，或通过 `ARMIPS`、`IPS_TOOL` 覆盖。

把本体提取出的 RomFS 放到 `bank/romfs`，并确保存在 `bank/romfs/a/0/0/4` 至 `bank/romfs/a/0/1/3`；也可以用 `ROMFS_SOURCE` 指定 RomFS 根目录。消息构建需要 Python 3；如果程序名不是 `python3`，请覆盖 `PYTHON`。

## 注入布局

| 项目 | 值 |
|---|---|
| state 12 结果 5 目标 | `0x002A57E0` |
| state 12 结果 6/12 分支 | `0x002A57F0` |
| 原始“不保存并结束”目标 | `0x002A58F0`（state 19） |
| 远端成功回调完整数据捕获 | `0x002D11C4` |
| state 16/28 条件消息选择 | `0x002AFE50`（Bank 使用第 96 行；HOME 保留原版第 14 行） |
| 第一项完成标记 | BankFlow `+0x1D` → 断网状态对象 `+0x3D`（均为对象内填充字节） |
| 条件断网文本 | `0x002ABD8C`（第一项用第 97 行；其他路径保留第 13 行） |
| 原 HOME 结果重定向 | `0x002A56F0`（state 4 结果 23：state 28 → 语言 state 1） |
| Luma LayeredFS 保留区域 | `0x00313910–0x00313A3F` |
| 跳板区域 | `0x00313A40–0x00313B4F` |
| 导入对象区域 | `0x00313B50–0x00313FFF` |

Luma 会先应用 `code.ips`，再安装 LayeredFS 重定向载荷。加载器会从本标题
原始 `.text` 末尾（`0x00313910`）放置该载荷，因此下载补丁主动空出可执行
填充区的前 `0x130` 字节，避免补丁代码被 LayeredFS 覆盖。
| C 入口 | 以生成的 `armips-symbols.txt` 为准 |
| 可执行区末端 | `0x00314000` |

构建成功后会在 `bank/release/1-download_patch/luma/titles/00040000000C9B00/` 下生成完整 Luma 目录：`code.ips` 和十个修改后的 `romfs/a/...` 档案。把 `luma` 目录复制到 SD 卡并启用 Luma3DS 游戏补丁即可。修改后的完整代码镜像仍保留在 `bank/build/1-download_patch/`。

## 格式参考

- [Luma3DS loader 补丁实现](https://github.com/LumaTeam/Luma3DS/blob/master/sysmodules/loader/source/patcher.c)定义了按 Title ID 查找 `code.ips` 和 `romfs` 的路径。
- [pkNX TextFile 实现](https://github.com/kwsch/pkNX/blob/master/pkNX.Structures/Text/TextFile.cs)公开了重建工具所用的第六、七世代消息文件密钥与行编码。
