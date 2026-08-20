# Step 3: combined original and offline patch

## Mode selection

The title screen starts in **Offline Mode**. Press the `R` button on
the title screen to switch between **Offline Mode** and **Original Mode**. The
mode line is displayed below the HOME-menu help text, uses the same button glyph
as the Bank patch, and updates immediately.

Starting the software with A, START, or the touch screen latches the displayed
mode for that session. `R` no longer changes mode after leaving the title.

```text
Title screen
   ├── R ─► Offline Mode ◄────► Original Mode
   └── Start/touch
          │ latch selected mode
          ├── Offline ─► local bankdata.bin and offline transaction hooks
          └── Original ─► untouched official network and server flow
```

## Isolation between modes

Every code site used by the Step 2 offline patch first reads the latched session
flag. Offline Mode enters the established local implementation. Original Mode
replays the exact overwritten instruction or branches to the original function
body, including network availability, ticket, legality checks, Bank download,
transfer staging, commit, rollback, and disconnect.

Stock message entries remain unchanged. Six entries are appended for the two
title variants and the four offline connection/save messages; runtime hooks
select the appended messages only in Offline Mode. All ten languages are built
as LayeredFS resources.

Offline Mode has the same prerequisite and transaction guarantees as Step 2:
a valid `sd:/3ds/Bank/bankdata.bin` must already exist, and the Transfer Box
must be empty. Poke Mover does not create a new Bank file.

## Build output

Run `make -C src/3-combine_patch` from the `mover` directory. The Luma package
is generated under:

```text
release/3-combine_patch/luma/titles/00040000000C9C00/
├── code.ips
└── romfs/a/...
```

The build verifies the supported base-code hash, code-cave limits, hook targets,
IPS reconstruction, and that every original localized message remains intact.

## External open-source references

The offline half retains the independently verified Step 2 implementation and
its references to
[zaksabeast/Transporter-Offline-Patch](https://github.com/zaksabeast/Transporter-Offline-Patch),
[Transporter-PKSM-Bank-Patch state-machine notes](https://github.com/zaksabeast/Transporter-PKSM-Bank-Patch/blob/master/TRANSPORTER_DOCS.md),
and the [devkitPro/libctru FS interfaces](https://github.com/devkitPro/libctru/blob/master/libctru/include/3ds/services/fs.h).
All addresses and original-mode continuations are verified against the current
Poke Mover binary.
