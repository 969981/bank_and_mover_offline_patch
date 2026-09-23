# Official Bank Recovery B — Smart Commit / Rollback Design

## Purpose

Build an experimental self-healing recovery path for Pokémon Bank v1.5 that prevents Official Bulk Sync sessions from remaining blocked after a network-interrupted save while preserving a successfully progressed transaction whenever evidence is strong enough. Variant B uses exact transaction ownership plus save-stage evidence to choose stock Commit or stock Rollback.

## Baseline

- Source branch: `feature/official-bank-recovery-research`
- Intended implementation branch: `feature/official-bank-recovery-smart`
- Original functional baseline: `feature/official-bank-bulk-sync`
- Bank title: `00040000000C9B00`, internal v1.5
- Verified stock `.code` SHA-256: `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`

## Confirmed Stock Behavior

Stock state18 at `0x002A8760` blocks when the current server pending transaction cannot be reconciled with either the Bank-local persistent recovery record or the active game's recovery record. The core match is transaction identity/version (`dataId + curVersion`); matched records then use `status=1` for Rollback and `status=2` for Commit.

Game recovery record:

```text
+0x00 dataId                u64
+0x08 transactionPassword   u64
+0x10 curVersion            u32
+0x14 updateVersion         u32
+0x18 size                  u32
+0x1C status                u8
```

The recovery UI's Trainer information is display metadata and is not the core blocking predicate.

## Variant B Principle

Do not infer Commit merely because a transaction is tool-owned. Commit is allowed only when the tool has positive evidence that the stock game-save phase completed successfully for the exact server transaction. Otherwise use Rollback.

```text
owned exact transaction
        ↓
stock recovery records mismatch
        ↓
marker stage evidence
        ├─ GAME_SAVE_OK or stronger -> COMMIT
        └─ otherwise                -> ROLLBACK
```

This keeps the failure default conservative while allowing the common "game save succeeded, final Complete request lost" window to preserve the staged Bank update.

## Marker State Machine

Extend the OBRX marker with a monotonic stage field/flags. Exact binary encoding may remain within the existing fixed marker size if layout permits; version must be incremented when the persisted format changes.

Required semantic stages:

```text
NONE
BULK_APPLIED
TX_BOUND
GAME_SAVE_STARTED
GAME_SAVE_OK
REMOTE_COMPLETE_STARTED
DONE
```

Only `TX_BOUND`, `GAME_SAVE_STARTED`, `GAME_SAVE_OK`, and `REMOTE_COMPLETE_STARTED` are required for recovery decisions. `DONE` is transient/diagnostic; a successfully completed session should delete/invalidate the marker.

### BULK_APPLIED

Created after state16 successfully overlays `bulk_import.bin`. Contains profile but no valid transaction identity yet.

### TX_BOUND

Written once stock Prepare/Stage has returned a complete transaction context:

```text
dataId
transactionPassword
curVersion
updateVersion
size
profile
```

### GAME_SAVE_STARTED

Set immediately before the stock path begins persisting the game recovery record/main for this transaction. This stage is not sufficient for Commit.

### GAME_SAVE_OK

Set only after the stock game-save completion callback/result has positively indicated success for the same transaction. This is the minimum stage that permits automatic Commit.

### REMOTE_COMPLETE_STARTED

Optional but useful diagnostic stage set immediately before stock CompleteUpdate is initiated. It still permits Commit on restart because GAME_SAVE_OK has already been proven.

## Recovery Policy

Existing valid stock recovery records always take precedence. Variant B activates only after stock local and game reconciliation both fail.

Then require exact marker/server transaction match across:

```text
profile
dataId
transactionPassword
curVersion
updateVersion
size
```

Decision:

```text
marker invalid/not exact    -> stock mismatch
stage < TX_BOUND            -> stock mismatch
TX_BOUND                    -> ROLLBACK
GAME_SAVE_STARTED           -> ROLLBACK
GAME_SAVE_OK                -> COMMIT
REMOTE_COMPLETE_STARTED     -> COMMIT
unknown/newer stage         -> fail closed to stock mismatch unless explicitly supported
```

The recovered runtime record must be built from the current server transaction, not stale local/game data. Only `status` is selected by policy:

```text
ROLLBACK -> status = 1
COMMIT   -> status = 2
```

Then rejoin the corresponding stock recovery path.

## Why GAME_SAVE_OK Is the Commit Boundary

Stock Bank deliberately places the game save between remote staging and final Complete. If the game-save callback returned success, the game-side recovery bookkeeping/main is known to have crossed the transaction boundary. A lost or failed network Complete after that point is the exact case where retrying stock Commit is aligned with the original transaction intent.

