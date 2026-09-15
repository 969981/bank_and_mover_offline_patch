# Combined original and offline patch

This is the maintained Poke Mover v5.5.0 patch for base title
`00040000000C9C00`. It combines the verified standalone offline behavior with
an exact runtime path back to the original application.

Poke Mover has no download mode. It neither creates a new local Bank nor
downloads the supported local file. Use Pokemon Bank's combined patch in
Download Mode to obtain `sd:/3ds/Bank/bankdata.bin`, or let Bank's Offline Mode
create it during first-time initialization, then use Poke Mover in Offline
Mode. The discontinued standalone Mover download experiment is not part of
this workflow.

The upload patch has also been permanently discontinued. Offline transfers are
committed only to the local Bank file and are never uploaded by this project.

## Mode selection

The title screen starts in **Offline Mode**. Press the physical **R** button to
switch between **Offline Mode** and **Original Mode**. The mode line is shown
below the HOME-menu help text, uses the same button glyph as the Bank patch,
and updates immediately.

Press **A**, **START**, or touch the lower screen to latch the displayed mode
for the session. R no longer changes mode after leaving the title screen.

```text
Title screen (default: Offline)
        │
        ├── R ───────────────► Original
        ├── R again ─────────► Offline
        └── A / START / touch
                  │ latch displayed mode
                  ├── Offline ─► local bankdata.bin and local transactions
                  └── Original ─► official network and server flow
```

## Strict separation between modes

Every hook inherited from the offline patch reads the latched session flag.
Offline Mode enters the local implementation. Original Mode replays the exact
overwritten instruction or resumes the original function body for:

- network availability and connection jobs;
- ticket handling;
- Gen 5 and Gen 1/2 legality requests;
- server Bank-data download;
- transfer eligibility and candidate states;
- remote staging, commit, rollback, and disconnect.

Original Mode therefore does not read, write, create, rename, or delete any
file under `sd:/3ds/Bank/`. It keeps the original server flow and original
messages.

Stock message entries remain unchanged. The LayeredFS archive only appends two
title variants and four offline connection/save messages; runtime hooks select
those entries only in Offline Mode. All ten shipped languages are rebuilt and
validated.

## Offline prerequisites and local file

Offline Mode uses the same file as Pokemon Bank:

```text
sd:/3ds/Bank/bankdata.bin
```

It must already be a valid current-format Bank object of exactly `0xBB518`
bytes. Poke Mover does not perform Bank's missing-file recovery or first-use
creation. A missing, unreadable, incorrectly sized, or invalid file follows the
error path.

The local Transfer Box must be empty before a new transfer. Existing Transfer
Box contents are never overwritten. Back up `bankdata.bin` before testing on
hardware.

## Offline transfer route

```text
Stock source-game selection
        │
        ▼
Generic Connecting message
        │
        ├── report network available locally
        └── allocate no remote connection job
        │
        ▼
Set runtime offline ticket to console time + 999 days
        │
        ▼
Connect to local offline Bank data (at least 2 seconds)
        │
        ▼
Stock cartridge read, filtering, and Pokemon conversion
        │
        ├── Gen 5 legality request ──────► verified local continuation
        └── Gen 1/2 legality request ────► verified local continuation
                                              │
                                              ▼
                               Complete remote-check state locally
                                              │
                                              ▼
                         Load and validate complete bankdata.bin
                                ├── invalid/missing ─► error
                                ├── Transfer Box busy ► stock message 5;
                                │                       preserve file
                                └── Transfer Box empty ► stock confirmation UI
```

The native candidate-conversion state remains responsible for reading the
source game, filtering records, and constructing transfer candidates. Only its
two embedded server legality requests are bypassed in Offline Mode.

Before loading `bankdata.bin`, the patch preserves candidates in native
Transfer Slot objects. After validating the complete local Bank, it restores
the candidates only when the Transfer Box is empty. Stock slot-write operations
update each `0xE8`-byte record and its parallel tag; the patch does not copy raw
slot bytes over existing data. Existing account identity fields are preserved.

