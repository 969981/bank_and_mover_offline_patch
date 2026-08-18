# Pokemon Bank Upload Patch Design

## Scope

The upload patch returns an offline-edited local file to the service without reusing stale session control data.

## Online re-upload sequence

1. Complete normal online authentication and download the latest server file as `remote`.
2. Obtain the fresh 32-byte transaction descriptor created for the current session; never copy it from `bankdata.bin` or a previous session.
3. Compare the previously synchronized `base`, the offline-edited `local`, and the newly downloaded `remote` at slot granularity.
4. Apply non-conflicting local slot changes to `remote` while retaining current remote identity, counters, timestamps, and other control-related fields unless their update semantics are proven.
5. Stop and preserve all three inputs when both local and remote changed the same slot differently.
6. Feed the merged complete object into the original serialize, remote-stage, game-save, and commit/rollback path.
7. Replace `base` and the working local file only after the original server commit reports success.

## Safety limits

- Server validation of identity fields, revisions, counters, and per-slot timestamps has not been established.
- The first validation run is limited to the same account, a backed-up file, and one non-critical slot change.
- A failed stage, game save, or commit must not advance the local synchronization baseline.
