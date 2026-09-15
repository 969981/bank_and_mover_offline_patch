# Step 2: offline patch

## Purpose and files

This patch redirects Pokemon Bank's remote Bank-data operations to one local
file while retaining the stock game-selection, Bank Box, and game-save logic.

| File | Purpose |
|---|---|
| `sd:/3ds/Bank/bankdata.bin` | Current complete Bank file (`0xBB518` bytes) |
| `sd:/3ds/Bank/bankdata.tmp` | Fully written candidate used during saving |
| `sd:/3ds/Bank/bankdata.bak` | Previous complete file retained during commit |
| `sd:/3ds/Bank/bankdata.bin.break` | Byte-for-byte copy of an unusable primary file |
| `sd:/3ds/Bank/bankdata.bak.break` | Byte-for-byte copy of an unusable backup file |

The patch creates `sd:/3ds` and `sd:/3ds/Bank` when a local file must be
created. An invalid or missing `bankdata.bin` is restored from a readable,
valid `bankdata.bak`. If neither file is recoverable, every existing invalid
file is copied to its corresponding `.break` path before stock first-use
creation runs. Missing files do not produce placeholder `.break` files.

## Overall route

```text
Title / account checks
        │
        ▼
"Connecting..." ── network availability forced locally
        │             no remote connection job
        ▼
Inspect bankdata.bin header and exact length
        ├── valid ──────────────► existing-record mode 4
        └── missing/invalid
                  │
                  ▼
             Inspect bankdata.bak
                  ├── valid ────► read all 0xBB518 bytes
                  │                copy to bankdata.bin; preserve .bak
                  │                no .break files
                  │                └────────► existing-record mode 4
                  └── missing/invalid
                            │
                            ▼
                 Copy each existing invalid file to .break
                            ├── initial failure ─► retry up to 3 times per file
                            └── copied / all 4 attempts failed / both absent
                                           └──► first-use mode 5
                                      │
                                      ▼
Refresh runtime offline ticket to console time + 999 days
                │
                ▼
Stock first-use decision
        ├── mode 4 ──────────────► feature menu
        └── mode 5 ─► stock first-use messages
                         │
                         ▼
                    skip remote record-ID substates 4-5
                         │
                         ▼
                    stock empty-object initialization
                    (localized boxes and creation date)
                         │
                         ▼
                    write bankdata.bin directly
                                                    │
                                                    ▼
                                               feature menu
```

The normal startup record check reads only the four-byte format header at file
offset `0x15C`. Recovery additionally reads and validates the complete backup
before copying it. A valid primary or recoverable backup never creates a
`.break` file. If no valid recovery source exists, each invalid file that is
actually present is copied in full; first-use creation proceeds only after all
copies have either succeeded or exhausted the initial attempt plus three retries. Copy failure does not
remove the original invalid file and does not block first use. If both files
are absent, first use begins directly.
The stock state 9 decision is preserved. When no valid primary or backup exists,
the application therefore uses its own first-use setup
to obtain console/account values, initialize 100 localized Bank Boxes, and set
the real creation date. The remote record-ID acquisition substates are skipped;
the native empty-object initializer still runs. The final remote creation is
replaced with a checked direct write to `bankdata.bin`. A failed first write
removes its partial file. The normal save path continues to use `.tmp` and
maintain `.bak`.

The console clock supplies the current-time field used by the native local
mileage calculation. The 999-day offline entitlement is stored separately and
is never used as mileage time. Existing identity fields and the creation date
stored in `bankdata.bin` are not rewritten by this patch.

## Loading and using the Bank

```text
Feature menu: Use Pokemon Bank
        │
        ▼
Stock game selection and game-software checks
        │
        ▼
"Connecting to the local offline Bank data..." (at least 2 seconds)
        │
        ▼
Close the stock rotating wait UI and its looping sound
        │
        ▼
Read exactly 0xBB518 bytes from bankdata.bin
        ├── read/header failure ─► error
        └── valid ───────────────► rebuild flow metadata
                                      │
                                      ▼
                         resume stock local substates 6-10
                                      │
                                      ▼
                         skip reward-server states
                                      │
                                      ▼
                              stock Bank Box UI
```

The complete local file is loaded only after a game has been selected. The
patch skips the remote request portion of the shared Bank-data synchronization
state, then resumes its native metadata-copy and selected-game callbacks. Box
viewing, Pokemon movement, validation, and game interaction remain stock code.

The former Pokemon HOME menu entry is named **Choose Language** and is routed to
the stock language-selection flow. It does not enter the HOME Bank-data path.
After a language change, the return-to-title variant selects an appended blank
message so the newly selected font does not draw the previous language's text.
Before returning to the title screen, the patch copies the pending language and
Japanese Kanji setting into the stock persistent-settings object, starts native
save mode 0, and waits for it to complete. The selected language therefore
survives an immediate restart without requiring another title-screen action.

## Saving, commit, and rollback

```text
Stock full Bank serialization (0xBB518 bytes)
        │
        ▼
Write bankdata.tmp + set size + flush + verify bytes written
        ├── failure ─────────────► save failure; keep bankdata.bin
        └── success
              │
              ▼
Save-progress screen remains visible for at least 2 seconds
              │
              ▼
Stock cartridge / digital-game save
        ├── failed ─► delete bankdata.tmp ─► keep bin and bak
        └── succeeded
              │
              ▼
Delete old bak ─► rename bin to bak ─► rename tmp to bin
                                      ├── success ─► disconnect
                                      └── failure ─► restore bak when possible
```

The local staging operation is synchronous, but its completion enters a
nonblocking two-second state-machine delay. Rendering continues and the file is
not written repeatedly. Commit occurs only after the stock game-save result is
successful. Delete, rename, close, size, write-length, restoration, and rollback
results are checked.

Ending Bank use without saving does not install a new `bankdata.bin`.

## Display and disconnect behavior

LayeredFS resources cover all ten supported languages:

- The initial Internet message becomes a generic **Connecting...** prompt.
- The post-selection service message identifies the local offline Bank data.
- When that local connection delay completes, the patch explicitly closes the
  stock rotating wait UI so its looping sound cannot continue into the Bank Box.
- The save message identifies the local offline file instead of a server.
- Normal state 20 exits display **Disconnecting...** and complete their local
  first phase after 1.5 seconds without allocating a remote disconnect job.
- The language-change state 21 uses the blank message described above and
  completes the native local-settings save before returning to the title screen.

Test with a backup in an emulator before using the patch on hardware.

## External open-source references

- [devkitPro/libctru FS interface declarations](https://github.com/devkitPro/libctru/blob/master/libctru/include/3ds/services/fs.h)
  and [FS service implementation](https://github.com/devkitPro/libctru/blob/master/libctru/source/services/fs.c)
  were used to verify the public 3DS FSUSER/FSFILE command interfaces and result
  handling used by the local-file layer.

The current Bank binary is the authority for all application addresses, state
transitions, object layouts, file offsets, and patch sites. Those conclusions
were independently derived and verified for this version; they were not taken
from the external FS references.
