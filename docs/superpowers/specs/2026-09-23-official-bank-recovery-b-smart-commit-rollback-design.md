# Official Bank Recovery B — Smart Commit / Rollback Design

## Purpose

Build an experimental self-healing recovery path for Pokémon Bank v1.5 that prevents Official Bulk Sync sessions from remaining blocked after a network-interrupted save while preserving a successfully progressed transaction whenever evidence is strong enough. Variant B uses exact transaction ownership plus save-stage evidence to choose stock Commit or stock Rollback.

## Baseline

- Source branch: `feature/official-bank-recovery-research`
- Intended implementation branch: `feature/official-bank-recovery-smart`
- Original functional baseline: `feature/official-bank-bulk-sync`
- Bank title: `00040000000C9B00`, internal v1.5
- Verified stock `.code` SHA-256: `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`
- The supplied CIA is a NoCrypto NCCH; its ExeFS `.code` can be extracted and BLZ-decompressed directly to the verified stock image.

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

## Important machine-code correction

Verified stock state7 behavior is now known exactly:

```text
case3 @ 0x002B1E18
    write exact current transaction to GameRecoveryRecord
    status = 2
    start game main save

0x002B1F1C
    enter case4 / wait game save

case4
0x002B1F3C CMP r0,#1
0x002B1F40 MOVEQ r0,#5
0x002B1F44 MOVNE r0,#7

case5 @ 0x002B1F4C
    reached only after game-save success
    write exact transaction/status=2 to Bank-local recovery record

case9 @ 0x002B20A0
    start CompleteUpdate
```

This has two design consequences.

### 1. TX_BOUND at state7 case3 is too late

A server pending transaction can already exist after `PrepareUpdateBankObject` while HPP/HTTP upload still has not completed. If the network fails there, state7 never reaches case3, so neither game nor Bank-local recovery record contains the new transaction.

Therefore `TX_BOUND` must be captured:

```text
PrepareUpdate response returns exact server BankTransactionParam
        ↓
TX_BOUND marker persisted
        ↓
HPP/upload continues
```

not:

```text
HPP/upload finished
        ↓
state7 case3
        ↓
TX_BOUND               ❌ too late
```

### 2. GAME_SAVE_OK + stock mismatch is not the normal primary failure case

Once case3 writes the exact transaction/status=2 and the game save is positively confirmed, the next startup should already have a valid game recovery record that state18 can match and use to retry stock Commit.

Therefore the previously assumed common window:

```text
game save success
final Complete network failure
next startup Trainer mismatch
```

is **not** the best explanation under stock semantics. A plain final-Complete failure should normally be recoverable by stock from the persisted game record.

The higher-confidence mismatch window is earlier:

```text
PrepareUpdate creates pending T1
        ↓
HPP/upload/network fails before case3
        ↓
no game/local recovery T1
        ↓
state18 mismatch
```

Variant B is still kept as requested, but its auto-Commit branch is now explicitly an **experimental fault-injection path**, not the default explanation for real-world Trainer mismatch.

## Variant B Principle

Do not infer Commit merely because a transaction is tool-owned. Commit is allowed only when the tool has positive stage evidence and hardware fault injection confirms that a `GAME_SAVE_OK+` marker can coexist with stock local/game mismatch for the exact same server transaction.

Until that combination is proven on hardware, the production-safe interpretation is:

```text
owned exact mismatch
    -> Rollback
```

while the smart action selector remains available for controlled experiments.

## Marker State Machine

The OBRX v2 marker uses monotonic stages:

```text
NONE
BULK_APPLIED
TX_BOUND
GAME_SAVE_STARTED
GAME_SAVE_OK
REMOTE_COMPLETE_STARTED
DONE
```

### BULK_APPLIED

Created after state16 successfully overlays `bulk_import.bin`. Contains profile but no valid transaction identity yet.

### TX_BOUND

Must be written at the earliest confirmed `PrepareUpdateBankObject` response point, before HPP upload completion, and binds:

```text
dataId
transactionPassword
curVersion
updateVersion
size
profile
```

### GAME_SAVE_STARTED

Verified semantic point:

```text
0x002B1F1C  MOV r0,#4
```

At this point case3 has already written the exact transaction/status=2 into the game recovery object and has invoked the stock game save path.

### GAME_SAVE_OK

Verified semantic point:

```text
0x002B1F4C  case5 entry
```

The previous case4 branches here only when the game-save poll returned `1`.

### REMOTE_COMPLETE_STARTED

Verified semantic point:

```text
0x002B20A0  case9 entry
```

This stage may remain useful for diagnostics/fault injection.

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

Current experimental action table remains:

```text
marker invalid/not exact    -> stock mismatch
stage < TX_BOUND            -> stock mismatch
TX_BOUND                    -> ROLLBACK
GAME_SAVE_STARTED           -> ROLLBACK
GAME_SAVE_OK                -> COMMIT      [experimental]
REMOTE_COMPLETE_STARTED     -> COMMIT      [experimental]
unknown/newer stage         -> fail closed
```

The recovered runtime context must be built from the current server transaction, not stale local/game data. Only the direction/status is selected:

```text
ROLLBACK -> status = 1
COMMIT   -> status = 2
```

## Exact state18 Hook Surface

