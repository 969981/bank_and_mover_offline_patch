# Pokemon Bank 与 Poke Mover 离线补丁工程

[English](README.md)

## 当前状态

第 1 步下载补丁已经为 Pokemon Bank 和 Poke Mover 实现。补丁会把完整下载的 Bank 数据保存到 `/3ds/Bank/bankdata.bin`。离线补丁和上传补丁目前仅保留工程接口，尚未实现。

普通玩家安装发行补丁时不需要原始 `.code` 文件，只需要对应 `release` 目录中的 `code.ips`。只有自行重新编译补丁时才需要原始 `.code`。

## 获取原始 code

请只从自己 3DS 上已安装的正版软件中提取代码，不要传播提取出的文件。

1. 按住 `START` 开机，进入 [GodMode9](https://github.com/d0k3/GodMode9)。
2. 按 `HOME`，进入 `Title manager`，选择 SD 卡上的软件列表。
3. 选择已安装的软件本体。本工程使用的是本体，不是更新数据：

   | 软件 | Title ID |
   |---|---|
   | Pokemon Bank | `00040000000C9B00` |
   | Poke Mover | `00040000000C9C00` |

4. 选择 `Open title folder`。
5. 选择包含可执行代码的 `.app`，按 `A`，依次选择 `NCCH image options...` 和 `Extract .code`。
6. 从 `SD:/gm9/out/` 把生成的、已经解压的 `.dec.code` 文件复制到电脑。
7. 按下表改名并放入对应工程目录。

## 所需文件及 SHA-1

| 软件 | 工程内路径 | 大小 | SHA-1 |
|---|---|---:|---|
| Pokemon Bank | `bank/00040000000C9B00.code` | 2,801,664 字节 | `5AB630856835DCF2DBDF9A62244DD19E46AE1C7C` |
| Poke Mover | `mover/00040000000C9C00.code` | 2,269,184 字节 | `583859C1E874D11650EFBDDE51F470ECF96900C4` |

如果文件大小或 SHA-1 不一致，说明提取出的代码不是本工程针对的版本。不要使用不匹配的文件生成 IPS。

## 编译

需要准备：

- GNU Make 和兼容 POSIX 的 shell。
- devkitARM，并正确设置 `DEVKITARM` 环境变量。
- 本仓库目前只存放了 Windows 版 [armips](https://github.com/Kingcom/armips) 和 [Floating IPS](https://github.com/Sir-Walrus/Flips) 可执行文件。其他平台请从对应项目的官方发布页面下载兼容的可执行文件，或从官方源码自行编译，然后通过 Make 变量 `ARMIPS` 和 `IPS_TOOL` 指定这些可执行文件的路径。

在仓库根目录运行：

```sh
make -C bank clean
make -C bank

make -C mover clean
make -C mover
```

如果当前平台无法运行工程自带的 Windows 工具，请指定本机工具路径：

```sh
make -C bank ARMIPS=/path/to/armips IPS_TOOL=/path/to/flips
make -C mover ARMIPS=/path/to/armips IPS_TOOL=/path/to/flips
```

发行补丁将生成到：

```text
bank/release/1-download_patch/luma/titles/00040000000C9B00/code.ips
mover/release/1-download_patch/luma/titles/00040000000C9C00/code.ips
```

安装时，将对应发行目录中的 `luma` 文件夹合并到 3DS SD 卡根目录，并在 Luma3DS 配置中启用 `Enable game patching`。Luma3DS 会从 `/luma/titles/<Title ID>/code.ips` 载入 IPS 补丁。