## Offline save transaction

```text
User confirms the transfer
        │
        ▼
Stock full Bank serialization (0xBB518 bytes)
        │
        ▼
Write bankdata.tmp + set size + flush + verify bytes written
        ├── failure ─► abort; preserve bankdata.bin
        └── success
              │
              ▼
Keep save-progress screen visible for at least 2 seconds
        │
        ▼
Stock source-game save
        ├── failure ─► delete tmp; retain bin and bak
        └── success
              │
              ▼
Delete old bak ─► rename bin to bak ─► rename tmp to bin
        ├── success ─► stock disconnect route
        └── failure ─► restore bak where possible
```

Local staging, commit, and rollback replace only their remote counterparts.
The staging write is synchronous, followed by a nonblocking two-second
state-machine delay; rendering continues and the file is not written twice.
Commit occurs only after the original source-game save succeeds. File close,
size, write length, delete, rename, restoration, and rollback results are
checked.

When there are no transferable Pokemon or the user cancels, the stock
no-transfer route is retained. Its final remote transaction is completed
locally before entering the stock disconnect route.

## Offline display and timing

- The initial Internet line becomes a generic **Connecting...** message.
- The local Bank-data connection message remains visible for at least two
  seconds before stock cartridge reading and conversion proceed.
- The save message identifies local offline Bank data and remains visible for
  at least two seconds after the complete staging write.
- The disconnect line is generic. Its existing 1.5-second local first phase is
  retained, and no remote disconnect job is allocated.

The stock state functions remain the sole owner of the waiting UI, spinner,
and rhythmic sound. Offline updates report completion through the original
state object; the native state exit path performs cleanup.

## Source layout

| File | Role |
|---|---|
| `main.s` | Title-mode latch and mode dispatch for every offline hook |
| `patch_messages.py` | Appends and validates title/offline text in all ten language archives |
| `message_archive.py` | Self-contained GARC and encrypted message-file codec |
| `verify_patch.py` | Verifies the base hash, code regions, hooks, native replay, IPS reconstruction, and resources |
| `Makefile` | Compiles the shared offline implementation, injects code, creates IPS, rebuilds messages, and writes the release tree |

## Build and installation

Set `DEVKITARM`, then place the user-dumped inputs at
`mover/rom/exefs/00040000000C9C00.dec.code` and `mover/rom/romfs/`. Only
`mover/rom/.gitkeep` is tracked; the code image and RomFS are deliberately
ignored and must be extracted from the user's own copy. `ROMFS_SOURCE` may
still be overridden explicitly. Python 3 is required for the message rebuild.

```sh
make -C mover/src/3-combine_patch all
```

The complete package is generated at:

```text
mover/release/3-combine_patch/luma/titles/00040000000C9C00/
├── code.ips
└── romfs/
```

Copy the generated `luma` directory to the SD card and enable Luma game
patching. The verifier checks the supported base-code hash, executable-region
limits, each hook and original-mode continuation, IPS byte-for-byte
reconstruction, and preservation of every original localized message.

## External open-source references

- [zaksabeast/Transporter-Offline-Patch](https://github.com/zaksabeast/Transporter-Offline-Patch)
  provided a public precedent for replacing Poke Mover network-facing states,
  including the two legality-request bypass locations.
- [Transporter-PKSM-Bank-Patch state-machine notes](https://github.com/zaksabeast/Transporter-PKSM-Bank-Patch/blob/master/TRANSPORTER_DOCS.md)
  were used to cross-check the high-level state order.
- [devkitPro/libctru FS declarations](https://github.com/devkitPro/libctru/blob/master/libctru/include/3ds/services/fs.h)
  and [implementation](https://github.com/devkitPro/libctru/blob/master/libctru/source/services/fs.c)
  were used to verify the public FSUSER/FSFILE interfaces and result handling.

The current Poke Mover binary remains authoritative for addresses, state
transitions, object layouts, file offsets, patch sites, and every Original Mode
continuation. External projects were used only as public cross-checks.
