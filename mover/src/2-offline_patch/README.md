# Poke Mover Offline Patch Design

## Scope

The offline patch retains the original cartridge scan, filtering, conversion, and Transfer Box normalization while replacing service-dependent eligibility, download, stage, commit, and rollback states with local equivalents.

## Business-state bypass

| Proposed patch site | Intended transition |
|---:|---|
| `0x00242D10` | Skip `CONNECT_ONLINE` after game selection |
| `0x00242D28` | Continue with transfer eligibility processing |
| `0x00248CDC` | Skip creation of the remote eligibility object |
| `0x00248D58` | Enter local completion handling |
| `0x00245728` | Skip the Gen 5 remote check |
| `0x002460B8` | Skip the Gen 1/2 remote check |
| `0x002488A0`, `0x002483CC` | Enter the existing initialization-success branches |
| `0x0024A150` | Skip remote transaction preparation |
| `0x0024A3D8` | Enter complete-file local commit handling |

These are business-state transitions, not a replacement for all HTTPC results.

## Local load

The replacement takes control of the complete state-1 branch at `0x00248D3C`, reads and validates exactly `0xBB518` bytes from `/3ds/Bank/bankdata.bin`, and writes the final state that the original asynchronous callback would have selected.

It reuses the object-loading semantics of `0x0025C978`: preserve the 30 cartridge candidates, load the complete BankObject, and restore those candidates when the file's Transfer Box is empty. A Transfer Box update must keep each `0xE8` record synchronized with its one-byte tag.

## Transactional local save

| Proposed hook boundary | Replacement behavior |
|---:|---|
| `0x0024A240` | Write the complete serialized object to `bankdata.tmp` and verify the exact byte count |
| `0x0024A3E4` | After the game save succeeds, rotate the previous file to a recoverable backup and replace `bankdata.bin` |
| `0x0024A420` | After the game save fails, discard the temporary file and retain the previous `bankdata.bin` |

The replacement branches reproduce the original asynchronous completion fields. Mover and Bank continue to share `/3ds/Bank/bankdata.bin`; no Mover-specific persistent format is introduced.

The implementation must create `/3ds/Bank` when absent, close every FS handle, reject short reads and writes, and emit all overlapping state changes in one IPS.

## References

The high-level state-machine and offline-bypass approach was cross-checked against these public projects:

- [Transporter-PKSM-Bank-Patch](https://github.com/zaksabeast/Transporter-PKSM-Bank-Patch) and its [Transporter documentation](https://github.com/zaksabeast/Transporter-PKSM-Bank-Patch/blob/master/TRANSPORTER_DOCS.md), by zaksabeast: state-machine structure and patch-oriented control-flow concepts.
- [Transporter-Offline-Patch](https://github.com/zaksabeast/Transporter-Offline-Patch), by zaksabeast: the public offline-bypass design and its compatibility context.

These references apply to the overall approach only. The addresses and version-specific behavior in this document were derived from and cross-checked against the current `00040000000C9C00.code`; they must not be assumed to apply to other versions. No source code from the referenced projects is included in this patch directory.

## Known limitations

- The minimal local retry state that must be cleared is not yet proven.
- Fully offline timestamp behavior remains tied to the unidentified per-slot timestamp producer.
