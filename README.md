# Pokemon Bank and Poke Mover Offline Patch Project

[简体中文](README.zh-cn.md)

## Current status

Step 1, the download patch, is implemented for both Pokemon Bank and Poke Mover. It saves the complete downloaded Bank data to `/3ds/Bank/bankdata.bin`. The offline and upload patches are reserved for later implementation.

Players installing a release do not need an original `.code` file. They only need the generated `code.ips` under the appropriate `release` directory. The original `.code` files are required only when rebuilding the patches.

## Obtaining the original code

Extract the code only from titles installed on your own 3DS. Do not redistribute the extracted files.

1. Hold `START` while booting the console to open [GodMode9](https://github.com/d0k3/GodMode9).
2. Press `HOME`, open `Title manager`, and select the SD title list.
3. Select the installed base application. These patches use the base titles, not update titles:

   | Application | Title ID |
   |---|---|
   | Pokemon Bank | `00040000000C9B00` |
   | Poke Mover | `00040000000C9C00` |

4. Select `Open title folder`.
5. Select the executable `.app`, press `A`, and choose `NCCH image options...` followed by `Extract .code`.
6. Copy the resulting decompressed `.dec.code` file from `SD:/gm9/out/` to the computer.
7. Rename and place each file as shown below.

## Required files and SHA-1

| Application | Project path | Size | SHA-1 |
|---|---|---:|---|
| Pokemon Bank | `bank/00040000000C9B00.code` | 2,801,664 bytes | `5AB630856835DCF2DBDF9A62244DD19E46AE1C7C` |
| Poke Mover | `mover/00040000000C9C00.code` | 2,269,184 bytes | `583859C1E874D11650EFBDDE51F470ECF96900C4` |

A different size or SHA-1 means the extracted code is not the version targeted by this project. Do not build an IPS against a mismatched file.

## Building

Requirements:

- GNU Make and a POSIX-compatible shell.
- devkitARM with the `DEVKITARM` environment variable set.
- This repository currently includes Windows executables only for [armips](https://github.com/Kingcom/armips) and [Floating IPS](https://github.com/Sir-Walrus/Flips). On other platforms, download compatible executables from the projects' official release pages or build them from the official source, then set the `ARMIPS` and `IPS_TOOL` Make variables to those executable paths.

From the repository root, run:

```sh
make -C bank clean
make -C bank

make -C mover clean
make -C mover
```

On a platform that cannot run the bundled Windows tools, override their paths:

```sh
make -C bank ARMIPS=/path/to/armips IPS_TOOL=/path/to/flips
make -C mover ARMIPS=/path/to/armips IPS_TOOL=/path/to/flips
```

The release patches are written to:

```text
bank/release/1-download_patch/luma/titles/00040000000C9B00/code.ips
mover/release/1-download_patch/luma/titles/00040000000C9C00/code.ips
```

To install a release, merge its `luma` directory into the root of the 3DS SD card and enable `Enable game patching` in the Luma3DS configuration. Luma3DS loads title IPS patches from `/luma/titles/<Title ID>/code.ips`.
