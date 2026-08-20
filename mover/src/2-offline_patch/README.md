# Step 2: offline patch

## Purpose and prerequisites

This patch makes Poke Mover use the same local Bank file as Pokemon Bank:
`sd:/3ds/Bank/bankdata.bin`. It retains the stock source-game selection,
cartridge reading, Pokemon conversion, confirmation, source-game save, and
disconnect flow.

A valid current-format `bankdata.bin` of exactly `0xBB518` bytes must already
exist. Poke Mover does not create a new Bank file. In the stock distribution and
usage path, a user reaches Poke Mover through Pokemon Bank only after the Bank
account and initial Bank data have been created.

The local Transfer Box must be empty before starting a new transfer. Existing
Transfer Box contents are never overwritten.

## Overall route

```text
Stock source-game selection
        │
        ▼
"Connecting..." ── network availability forced locally
        │             no remote connection job
        ▼
Refresh runtime offline ticket to console time + 999 days
        │
        ▼
"Connecting to the local offline Bank data..." (at least 2 seconds)
        │
        ▼
Stock cartridge read, filtering, and Pokemon conversion
        │
        ├── Gen 5 legality request ──────► skip to local continuation
        └── Gen 1/2 legality request ────► skip to local continuation
                                              │
                                              ▼
                                complete remote-check state locally
                                              │
                                              ▼
                           load bankdata.bin and merge candidates
                                ├── invalid/missing ─► error
                                ├── Transfer Box busy ► stock message 5; preserve file
                                └── empty box ───────► stock confirmation UI
```

The native candidate-conversion state remains responsible for reading the
source game, filtering records, and constructing transfer candidates. Only its
two embedded server legality requests are bypassed. These two call sites were
verified against the current binary and cross-checked with the public precedent
cited below.

Before loading `bankdata.bin`, the patch preserves the candidates in native
Transfer Slot objects. It then reads and validates the complete local Bank file.
If the loaded Transfer Box is empty, the candidates are restored with the
stock slot-write operations, which update both each `0xE8`-byte record and its
parallel tag. The patch does not copy raw slot bytes over existing data.

Existing account identity fields remain unchanged. The offline ticket expiry is
computed in runtime state from the 3DS system clock plus 999 days.

## Transfer save transaction

```text
User confirms the transfer
        │
        ▼
Stock full Bank serialization (0xBB518 bytes)
        │
        ▼
Write bankdata.tmp + set size + flush + verify bytes written
        ├── failure ─────────────► abort; preserve bankdata.bin
        └── success
              │
              ▼
Save-progress screen remains visible for at least 2 seconds
              │
              ▼
Stock source-cartridge save
        ├── failed ─► delete bankdata.tmp ─► keep bin and bak
        └── succeeded
              │
              ▼
Delete old bak ─► rename bin to bak ─► rename tmp to bin
                                      ├── success ─► stock disconnect route
                                      └── failure ─► restore bak when possible
```

Staging, commit, and rollback replace the corresponding remote transactions.
After the synchronous stage write, a nonblocking state-machine delay keeps the
save screen visible for at least two seconds without repeating the write.
Commit occurs only after the original source-game save succeeds. Delete, rename,
close, size, write-length, restoration, and rollback results are checked.

If there are no transferable Pokemon, or if the user cancels, the stock
no-transfer route is retained while its final server transaction is completed
locally. It then enters the stock disconnect route.

## Display and timing behavior

LayeredFS resources cover all ten supported languages:

- The initial Internet message becomes a generic **Connecting...** prompt.
- The local Bank-data message is shown for at least 2 seconds before native
  cartridge reading and conversion begin.
- The save message identifies the local offline Bank data instead of a server.
  It remains visible for at least 2 seconds after the complete local stage write.
- The disconnect text is generic. Its existing 1.5-second local first phase is
  unchanged and no remote disconnect job is allocated.

The stock functions still create and destroy the waiting UI, spinner, and
rhythmic sound. Offline updates only report completion through the original
state object; they do not hide the UI or stop sound early, so the native state
exit path remains the single cleanup owner.

Test in an emulator and back up `bankdata.bin` before using the patch on
hardware.

## External open-source references

- [zaksabeast/Transporter-Offline-Patch](https://github.com/zaksabeast/Transporter-Offline-Patch)
  provided the public precedent for replacing Poke Mover's network-facing
  states, including the two legality-request bypass points in the native
  candidate-conversion state.
- [Transporter-PKSM-Bank-Patch state-machine notes](https://github.com/zaksabeast/Transporter-PKSM-Bank-Patch/blob/master/TRANSPORTER_DOCS.md)
  were used to cross-check the high-level state order.
- [devkitPro/libctru FS interface declarations](https://github.com/devkitPro/libctru/blob/master/libctru/include/3ds/services/fs.h)
  and [FS service implementation](https://github.com/devkitPro/libctru/blob/master/libctru/source/services/fs.c)
  were used to verify the public FSUSER/FSFILE interfaces and result handling
  used by the local-file layer.

The current Poke Mover binary is the authority for all addresses, transitions,
object layouts, file offsets, and patch sites. They were independently verified
for this version rather than copied from the external projects.
