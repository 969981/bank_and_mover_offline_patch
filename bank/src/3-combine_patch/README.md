# Step 3: combined offline and download patch

This project builds one Pokemon Bank v1.5 patch with two runtime modes. It
does not combine the binary output of the earlier patches: it selects the
appropriate behavior at every shared network and save hook.

## Mode selection

The patch defaults to offline mode. Press the physical **R** button on the
title screen to switch between offline and download mode; each press updates
the mode shown near the bottom of the title screen. Press **A**, **START**, or touch the
lower screen to enter Bank. The currently displayed mode is latched on that
title-exit frame and cannot change during the Bank session.

```text
Title screen (default: Offline)
        |
        +-- press R ---------------------------> Download shown
        |
        +-- press R again ----------------------> Offline shown
        |
        +-- A / START / touch -----------------> latch shown mode and enter
```

The stock version label remains unchanged. The upper screen's original
HOME-return help stays intact, and a localized current-mode / press-R hint is
appended on the following line in the same wide text pane. The
feature menu's upper screen keeps the stock greeting; Japanese, English, and
Korean use a one-line equivalent where the original occupied multiple lines.
The selected mode follows it with a localized "Current Mode:" prefix. Both are
supplied for all ten shipped language archives. Only the
first entry on the lower-screen feature menu is replaced by the mode-specific
label.

## Runtime message selection

The combined archive keeps the stock network, Bank-connection, save, and
disconnect entries unchanged. Mode-specific text is stored in appended entries
and selected at the state that owns the message.

| UI state | Offline mode | Download mode |
|---|---|---|
| Initial connection | Local offline connection message | Stock Internet-connection message |
| Connection after game selection | Local Bank-data connection message | Downloading from the server to `sd:/3ds/Bank/bankdata.bin` |
| Save | Local offline-file save message | Stock server-save message if this normally unreachable path is entered |
| Normal disconnect | Local disconnect message | Stock disconnect message |
| Disconnect after a successful capture | Not used | Download-complete message, then return to title |
| Disconnect after language selection | Blank message | Blank message |

The waiting screen, spinner, and rhythmic sound after game selection remain
owned by the stock state initializer, update, and destructor. The patch does
not hide or stop them early; after local work completes, the native exit path
performs cleanup.

## Offline mode

Offline mode keeps the stock game-selection, Bank Box, and game-save logic,
but replaces the remote Bank-data connection with the checked local-file flow
from Step 2.

```text
Select Use Pokemon Bank
        |
        v
Stock game detection and game selection
        |
        v
Read sd:/3ds/Bank/bankdata.bin
        |
        +-- valid -----------------------------> stock local metadata and Box flow
        |
        +-- missing or invalid ----------------> backup recovery or stock first-use creation
```

The local primary, staging, backup, and broken-file handling is documented in
[the Step 2 README](../2-offline_patch/README.md). The offline local data is
separate from data on the official service.

## Download mode

Download mode retains the stock account, connection, remote-record creation,
Bank-data download, and native disconnect paths. Both modes deliberately finish
the separate optional-reward state locally, which avoids the points/reward UI
while supplying its downstream runtime fields. This mode is intended to refresh
the local data file without entering the normal Bank Box session.

Where a combined hook overlaps stock allocation setup, its download-mode branch
replays every overwritten allocator-context, allocation, and root-load
instruction before continuing after the original sequence. The official
connection, first-use creation, and disconnect jobs therefore remain native.

```text
Select Download Bank Data
        |
        v
Stock game detection, game selection, and server download
        |
        v
Successful ordinary-Bank download callback
        |
        v
Checked local stage and commit to sd:/3ds/Bank/bankdata.bin
        |
        +-- local capture succeeded -----------> skip points, Box, and save UI
        |                                        -> stock no-save disconnect
        |
        +-- local capture failed -------------> stock callback outcome is unchanged
```

Only the ordinary Bank download route writes the local file. The HOME route
does not use the capture callback, so it cannot overwrite local Bank data.
When an ordinary capture succeeds, the completion message reports that the
data was downloaded to the SD card and that Bank is returning to the title
screen. The next normal start is offline mode.

## Shared feature-menu behavior

The feature menu is intentionally small and predictable in both modes:

| Entry | Offline mode | Download mode |
|---|---|---|
| First entry | Use Pokemon Bank | Download Bank Data |
| About Pokemon Bank | Stock information screen | Stock information screen |
| Support | Disabled; returns to the feature menu | Disabled; returns to the feature menu |
| Poke Mover/eShop | Disabled; returns to the feature menu | Disabled; returns to the feature menu |
| Pokemon HOME | Stock language-selection flow | Stock language-selection flow |
| Back | Stock behavior | Stock behavior |

The HOME entry is redirected before the HOME transfer state begins. It opens
the existing language-selection flow instead, and does not trigger the
ordinary Bank-data capture logic.

## Source layout

| File | Role |
|---|---|
| `main.s` | Mode latch, dynamic hook dispatch, callback capture, and menu routing |
| `combine_patch.c` | Shared checked local-file implementation |
| `patch_messages.py` | Rebuilds the localized LayeredFS message archives |
| `verify_patch.py` | Checks code ranges, branch destinations, IPS framing, and all localized messages |
| `Makefile` | Compiles, injects, creates IPS, and writes the Luma release tree |

## Build

Set `DEVKITARM` to a devkitARM installation and place the extracted base code
at `bank/00040000000C9B00.code`. The extracted Bank RomFS must be available at
the default `ROMFS_SOURCE` path, or provide that Make variable explicitly.
The supported decompressed code image has SHA-256
`2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`;
the build verifier rejects a different base image.

```text
make -C bank/src/3-combine_patch all
```

The complete Luma tree is generated at:

```text
bank/release/3-combine_patch/luma/titles/00040000000C9B00/
  code.ips
  romfs/
```

Copy the generated `luma` directory to the SD card and enable Luma game
patching. Test with a backed-up SD card and a disposable save before using it
on hardware.

`all` also runs `verify_patch.py`. It checks that the local implementation fits
inside the intentionally bypassed optional-reward state, that every patched ARM
hook has its intended target, condition code, and overwritten padding, that the
release IPS reproduces the patched code image byte-for-byte, and that all ten
generated message archives retain the stock title and upper-menu greeting lines
required by the UI. It also compares the replayed native allocation sequences
against the supported base image.

## External open-source references

- [devkitPro/libctru FS declarations](https://github.com/devkitPro/libctru/blob/master/libctru/include/3ds/services/fs.h)
  were used to check the public FSUSER/FSFILE interfaces and result handling
  used by the local-file layer.
- [Luma3DS loader patcher](https://github.com/LumaTeam/Luma3DS/blob/master/sysmodules/loader/source/patcher.c)
  was used to check the title-specific `code.ips` and LayeredFS directory
  layout.
- [pkNX TextFile](https://github.com/kwsch/pkNX/blob/master/pkNX.Structures/Text/TextFile.cs)
  was used to check the public message-file encoding and line-table format
  used by the resource rebuild tool.

The current Bank binary is the authority for application addresses, state
transitions, object layouts, file offsets, and patch sites. The external
references above are only used for public platform and file-format interfaces.
