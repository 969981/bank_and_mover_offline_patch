# Pokemon Bank and Poke Mover Offline Patch Project

[简体中文](README.zh-cn.md)

## Current status

One maintained combined patch is provided for each application. All local Bank data uses `/3ds/Bank/bankdata.bin`.

- Pokemon Bank's combined patch switches between download and offline modes.
- Poke Mover's combined patch switches between original and offline modes.

The upload patch has been permanently discontinued and will not be implemented or distributed. Safe re-upload would require proven handling of current server-side identity fields, revisions, timestamps, transaction state, and conflicts between local and remote changes. Those validation rules are not sufficiently established, so this project will not risk modifying server-side Bank data. There is no upload-patch build target or release.

Players installing a release do not need an original `.code` file. They only need the generated `code.ips` under the appropriate `release` directory. The original `.code` files are required only when rebuilding the patches.

## Obtaining the original code and RomFS

Extract the code only from titles installed on your own 3DS. Do not redistribute the extracted files.

1. Hold `START` while booting the console to open [GodMode9](https://github.com/d0k3/GodMode9).
2. Press `HOME`, open `Title manager`, and select the SD title list.
3. Select the installed base application. These patches use the base titles, not update titles:

   | Application | Title ID |
   |---|---|
   | Pokemon Bank | `00040000000C9B00` |
   | Poke Mover | `00040000000C9C00` |

4. Select `Open title folder`.
5. Select the executable `.app`, press `A`, and choose `NCCH image options...` followed by `Extract .code`. GodMode9 writes `<Title ID>.dec.code` to `SD:/gm9/out/`.
6. Select the same `.app` again, press `A`, and choose `NCCH image options...` followed by `Mount image to drive`. In the mounted `G:` drive, highlight the `romfs` directory and press `Y` to copy it. Press `B` to return to the drive list, open `[0:] SDCARD` → `gm9` → `out`, press `Y` to paste, and press `A` to confirm. The complete directory is saved as `SD:/gm9/out/romfs/`.
7. Press `HOME` and select `Poweroff system`. Connect the SD card to the computer, then copy the files to these exact locations:

   - Bank: copy `SD:/gm9/out/00040000000C9B00.dec.code` to `bank/rom/exefs/00040000000C9B00.dec.code`, and copy `SD:/gm9/out/romfs/` to `bank/rom/romfs/`.
   - Mover: copy `SD:/gm9/out/00040000000C9C00.dec.code` to `mover/rom/exefs/00040000000C9C00.dec.code`, and copy `SD:/gm9/out/romfs/` to `mover/rom/romfs/`.

   Process one application at a time. After copying it to the computer, move `SD:/gm9/out/romfs/` out of the output directory before extracting the other application, so the identically named directories cannot overwrite each other.

## Required files and SHA-1

| Application | Project path | Size | SHA-1 |
|---|---|---:|---|
| Pokemon Bank | `bank/rom/exefs/00040000000C9B00.dec.code` | 2,801,664 bytes | `5AB630856835DCF2DBDF9A62244DD19E46AE1C7C` |
| Poke Mover | `mover/rom/exefs/00040000000C9C00.dec.code` | 2,269,184 bytes | `583859C1E874D11650EFBDDE51F470ECF96900C4` |

A different size or SHA-1 means the extracted code is not the version targeted by this project or was not extracted and decompressed correctly. Do not build an IPS against a mismatched file. RomFS resources remain in their native per-file formats; copy the mounted `romfs` tree as-is rather than attempting another whole-tree decompression.

The complete local input layout is:

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

Only each empty `rom/.gitkeep` placeholder is tracked. Extracted `.code` and
RomFS data are ignored by Git and must not be committed or redistributed.

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

The release title directories are written directly below each application's `release` directory:

```text
bank/release/00040000000C9B00/
├── code.ips
└── romfs/

mover/release/00040000000C9C00/
├── code.ips
└── romfs/
```

To install a release, copy its complete Title ID directory into `SD:/luma/titles/` and enable `Enable game patching` in the Luma3DS configuration. Luma3DS loads title IPS patches from `/luma/titles/<Title ID>/code.ips`.