`GAME_SAVE_STARTED` is insufficient because power loss/write failure can occur after start but before durable completion.

## Runtime Mutation Policy

As with Variant A, prefer runtime repair first:

1. Read and validate bound marker against current server pending transaction.
2. Build a temporary recovery context from the server transaction.
3. Set `status=1` or `2` according to the marker stage.
4. Rejoin stock Rollback/Commit.
5. Only after remote success allow stock cleanup/persistence and remove the marker.

Do not pre-write a fabricated recovery record to raw game `main` merely to satisfy the compare unless static control-flow analysis proves that stock helpers require it. If persistence before remote action is unavoidable, use stock family-specific writer/save paths, never raw offsets/checksum bypasses.

## Idempotence and Restart Safety

Recovery itself can fail again due to network loss. Therefore:

- marker remains until stock Commit/Rollback success is confirmed;
- retrying with the same exact server transaction repeats the same decision;
- a changed/nonmatching server transaction causes fail-closed behavior;
- if server has no matching pending transaction, perform local marker cleanup only;
- never "upgrade" a stale marker to a new server transaction during recovery.

## Hook Surface

Variant B requires more stock observation points than A:

1. state16 bulk-apply success -> `BULK_APPLIED`;
2. state7 Prepare/Stage success -> `TX_BOUND`;
3. immediately before game save starts -> `GAME_SAVE_STARTED`;
4. positive game-save completion branch/callback -> `GAME_SAVE_OK`;
5. optional pre-Complete branch -> `REMOTE_COMPLETE_STARTED`;
6. state18 mismatch edge -> exact marker match, policy decision, runtime recovery reconstruction, stock Commit/Rollback rejoin;
7. normal Complete success and recovery Commit/Rollback success -> marker cleanup.

Each hook requires exact machine-code verification against the stock `.code` hash and a patch whitelist.

## Safety Gates

Automatic Commit is forbidden unless all are true:

- marker format/checksum valid;
- active profile matches marker;
- marker is bound to current server pending transaction across all transaction fields;
- marker stage is `GAME_SAVE_OK` or `REMOTE_COMPLETE_STARTED`;
- code is executing in the known state18 mismatch recovery context;
- server transaction status is compatible with the stock recovery operation being retried.

If any condition is uncertain, downgrade to Rollback only when exact transaction ownership is still proven; otherwise retain stock mismatch behavior.

## Relationship to Variant A

Variant B should share a common pure recovery policy layer with A where possible:

```text
validate marker
validate exact transaction ownership
build runtime recovery record
cleanup marker
```

Only the action selector differs:

```text
A: exact owned mismatch -> always ROLLBACK
B: exact owned mismatch -> COMMIT iff GAME_SAVE_OK+, else ROLLBACK
```

Keeping the common layer equivalent makes hardware A/B comparison meaningful.

## Code-Space Constraints

- Existing V3 RX tail is limited (`0x00313910..0x00314000`).
- Variant B adds stage hooks, so code-size pressure is higher than A.
- Prefer tiny assembly branch shims and a compact shared marker/policy helper.
- Do not execute code from mapped `.data`.
- If safe RX space cannot be proven, stop at a statically verified experimental source build rather than using an unsafe cave.

## Testing

Host tests must pin the action table:

```text
exact + TX_BOUND                -> ROLLBACK
exact + GAME_SAVE_STARTED       -> ROLLBACK
exact + GAME_SAVE_OK            -> COMMIT
exact + REMOTE_COMPLETE_STARTED -> COMMIT
not exact                       -> BLOCK
pending-only                    -> BLOCK
unknown stage                   -> BLOCK
```

Additional tests:

- marker downgrade/rewind is rejected;
- stage update cannot change transaction identity;
- profile mismatch blocks;
- corrupted marker blocks;
- stale marker + no server pending -> cleanup only;
- normal stock matching local/game record bypasses tool policy entirely;
- repeated recovery retry is idempotent.

Real-hardware fault matrix should attempt failures at observable boundaries:

1. before Prepare;
2. after Prepare / before game save;
3. during game save;
4. after game-save success / before Complete;
5. during Complete;
6. clean success.

Capture marker stage, server pending metadata, whether stock local/game recovery records match, chosen action, remote result, and subsequent ability to re-enter Bank.

## Success Criterion

For an exact tool-owned bulk transaction, network interruption no longer causes a permanent mismatch lock. Transactions that reached confirmed game-save success are retried through stock Commit when safe; earlier/ambiguous transactions are safely rolled back. Unrelated or unverifiable sessions retain stock behavior.
