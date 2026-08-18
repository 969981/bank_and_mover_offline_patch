# Pokemon Bank Code Analysis

## Target and memory layout

- Title ID: `00040000000C9B00`
- Version: v6.8.0
- Image base: `0x00100000`
- Decompressed code SHA-256: `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`

| Region | Virtual range | Properties |
|---|---|---|
| `.text` | `0x00100000–0x00314000` | Read/execute; actual content ends at `0x00313910` |
| `.rodata` | `0x00314000–0x0036A000` | Read-only, non-executable |
| `.data` | `0x0036A000–0x003AC000` | Read/write |
| `.bss` | Starts at `0x003AC000`, length `0x4EE38` | Read/write, zero-initialized |
| Thread stack | Length `0x40000` | ExHeader setting |

The end of `.text` contains executable padding at `0x00313910–0x00314000`; the following `.rodata` region is non-executable.

## Main flow and function addresses

| Address | Function |
|---:|---|
| `0x002A5580` | Select the next state from the current flow result |
| `0x002A5A7C` | Factory for 30 state objects |
| `0x002AF1FC` | Network connection state update |
| `0x002AF460` | Account entitlement and remote metadata state |
| `0x002ACBDC` | Complete Bank file download state |
| `0x002AE568` | Initial remote Bank file creation state |
| `0x002B0270` | Optional reward delivery state |
| `0x002A7094` | Bank Box UI entry |
| `0x002B1CF8` | Save, commit, and rollback state machine |
| `0x002ABC24` | Return-to-title state |

```text
Validate selected game
  → ACT/NNID and network session
  → entitlement and remote metadata
  → feature menu
  → select Use Pokemon Bank and a game
  → download or create the complete Bank file
  → Bank Box UI
  → serialize, stage remotely, save the game, commit or roll back
  → title screen
```

## Network states

The connection between the title screen and feature menu initializes the control plane. It handles game validation, ACT/NNID, the network endpoint, the service session, account entitlement, remote metadata, and unfinished transaction state. It does not download the complete bankdata file.

The complete Bank file is downloaded after selecting Use Pokemon Bank and a game:

```text
0x002ACBDC BankDownloadState_Update
  → 0x002A2F68 BankRemote_RequestFile
  → 0x002D11B0 BankRemote_DownloadSuccessCallback
  → load the Bank object
  → 0x002A3144 BankRemote_QueryTransaction
  → completion state
```

The eleventh argument of `0x002D11B0` is the complete data pointer. It is held in `r7` and passed to vtable slot `+0x0C` at `0x002D1234`. Vtable slot `+0x10` supplies the file length.

`0x002ACBDC` substates:

| State | Function |
|---:|---|
| 0 | Create the remote job and callback context |
| 1 | Request the complete file |
| 2 | Wait for success or failure callback |
| 3/4 | Wait for the related UI dialog |
| 5 | Query the same remote transaction |
| 6 | Wait for the transaction query result |
| 7 | Wait for the local asynchronous save |
| 8/9 | Return success or failure |

The transfer stack combines a control-plane request with HPP/HTTP:

| Address | Function |
|---:|---|
| `0x00198A78` | Prepare and start an HTTP request |
| `0x00199570` | HTTP streaming send/receive worker |
| `0x001C1EF8` | Build a multipart file stream containing `name="file"` |
| `0x001C22F0` | Emit multipart prefix, file body, and suffix |
| `0x00245414` | Send an HTTPC chunk |
| `0x002454A4` | Finish the POST body |
| `0x002454C4` | Receive the HTTP response |
| `0x002CC878` | Prepare BankObject GET |
| `0x002CC988` | Validate response `Content-Length` |
| `0x001B23E8` | Initialize an HPP POST job |
| `0x001B2544` | Process HPP result, redirects, and retries |
| `0x001B2820` | Rebuild a retry request |

The four HPP resources are `CACERT_PUBLIC_CA_5.der` through `_8.der`, not bankdata fragments. The HTTP layer follows up to five `307` redirects, retries `409/500`, and limits cached error responses to `0x2800` bytes.

## BankObject and bankdata

The Bank object vtable is `0x003626FC`. The runtime object header is eight bytes; the file corresponds to `obj_bank + 8`.

| Vtable slot | Address | Function |
|---:|---:|---|
| `+0x08` | `0x002CB870` | Serialize the body at object `+8` |
| `+0x0C` | `0x0023650C` | Load input into object `+8` |
| `+0x10` | `0x002CB864` | Return `0xBB518` |
| `+0x14` | `0x00116294` | Initialize the current format |
| `+0x18` | `0x002BA490` | Load and upgrade the `0xACA48` legacy format |
| `+0x1C` | `0x002CB84C` | Check `u16(data+0x15C)==2` |

Runtime object chain:

```text
slot_address   = *(u32*)0x002ACEEC     ; 0x003AB938
root           = *(u32*)slot_address
manager        = *(u32*)(root + 0x1C)
obj_bank       = *(u32*)(manager + 0xCC)
bank_file_data = obj_bank + 8
```

The object must satisfy `*(u32*)obj_bank == 0x003626FC`. The disk file is exactly `0xBB518` bytes. Minimum load checks are `u16(data+0x15C)==2` and `u16(data+0x15E)==100`.

### bankdata layout

| File offset | Length | Content |
|---:|---:|---|
| `0x000000` | `0x17C` | Header, names, version, and state fields |
| `0x00017C` | `100 × 0x1B56` | 100 Bank Boxes, each with 30 `0xE8` slots and box metadata |
| `0x0AAF14` | `30 × 0xE8` | 30 Transfer Box slots |
| `0x0ACA44` | `3000` | Per-slot Bank format tags |
| `0x0AD5FC` | `30` | Per-slot Transfer Box tags |
| `0x0AD61A` | `2` | Reserved/alignment |
| `0x0AD61C` | `8 × 0x44` | Source-game summaries |
| `0x0AD83C` | `0x7260` | Pokedex-like aggregate data |
| `0x0B4A9C` | `4` | Deposit/withdrawal counters |
| `0x0B4AA0` | `3000` | Source software IDs for Bank slots |
| `0x0B5658` | `3000 × 8` | Update timestamps for Bank slots |
| `0x0BB418` | `0x100` | Tail flags and reserved bytes |

Header fields include a 64-bit identity-bound value at `+0x000000`, ten fixed UTF-16 name buffers at `+0x000008`, date fields at `+0x000160`, remote content identifiers at `+0x000168/+0x00016C`, counters at `+0x000170/+0x000174`, and four flag bytes at `+0x000178`.

The current-format load and serialize methods perform fixed-size copies. No client-side bankdata checksum, MAC, compression, or decryption routine was identified in this object layer. Server-side upload rules remain separate.

## Save and upload

```text
0x002B2320 BankSave_SerializeAndStage
  → 0x002B2490 completes 0xBB518 serialization
  → 0x002B24A0 / 0x002A2504 stages the remote update
  → game and local save operations
  → 0x001D5D74 commits
  → 0x001D5C28 rolls back on failure
```

The 32-byte transaction descriptor belongs to remote stage/commit/rollback control and is not part of bankdata. Faking one HTTPC return value is insufficient because the outer state machine still waits for HTTP status, response body, control-plane result, and asynchronous completion flags.
