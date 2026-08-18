# Poke Mover Upload Patch Design

## Scope

The upload patch submits locally prepared Transfer Box changes through a fresh online Mover session while preserving fields not owned by the Transfer Box operation.

## Online re-upload sequence

1. Complete normal online authentication and download the latest complete Bank file as `remote`.
2. Obtain the current session's fresh remote transaction descriptor.
3. Compare `base`, `local`, and `remote` for the 30 Transfer Box records at `0x0AAF14` and their 30 tags at `0x0AD5FC`.
4. Apply non-conflicting local record-and-tag pairs to `remote`; preserve all fields outside the intended Transfer Box edit.
5. Stop on a conflicting change to the same Transfer Box slot.
6. Use the original complete-object serialization, remote stage, cartridge save, and commit/rollback states.
7. Advance the local synchronization baseline only after server commit succeeds.

## Safety limits

- Server rules for fields outside the Transfer Box remain unknown.
- The first validation run is limited to the same account, one backed-up transfer-slot change, and a recoverable cartridge save.
- A stale transaction descriptor is never reusable.
