# Bank 下载补丁

目标：Pokemon Bank `00040000000C9B00` v6.8.0。

## 行为

补丁在完整 `0xBB518` BankObject 下载完成后执行，不在网络接收过程中分块写入。

1. `0x002D11C4` 的 hook 跳转到 `0x00313910` trampoline。
2. `r7` 保存完整 bankdata 指针。trampoline 保存 `r0-r3`、`r12`、`lr` 和 CPSR 标志后调用 C 载荷。
3. 载荷打开 SDMC，并在需要时创建 `/3ds` 和 `/3ds/Bank`。
4. 创建或打开 `/3ds/Bank/bankdata.bin`，把文件长度设为 `0xBB518`，完整写入并 flush，检查服务返回值和实际写入量，然后关闭文件。写入失败或短写时将文件截断为 0 字节。
5. trampoline 恢复 CPU 状态，补执行被覆盖的 `ldr r8,=0x000BB528`，返回 `0x002D11C8`。

本地文件操作失败不会改变原联网操作的结果。

## 源码结构

- `main.s`：hook、trampoline、可执行边界和 `.importobj`。
- `download_patch.c`：目录创建和完整文件写入。
- `Makefile`：devkitARM 编译、armips 注入与符号导出，以及 Flips IPS 生成。
- `../../include/symbol.inc`：精简后的 Bank、联网、HTTP 和 FS 符号。

## 构建环境

使用标准 `DEVKITARM` 环境变量指定 devkitARM 安装目录。工具路径不包含平台专用的可执行文件后缀；默认使用 `tools/armips/armips` 和 `tools/flips/flips`。各平台可在对应路径放置原生程序，或通过 `ARMIPS`、`IPS_TOOL` 覆盖。

## 注入布局

| 项目 | 值 |
|---|---|
| hook 原指令 | `0x002D11C4 = E59F814C` |
| trampoline | `0x00313910` |
| 导入对象 | `0x00313990–0x00313BAC` |
| C 入口 | `0x003139E8` |
| 可执行区末端 | `0x00314000` |

构建成功后，IPS 直接写入 `bank/release/1-download_patch/luma/titles/00040000000C9B00/code.ips`；修改后的完整代码镜像保留在 `bank/build/1-download_patch/`。
