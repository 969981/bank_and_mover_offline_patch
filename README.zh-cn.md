# Pokemon Bank 与 Poke Mover 离线补丁工程

[English](README.md)

## 当前状态

Pokemon Bank 和 Poke Mover 各自只保留一个当前维护的合并补丁。本地银行数据统一使用 `/3ds/Bank/bankdata.bin`。

- Pokemon Bank 合并补丁可在下载模式与离线模式之间切换。
- Poke Mover 合并补丁可在原版模式与离线模式之间切换。

上传补丁现已永久废止，不再制作或发布。安全上传必须明确处理服务端当前的身份字段、修订号、时间戳、事务状态，以及本地与远端同时修改时的冲突；目前尚未充分确认这些校验规则。为避免修改服务端银行数据带来的安全风险，本工程不提供上传补丁的构建目标或发行文件。

普通玩家安装发行补丁时不需要原始 `.code` 文件，只需要对应 `release` 目录中的 `code.ips`。只有自行重新编译补丁时才需要原始 `.code`。

## 获取原始 code 与 RomFS

请只从自己 3DS 上已安装的正版软件中提取代码，不要传播提取出的文件。

1. 按住 `START` 开机，进入 [GodMode9](https://github.com/d0k3/GodMode9)。
2. 按 `HOME`，进入 `Title manager`，选择 SD 卡上的软件列表。
3. 选择已安装的软件本体。本工程使用的是本体，不是更新数据：

   | 软件 | Title ID |
   |---|---|
   | Pokemon Bank | `00040000000C9B00` |
   | Poke Mover | `00040000000C9C00` |

4. 选择 `Open title folder`。
5. 选择包含可执行代码的 `.app`，按 `A`，依次选择 `NCCH image options...` 和 `Extract .code`。完成后，GodMode9 会把 `<Title ID>.dec.code` 写入 `SD:/gm9/out/`。
6. 再次选择同一个 `.app`，按 `A`，依次选择 `NCCH image options...` 和 `Mount image to drive`。进入挂载的 `G:` 盘后，把光标移到 `romfs` 目录并按 `Y` 复制；按 `B` 返回驱动器列表，进入 `[0:] SDCARD` → `gm9` → `out`，按 `Y` 粘贴，再按 `A` 确认。完整目录将保存为 `SD:/gm9/out/romfs/`。
7. 按 `HOME`，选择 `Poweroff system`。把 SD 卡连接到电脑，然后按下列位置复制文件：

   - Bank：把 `SD:/gm9/out/00040000000C9B00.dec.code` 复制到 `bank/rom/exefs/00040000000C9B00.dec.code`，把 `SD:/gm9/out/romfs/` 复制到 `bank/rom/romfs/`。
   - Mover：把 `SD:/gm9/out/00040000000C9C00.dec.code` 复制到 `mover/rom/exefs/00040000000C9C00.dec.code`，把 `SD:/gm9/out/romfs/` 复制到 `mover/rom/romfs/`。

   每次只处理一个软件；复制到电脑后先移走 `SD:/gm9/out/romfs/`，再提取另一个软件，避免同名目录相互覆盖。

## 所需文件及 SHA-1

| 软件 | 工程内路径 | 大小 | SHA-1 |
|---|---|---:|---|
| Pokemon Bank | `bank/rom/exefs/00040000000C9B00.dec.code` | 2,801,664 字节 | `5AB630856835DCF2DBDF9A62244DD19E46AE1C7C` |
| Poke Mover | `mover/rom/exefs/00040000000C9C00.dec.code` | 2,269,184 字节 | `583859C1E874D11650EFBDDE51F470ECF96900C4` |

如果文件大小或 SHA-1 不一致，说明提取出的代码不是本工程针对的版本，或没有正确完成提取与解压。不要使用不匹配的文件生成 IPS。RomFS 资源应保持各文件的原生格式，直接复制挂载后的完整 `romfs` 目录，不要再对整个目录进行额外解压。

本地输入文件的完整布局如下：

```text
bank/rom/
├── exefs/
│   └── 00040000000C9B00.dec.code
└── romfs/
    └── ...

mover/rom/
├── exefs/
│   └── 00040000000C9C00.dec.code
└── romfs/
    └── ...
```

Git 只跟踪各自空目录中的 `rom/.gitkeep` 占位文件。提取出的 `.code` 和 RomFS 数据
均已被 Git 忽略，不应提交或传播。

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

发行用 Title ID 目录将直接生成到各软件的 `release` 目录：

```text
bank/release/00040000000C9B00/
├── code.ips
└── romfs/

mover/release/00040000000C9C00/
├── code.ips
└── romfs/
```

安装时，把对应的完整 Title ID 目录复制到 `SD:/luma/titles/`，并在 Luma3DS 配置中启用 `Enable game patching`。Luma3DS 会从 `/luma/titles/<Title ID>/code.ips` 载入 IPS 补丁。
