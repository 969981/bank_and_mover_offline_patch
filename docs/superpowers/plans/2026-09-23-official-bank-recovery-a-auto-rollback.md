# Official Bank Recovery A — Auto Rollback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed recovery path that automatically rolls back only exact tool-owned pending Bank transactions when stock state18 would otherwise raise Trainer/save mismatch.

**Architecture:** Reuse the existing OBRX two-phase marker and stock recovery model. Add a pure policy layer first, then marker persistence helpers, then runtime integration points for state16 apply-success, state7 transaction binding, state18 mismatch recovery, and success cleanup. Runtime IPS integration is allowed only after exact stock instruction bytes are verified from the known Bank v1.5 `.code` image.

**Tech Stack:** C11 host tests, ARMv6K Thumb freestanding C/ARM assembly, armips, Python static verification, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-23-official-bank-recovery-a-auto-rollback-design.md`

## Global Constraints

- Target Pokémon Bank `00040000000C9B00` internal v1.5 only.
- Stock `.code` SHA-256 must be `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF` before any machine-code patch is emitted.
- Never weaken normal stock Trainer/save validation for non-tool transactions.
- Never fabricate `transactionPassword`; reconstruct only from current server pending transaction.
- Variant A always selects Rollback for exact tool-owned mismatch recovery.
- Do not execute code from mapped `.data`.
- Until hardware validation, label runtime recovery `EXPERIMENTAL / STATICALLY VERIFIED ONLY`.

## Review Focus

- Pending-only/corrupt/stale markers must fail closed.
- Any profile or transaction-field mismatch must preserve stock error behavior.
- Existing exact stock local/game recovery records must remain stock-owned.
- Marker I/O failure must never turn an otherwise valid normal save into failure.
- Cleanup after successful rollback must be idempotent.

---

### Task 1: Pure auto-rollback policy

**Files:**
- Create: `bank/src/official_recovery_auto_rollback.h`
- Create: `bank/src/official_recovery_auto_rollback_core.c`
- Create: `bank/src/official_recovery_auto_rollback_host_test.c`

**Interfaces:**
- Consumes: `OfficialRecoveryRecord`, OBRX marker bytes, active profile, server-pending presence, and whether stock local/game recovery already matched.
- Produces: `OfficialRecoveryAutoAction` with `STOCK`, `ROLLBACK`, `LOCAL_CLEANUP`, or `BLOCK`.

- [ ] **Step 1: Write failing tests** covering exact bound marker -> ROLLBACK, pending-only -> BLOCK, profile/field mismatch -> BLOCK, stock match -> STOCK, no server pending + valid bound marker -> LOCAL_CLEANUP.
- [ ] **Step 2: Run host compile and verify RED** because the new policy symbols do not exist.
- [ ] **Step 3: Implement the minimal classifier** using `OfficialRecoveryMarker_MatchesServer`; never inspect stale game/local transaction fields for tool recovery.
- [ ] **Step 4: Run tests and verify GREEN** with `cc -std=c11 -O2 -Wall -Wextra -Werror`.
- [ ] **Step 5: Commit** `feat(bank): add auto rollback recovery policy`.

### Task 2: Marker persistence contract

**Files:**
- Create: `bank/src/official_recovery_marker_io.h`
- Create: `bank/src/official_recovery_marker_io_core.c`
- Create: `bank/src/official_recovery_marker_io_host_test.c`

**Interfaces:**
- Produces fixed path `/3ds/Bank/official_bulk_recovery.bin`, exact-size read/write validation, and invalidate semantics independent of 3DS FS syscalls.

- [ ] **Step 1: Write failing tests** for exact 48-byte read/write image acceptance, short/long image rejection, corrupt checksum rejection via marker decode, and invalidate-to-zero semantics.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement pure buffer contract**; runtime FS adapter remains separate.
- [ ] **Step 4: Verify GREEN**.
- [ ] **Step 5: Commit** `feat(bank): define recovery marker persistence contract`.

### Task 3: Runtime recovery adapter without stock patching

**Files:**
- Create: `bank/src/official_recovery_runtime.h`
- Create: `bank/src/official_recovery_runtime_core.c`
- Create: `bank/src/official_recovery_runtime_host_test.c`
- Modify: `bank/src/official_bulk_sync_prod.c`

**Interfaces:**
- `OfficialRecovery_OnBulkApplied(profile)` -> pending marker image.
- `OfficialRecovery_OnTransactionBound(serverTx, profile)` -> bound marker image.
- `OfficialRecovery_OnMismatch(serverTx, profile, stockMatched)` -> runtime `status=1` recovery record only when policy says ROLLBACK.
- `OfficialRecovery_OnRemoteResolved()` -> cleanup request.

- [ ] **Step 1: Write failing end-to-end host tests** for marker lifecycle and mismatch-to-rollback reconstruction.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement runtime-neutral adapter** around policy/marker functions; no raw game save writes.
- [ ] **Step 4: Verify GREEN plus existing bulk/recovery tests**.
- [ ] **Step 5: ARM-compile production object and enforce no unexpected runtime helpers**.
- [ ] **Step 6: Commit** `feat(bank): add auto rollback recovery runtime core`.

### Task 4: Static hook-site verification

**Files:**
- Modify: `bank/tools/disassemble_recovery_gate.py`
- Create: `bank/tools/verify_recovery_hook_sites.py`
- Create: `bank/tools/test_verify_recovery_hook_sites.py`
- Modify: `.github/workflows/official-bank-recovery-research-ci.yml` or create branch-specific workflow.

**Interfaces:**
- Consumes verified stock `.code`.
- Produces exact instruction whitelist for state7 transaction-bound hook and state18 mismatch-edge hook.

- [ ] **Step 1: Write parser/verifier tests against synthetic objdump text** requiring explicit original bytes and branch addresses.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement verifier** that refuses output when stock `.code` is absent, wrong size/hash, or expected instructions cannot be proven.
- [ ] **Step 4: Verify GREEN on synthetic fixtures and expected fail-closed behavior without stock `.code`**.
- [ ] **Step 5: Commit** `tools(bank): verify auto rollback hook sites`.

### Task 5: Experimental IPS integration when exact bytes are available

**Files:**
- Modify: `bank/src/main_official.s`
- Modify: `bank/src/official_bulk_sync.c` or add a dedicated minimal runtime unit.
- Modify: `bank/src/verify_official_bulk_sync.py`

**Interfaces:**
- Hook state16 apply success -> persist pending marker.
- Hook state7 after real transaction exists -> bind marker.
- Hook state18 mismatch edge -> call recovery policy and rejoin stock Rollback only on exact owned tx.
- Hook Complete/Rollback success -> invalidate marker.

- [ ] **Step 1: Add verifier assertions first** for every overwritten instruction and RX-tail size.
- [ ] **Step 2: Verify RED before assembly patch exists**.
- [ ] **Step 3: Implement minimal assembly shims only at verified sites**; if exact stock bytes are unavailable, stop here and document the blocker rather than guessing.
- [ ] **Step 4: Build/verify patch and ensure existing state16 bulk hook bytes remain expected**.
- [ ] **Step 5: Commit** `feat(bank): add experimental auto rollback hook`.

### Task 6: Validation guide and branch status

**Files:**
- Create: `bank/docs/official-bank-recovery-a-test-guide.zh-cn.md`
- Modify: `bank/docs/README.zh-cn.md`

- [ ] **Step 1: Document clean save, pre-bind failure, post-bind mismatch, automatic rollback, re-entry, repeat-save, and ordinary manual Bank regression cases.**
- [ ] **Step 2: Document captured fields and marker state for each case.**
- [ ] **Step 3: Run full available host/static/ARM CI and record exact remaining hardware-only validation.**
- [ ] **Step 4: Commit** `docs(bank): add auto rollback recovery validation guide`.
