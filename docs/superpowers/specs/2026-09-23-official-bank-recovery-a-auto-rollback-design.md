# Official Bank Recovery A — Auto Rollback Design

## Purpose

Build an experimental recovery path for Pokémon Bank v1.5 that prevents Official Bulk Sync sessions from remaining permanently blocked after a network-interrupted save. Variant A prioritizes safety and determinism: when stock state18 cannot match either Bank-local or game recovery records to the server pending transaction, but the tool can prove that pending transaction belongs to the current bulk-only session, reconstruct a recovery context with `status=1` and hand control back to the stock Rollback path.

## Baseline

- Source branch: `feature/official-bank-recovery-research`
- Intended implementation branch: `feature/official-bank-recovery-auto-rollback`
- Original functional baseline: `feature/official-bank-bulk-sync`
- Bank title: `00040000000C9B00`, internal v1.5
- Verified stock `.code` SHA-256: `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`

## Confirmed Stock Behavior

Stock state18 at `0x002A8760` compares the server pending transaction against Bank-local and game recovery records. The blocking predicate is transaction identity/version, not ordinary Trainer ID:

```text
server.dataId == recovery.dataId
&&
server.curVersion == recovery.curVersion
```

When a record matches, `status=1` selects Rollback and `status=2` selects Commit. When neither persisted record matches, stock enters the mismatch/error path and formats trainer metadata for the UI.

Game recovery record layout:

```text
+0x00 dataId                u64
+0x08 transactionPassword   u64
+0x10 curVersion            u32
+0x14 updateVersion         u32
+0x18 size                  u32
+0x1C status                u8
```

Family-specific runtime objects:

```text
Gen6  model + 0x1ADF8
SM    model + 0xB1394
USUM  model + 0xB4570
```

Variant A must preserve all normal stock validation and transaction behavior unless a tool-owned, exact-match recovery marker proves ownership of the pending transaction.

## Ownership Marker

Reuse the research branch OBRX two-phase marker.

### Phase 1 — BULK_PENDING

After state16 successfully applies `bulk_import.bin`, persist:

```text
magic/version/profile
flags = BULK_PENDING
transaction fields = zero
checksum
```

This phase is not sufficient for automatic recovery.

### Phase 2 — TX_BOUND

After stock Prepare/Stage has produced the actual `BankTransactionParam`, bind the marker to:

```text
dataId
transactionPassword
curVersion
updateVersion
size
profile
flags = BULK_APPLIED / TX_BOUND
checksum
```

Only a same-profile pending marker may be upgraded.

## Recovery Decision

Variant A is intentionally simple:

```text
stock local record matches -> stock recovery unchanged
stock game record matches  -> stock recovery unchanged
otherwise:
    marker exact-matches current server tx?
        no  -> stock mismatch/error
        yes -> build runtime recovery record from CURRENT server tx
               status = 1
               route into stock Rollback path
```

The reconstructed record must use the current server transaction fields, never fields copied from a stale game/local recovery record.

## Runtime Write Policy

Do not immediately raw-write the game `main` merely to make the comparison pass. Preferred order:

1. Construct a runtime recovery record from current server transaction.
2. Invoke/rejoin the stock Rollback path.
3. After stock Rollback succeeds, clear the tool marker.
4. Allow stock cleanup to clear/persist the appropriate game/local recovery state.

If runtime architecture requires a temporary local/game record object to satisfy stock helpers, mutate only the in-memory model before server success. Do not persist repaired records ahead of a successful stock Rollback unless static analysis proves the stock path requires it.

## No-Pending Cleanup

If a bound marker exists but the server no longer reports the matching pending transaction, do not issue Commit or Rollback. Treat this as a stale local marker and clean it only after confirming there is no matching server transaction.

## Fail-Closed Conditions

Variant A must retain stock mismatch behavior when any of these are true:

- marker absent;
- marker checksum/version invalid;
- marker is only BULK_PENDING;
- active profile differs;
- `dataId` differs;
- `transactionPassword` differs;
- `curVersion` differs;
- `updateVersion` differs;
- `size` differs;
- server transaction status is unsupported/unknown;
- runtime hook cannot prove it is executing in the state18 recovery path.

## Hook Surface

Minimum runtime integration points:

1. state16 bulk-apply success: persist BULK_PENDING marker;
2. state7 after Prepare/Stage returns the actual transaction: bind marker to TX_BOUND;
3. state18 mismatch edge: if exact marker/server match, construct `status=1` recovery context and rejoin stock Rollback;
4. normal Complete success: delete/invalidate marker;
5. recovery Rollback success: delete/invalidate marker.

Exact ARM branch sites and overwritten bytes must be derived from the verified stock `.code`; no guessed machine-code patch is allowed.

## Code-Space Constraints

- Existing V3 RX tail: `0x00313910..0x00314000` (`0x6F0` bytes).
- Do not execute from mapped `.data`.
- Prefer a minimal assembly shim and reuse existing filesystem helpers.
- Static verifier must whitelist every modified stock instruction and fail when payload exceeds the verified executable-space budget.

## Testing

Host/static tests must cover:

1. exact bound marker + mismatch -> ROLLBACK decision;
2. pending-only marker -> BLOCK;
3. profile mismatch -> BLOCK;
4. any server transaction field mismatch -> BLOCK;
5. corrupt marker -> BLOCK;
6. no pending server transaction + stale marker -> LOCAL_CLEANUP only;
7. existing exact stock local/game recovery record remains stock-owned;
8. ordinary non-bulk Bank session is untouched.

Real-hardware validation must include:

- clean bulk save;
- network failure before transaction bind;
- network failure after transaction bind;
- observed Trainer/save mismatch with exact marker;
- automatic rollback followed by successful re-entry to Bank;
- repeat clean bulk save after recovery;
- ordinary manual Game ↔ Bank operation regression.

Until that matrix is verified on hardware, label the branch `EXPERIMENTAL / STATICALLY VERIFIED ONLY`.

## Success Criterion

For tool-owned bulk sessions, a server pending transaction that would otherwise lead to stock Trainer/save mismatch is automatically and safely rolled back, clearing the pending transaction and restoring Bank usability without weakening validation for unrelated sessions.
