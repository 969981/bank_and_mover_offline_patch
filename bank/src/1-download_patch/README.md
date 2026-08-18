# Bank Download Patch

Target: Pokemon Bank `00040000000C9B00` v6.8.0.

## Behavior

The patch runs after the complete `0xBB518` BankObject has been downloaded. It does not write network chunks while the transfer is in progress.

1. The hook at `0x002D11C4` branches to the trampoline at `0x00313910`.
2. `r7` contains the complete bankdata pointer. The trampoline preserves `r0-r3`, `r12`, `lr`, and CPSR flags before calling the C payload.
3. The payload opens SDMC and creates `/3ds` and `/3ds/Bank` when necessary.
4. It creates or opens `/3ds/Bank/bankdata.bin`, sets its length to `0xBB518`, writes the complete buffer with flush enabled, verifies the service result and byte count, and closes the file. A failed or short write truncates the file to zero bytes.
5. The trampoline restores CPU state, reproduces the overwritten `ldr r8,=0x000BB528`, and returns to `0x002D11C8`.

A local file error does not change the result of the original online operation.

## Source layout

- `main.s`: hook, trampoline, executable bounds, and `.importobj`.
- `download_patch.c`: directory creation and complete-file write.
- `Makefile`: devkitARM compile, armips injection and symbol export, and Flips IPS creation.
- `../../include/symbol.inc`: curated Bank, network, HTTP, and FS symbols.

## Build environment

Set the standard `DEVKITARM` environment variable to the devkitARM installation directory. Tool paths do not contain platform-specific executable suffixes. The defaults are `tools/armips/armips` and `tools/flips/flips`; place native executables at those paths or override `ARMIPS` and `IPS_TOOL`.

## Injection layout

| Item | Value |
|---|---|
| Original hook instruction | `0x002D11C4 = E59F814C` |
| Trampoline | `0x00313910` |
| Imported object | `0x00313990–0x00313BAC` |
| C entry | `0x003139E8` |
| Executable limit | `0x00314000` |

A successful build writes the IPS directly to `bank/release/1-download_patch/luma/titles/00040000000C9B00/code.ips`. The modified full code image remains under `bank/build/1-download_patch/`.
