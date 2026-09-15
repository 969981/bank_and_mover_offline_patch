# Bank Download Patch

Target: Pokemon Bank `00040000000C9B00` v1.5.

## Behavior

1. Startup, account initialization, first-user data creation, and all networking before the feature menu follow the stock flow.
2. The stock menu and order remain unchanged; only the first entry is renamed **Download Bank Data**.
3. Selecting it retains stock game detection, game selection, transaction recovery, and server connection. Ordinary Bank download uses an appended local-download status message.
4. When the remote-success callback receives the complete `0xBB518` BankObject, it first checks the shared state's mode byte. Only ordinary Bank mode `0` saves the object to `/3ds/Bank/bankdata.bin`; HOME mode `1` and every other mode perform no local file operation.
5. The payload creates `/3ds` and `/3ds/Bank` as needed, writes and flushes `bankdata.tmp`, checks size-setting and write results including the actual byte count, rotates the old file to `bankdata.bak`, then renames the temporary file to `bankdata.bin`. Failure handling attempts to retain or restore the previous file.
6. State-12 results `5`, `6`, and `12` are redirected to stock state 19, skipping points/rewards, the Bank Box, and the save UI while retaining the stock no-save transaction-release and disconnect flow.
7. Only the disconnect screen reached after the first menu item uses the appended completion message. Every other exit retains the stock disconnect line.
8. The former Pokémon HOME entry is renamed **Choose Language** and its outer-flow result is redirected from HOME state 28 to the stock language-selection state 1. The redirect first hides the current menu's common UI layers so stale upper-screen text cannot remain behind the language prompt. After selection, stock state 21 still performs and waits for session cleanup, but displays an appended blank line so the new font does not render a stale-language disconnect message. HOME confirmation, networking, and Box UI are never entered. Shared confirmation text and button behavior remain stock.

The menu name, download status, and completion message are localized in all ten shipped message sets: Japanese kana, Japanese kanji, English, French, Italian, German, Spanish, Korean, Simplified Chinese, and Traditional Chinese.

As a second isolation layer, the remote-success callback still skips local saving for HOME mode `1` and every mode other than ordinary Bank mode `0`.

## Source layout

- `main.s`: hook, trampoline, executable bounds, and `.importobj`.
- `download_patch.c`: directory creation and complete-file write.
- `patch_messages.py`: verified message-file and GARC rebuild for the ten LayeredFS archives.
- `Makefile`: devkitARM compile, armips injection and symbol export, and Flips IPS creation.
- `../../include/symbol.inc`: curated Bank, network, HTTP, and FS symbols.

## Build environment

Set the standard `DEVKITARM` environment variable to the devkitARM installation directory. Tool paths do not contain platform-specific executable suffixes. The defaults are `tools/armips/armips` and `tools/flips/flips`; place native executables at those paths or override `ARMIPS` and `IPS_TOOL`.

Place the extracted base-title RomFS under `bank/romfs`, so that `bank/romfs/a/0/0/4` through `bank/romfs/a/0/1/3` exist. Alternatively, set `ROMFS_SOURCE` to the extracted RomFS root. Python 3 is required for the message build; override `PYTHON` when its executable is not named `python3`.

## Injection layout

| Item | Value |
|---|---|
| State-12 result-5 target | `0x002A57E0` |
| State-12 results-6/12 branch | `0x002A57F0` |
| Original no-save exit target | `0x002A58F0` (state 19) |
| Complete remote-success callback capture | `0x002D11C4` |
| Conditional state-16/28 message | `0x002AFE50` (Bank line 96; HOME retains stock line 14) |
| First-item completion marker | BankFlow `+0x1D` → disconnect-state `+0x3D` (object padding bytes) |
| Conditional disconnect text | `0x002ABD8C` (line 97 for the first item; stock line 13 otherwise) |
| Former HOME result redirect | `0x002A56F0` (state 4 result 23: state 28 → language state 1) |
| Luma LayeredFS reserved area | `0x00313910–0x00313A3F` |
| Trampoline area | `0x00313A40–0x00313B4F` |
| Imported-object area | `0x00313B50–0x00313FFF` |

Luma applies `code.ips` before installing its LayeredFS redirection payload. The
loader places that payload at the original end of `.text` (`0x00313910` for this
title), so the download patch deliberately leaves the first `0x130` bytes of
executable padding unused. This prevents LayeredFS from overwriting patch code.
| C entry | See generated `armips-symbols.txt` |
| Executable limit | `0x00314000` |

A successful build creates the complete Luma tree under `bank/release/1-download_patch/luma/titles/00040000000C9B00/`: `code.ips` plus the ten modified `romfs/a/...` archives. Copy the `luma` directory to the SD card and enable Luma3DS game patching. The modified full code image remains under `bank/build/1-download_patch/`.

## Format references

- [Luma3DS loader patch implementation](https://github.com/LumaTeam/Luma3DS/blob/master/sysmodules/loader/source/patcher.c) defines the title-specific `code.ips` and `romfs` lookup paths.
- [pkNX TextFile implementation](https://github.com/kwsch/pkNX/blob/master/pkNX.Structures/Text/TextFile.cs) documents the Gen 6/7 message-file keys and line encoding used by the rebuild tool.