Both dataId and curVersion mismatch branches converge at:

```asm
0x002A8AD0  MOV r0,#8
```

Original bytes:

```text
08 00 A0 E3
```

At this point `r4` is the state18 object and `[r4+0x28]` points to the current server pending transaction. A recovery shim can therefore fail closed to the original instruction or build the canonical transaction context from the current server tx and select:

```text
substate 5 -> stock Commit
substate 6 -> stock Rollback
```

Stock operations remain:

```text
0x001D5D74 Commit
0x001D5C28 Rollback
```

No custom network implementation is required.

## Why Commit stays experimental

A `GAME_SAVE_OK` marker records our observation that stock game save previously succeeded. But if the next state18 cannot match the game recovery record that stock wrote before that save, one of the assumptions below has failed:

- the game recovery object did not persist as expected;
- another stock cleanup path altered it;
- the server transaction changed;
- the observed stage did not correspond to durable save completion;
- an additional failure mode exists outside current static analysis.

Therefore B must not silently treat `GAME_SAVE_OK` as sufficient production evidence until fault injection demonstrates the exact combination and a repeated Commit is safe.

The intended A/B comparison is now:

```text
A: exact owned mismatch -> always Rollback
B: exact owned mismatch -> stage-aware action for controlled validation
```

with A remaining the preferred safety baseline.

## Runtime Mutation Policy

Prefer runtime repair first:

1. Read and validate bound marker against current server pending transaction.
2. Build a temporary state18 transaction context from the current server transaction.
3. Select stock Rollback or experimental Commit according to policy.
4. Rejoin stock substate 6 or 5.
5. Only after remote success allow stock cleanup/persistence and remove the marker.

Do not pre-write a fabricated recovery record to raw game `main` merely to satisfy the compare. If persistence before remote action is ever required, use stock family-specific writer/save paths, never raw offsets/checksum bypasses.

## Idempotence and Restart Safety

Recovery itself can fail again due to network loss. Therefore:

- marker remains until stock Commit/Rollback success is confirmed;
- retrying with the same exact server transaction repeats the same decision;
- a changed/nonmatching server transaction causes fail-closed behavior;
- if server has no matching pending transaction, perform local marker cleanup only;
- never upgrade a stale marker to a new server transaction during recovery.

## Hook Surface

Variant B runtime observation points are now:

1. state16 bulk-apply success -> `BULK_APPLIED`;
2. **PrepareUpdate response before HPP completion -> `TX_BOUND`**;
3. `0x002B1F1C` -> `GAME_SAVE_STARTED`;
4. `0x002B1F4C` -> `GAME_SAVE_OK`;
5. `0x002B20A0` -> `REMOTE_COMPLETE_STARTED`;
6. `0x002A8AD0` state18 mismatch convergence -> exact marker match + policy + stock recovery rejoin;
7. normal/recovery success -> marker cleanup.

Only item 2 still needs an exact machine-code address. The other state7/state18 points are verified against the exact stock SHA.

## Safety Gates

Automatic Commit is forbidden unless all are true:

- marker format/checksum valid;
- active profile matches marker;
- marker is bound to current server pending transaction across all transaction fields;
- marker stage is `GAME_SAVE_OK` or `REMOTE_COMPLETE_STARTED`;
- code is executing in the verified state18 mismatch context;
- server transaction status is compatible with the stock recovery operation;
- hardware fault-injection evidence has validated this stage/mismatch combination.

Before hardware validation of the last condition, smart Commit remains experimental and A-style Rollback is the safety reference.

## Code-Space Constraints

- Existing V3 RX tail is limited to `0x00313910..0x00314000` (`0x6F0`).
- Existing Bulk V3 already uses most of it.
- Variant B adds more observation hooks than A, so code pressure is higher.
- Prefer tiny ARM shims and reuse common marker/FS code.
- Do not execute from `.data` / `.rodata` / `.bss`.
- If extra RX space is needed, use only a stock function body proven unreachable by XREF/CFG analysis.

## Testing

Host tests continue to pin the experimental action table:

```text
exact + TX_BOUND                -> ROLLBACK
exact + GAME_SAVE_STARTED       -> ROLLBACK
exact + GAME_SAVE_OK            -> COMMIT
exact + REMOTE_COMPLETE_STARTED -> COMMIT
not exact                       -> BLOCK
pending-only                    -> BLOCK
unknown stage                   -> BLOCK
```

Real-hardware fault matrix must place special emphasis on:

1. failure before Prepare response;
2. **failure after Prepare response but before state7 case3**;
3. failure after case3 but before game save success;
4. failure after GAME_SAVE_OK;
5. failure during Complete;
6. clean success.

For each run record:

```text
server pending transaction
marker stage / tx
stock local recovery record
stock game recovery record
state18 action
remote result
subsequent Bank re-entry
```

The key research question for B is whether a real `GAME_SAVE_OK+` marker can ever coincide with both stock recovery records failing to match the same exact server transaction.

## Success Criterion

For an exact tool-owned bulk transaction, network interruption no longer causes a permanent mismatch lock. Earlier/ambiguous transactions are safely rolled back. Smart Commit remains available only when positive stage evidence plus hardware validation justify it. Unrelated or unverifiable sessions retain stock behavior.
