# Mover Download Patch

Target: Poke Mover `00040000000C9C00` v5.5.0.

## Behavior

The patch runs after the complete `0xBB518` BankObject has been downloaded. It does not write network chunks while the transfer is in progress.

1. The hook at `0x0025C990` branches to the trampoline at `0x0028D5F0`.
2. `r8` contains the complete bankdata pointer. The trampoline preserves `r0-r3`, `r12`, `lr`, and CPSR flags before calling the C payload.
3. The payload opens SDMC and creates `/3ds` and `/3ds/Bank` when necessary.
4. It creates or opens `/3ds/Bank/bankdata.bin`, sets its length to `0xBB518`, writes the complete buffer with flush enabled, verifies the service result and byte count, and closes the file. A failed or short write truncates the file to zero bytes.
5. The trampoline restores CPU state, reproduces the overwritten `mov r5,#0`, and returns to `0x0025C994`.

A local file error does not change the result of the original online operation.

## Usage notes

- This Mover download patch is retained only for interested users to study or test. It is not part of the supported offline-patch workflow.
- Mover reaches this download only after compatible game software has been selected and the original program connects to the server.
- The output path is the same `/3ds/Bank/bankdata.bin` used by the Bank download patch. The two patches therefore share and overwrite one local file rather than maintaining separate copies.
- Mover downloads the Bank object during this server phase even when the selected game has no Pokemon eligible for transfer.
- In the normal official flow, a user who can run Mover already has bankdata on the server. Mover was obtained through the Bank download menu, and reaching that menu means Bank has already created and synchronized new bankdata even for a first-time Bank user. Mover consequently consumes an existing Bank object instead of creating the account's initial object.

The supported workflow uses the Bank download patch to obtain `bankdata.bin`, then uses the offline patches with Bank and Mover. It does not require the Mover download patch. This avoids ambiguity over which application last replaced the shared file.

## Source layout

- `main.s`: hook, trampoline, executable bounds, and `.importobj`.
- `download_patch.c`: directory creation and complete-file write.
- `Makefile`: devkitARM compile, armips injection and symbol export, and Flips IPS creation.
- `../../include/symbol.inc`: curated Mover, BankObject, Transfer Box, network, HTTP, and FS symbols.

## Build environment

Set the standard `DEVKITARM` environment variable to the devkitARM installation directory. Tool paths do not contain platform-specific executable suffixes. The defaults are `tools/armips/armips` and `tools/flips/flips`; place native executables at those paths or override `ARMIPS` and `IPS_TOOL`.

## Injection layout

| Item | Value |
|---|---|
| Original hook instruction | `0x0025C990 = E3A05000` |
| Trampoline | `0x0028D5F0` |
| Imported object | `0x0028D670–0x0028D894` |
| C entry | `0x0028D6CC` |
| Executable limit | `0x0028E000` |

A successful build writes the IPS directly to `mover/release/1-download_patch/luma/titles/00040000000C9C00/code.ips`. The modified full code image remains under `mover/build/1-download_patch/`.
