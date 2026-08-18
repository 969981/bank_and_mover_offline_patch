# Pokemon Bank Offline Patch Design

## Scope

The offline patch loads and saves `/3ds/Bank/bankdata.bin` without starting the Bank service transaction. It bypasses only the business states that require the retired service; it does not report a false global network state to unrelated system components.

## Local load

The complete download state is replaced at its state-1 request boundary. The replacement:

1. Opens `/3ds/Bank/bankdata.bin` and reads exactly `0xBB518` bytes.
2. Rejects a short read, a format version other than `2`, or a box count other than `100`.
3. Passes the buffer through the original current-format BankObject loader.
4. Reproduces the original callback result and asynchronous completion flags.
5. Enters the existing final-success branch without issuing the later remote transaction query.

The 32-byte remote transaction descriptor is not part of bankdata and remains unused in an offline session.

## Transactional local save

| Proposed hook boundary | Replacement behavior |
|---:|---|
| `0x002B24A0` | Write the complete serialized object to `bankdata.tmp`; verify the file length and actual byte count |
| `0x002B20AC` | After the game save succeeds, rotate the previous file to a recoverable backup and replace `bankdata.bin` with the temporary file |
| `0x002B20E8` | After the game save fails, discard the temporary file and retain the previous `bankdata.bin` |

Each replacement must publish the result through the same completion fields consumed by the original outer state machine. The game save and other local title-save operations remain in their original order.

The implementation must create `/3ds/Bank` when absent, treat short writes as failure, close handles on every branch, and never overwrite the last valid file before the game save succeeds.

## Known limitations

- Fully offline edits may retain an old or zero per-slot 64-bit update time until the timestamp producer is identified.
- Local retry-state cleanup has not yet been reduced to a proven minimal set.
- Load bypass, local save, and their shared state edits must be built as one IPS so overlapping instruction sites cannot overwrite each other.
