# Official Bank Recovery B — Smart Commit/Rollback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed recovery path that preserves a tool-owned interrupted Bulk Sync transaction by committing only when stock game-save success was positively observed; otherwise it rolls back.

**Architecture:** Reuse the exact-transaction OBRX marker and stock state18 recovery model, but extend the marker with a durable stage field. The policy returns Commit only for stages at or beyond confirmed game-save success; all earlier exact-owned mismatches Rollback. Runtime IPS integration remains gated on verified Bank v1.5 machine-code hook sites.

**Tech Stack:** C11 host tests, ARMv6K Thumb freestanding C/ARM assembly, armips, Python static verification, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-23-official-bank-recovery-b-smart-commit-rollback-design.md`

## Global Constraints

- Target Pokémon Bank `00040000000C9B00` internal v1.5 only.
- Stock `.code` SHA-256 must be `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF` before any machine-code patch is emitted.
- Never weaken stock recovery for unrelated sessions.
- Never Commit merely because a marker exists; Commit requires exact tx ownership plus positively persisted/observed `GAME_SAVE_OK` or later stage.
- Unknown/impossible stage combinations fail closed to stock error or Rollback, never speculative Commit.
- Do not execute code from mapped `.data`.
- Until hardware validation, label runtime recovery `EXPERIMENTAL / STATICALLY VERIFIED ONLY`.

## Review Focus

- Torn/stale stage writes must never upgrade an unsafe transaction to Commit.
- Commit threshold must be exactly `GAME_SAVE_OK`, not `GAME_SAVE_STARTED`.
- Exact transaction comparison remains required at every stage.
- Repeated recovery after another network failure must be idempotent.
- Stage cleanup after successful Complete/Rollback must not affect normal Bank sessions.

---

### Task 1: Versioned staged marker format

**Files:**
- Modify: `bank/src/official_recovery_marker.h`
- Modify: `bank/src/official_recovery_marker_core.c`
- Modify: `bank/src/official_recovery_marker_host_test.c`

**Interfaces:**
- Add `OfficialRecoveryStage` enum: `NONE`, `BULK_APPLIED`, `TX_BOUND`, `GAME_SAVE_STARTED`, `GAME_SAVE_OK`, `REMOTE_COMPLETE_STARTED`, `DONE`.
- Add stage get/set API that preserves checksum and rejects backwards/illegal transitions.

- [ ] **Step 1: Write failing tests** for encode/decode stage, legal monotonic transitions, illegal backward transition, corrupt checksum, and version compatibility/fail-closed behavior.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement minimal staged marker** using currently reserved bytes without increasing 48-byte file size; bump marker version if required and explicitly reject unsupported versions.
- [ ] **Step 4: Verify GREEN**.
- [ ] **Step 5: Commit** `feat(bank): add staged smart recovery marker`.

### Task 2: Pure smart recovery policy

**Files:**
- Create: `bank/src/official_recovery_smart.h`
- Create: `bank/src/official_recovery_smart_core.c`
- Create: `bank/src/official_recovery_smart_host_test.c`

**Interfaces:**
- Produces `OfficialRecoverySmartAction`: `STOCK`, `ROLLBACK`, `COMMIT`, `LOCAL_CLEANUP`, `BLOCK`.
- Commit only when marker exact-matches current server pending transaction and stage >= `GAME_SAVE_OK`.

- [ ] **Step 1: Write failing matrix tests**: TX_BOUND -> ROLLBACK, GAME_SAVE_STARTED -> ROLLBACK, GAME_SAVE_OK -> COMMIT, REMOTE_COMPLETE_STARTED -> COMMIT, profile/field mismatch -> BLOCK, stock match -> STOCK, no pending + valid marker -> LOCAL_CLEANUP.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement minimal classifier** with explicit switch over stages; no numeric fall-through assumptions.
- [ ] **Step 4: Verify GREEN**.
- [ ] **Step 5: Commit** `feat(bank): add smart recovery decision policy`.

### Task 3: Runtime-neutral stage lifecycle adapter

**Files:**
- Create: `bank/src/official_recovery_smart_runtime.h`
- Create: `bank/src/official_recovery_smart_runtime_core.c`
- Create: `bank/src/official_recovery_smart_runtime_host_test.c`
- Modify: `bank/src/official_bulk_sync_prod.c`

**Interfaces:**
- `OnBulkApplied(profile)` -> staged pending marker.
- `OnTransactionBound(serverTx, profile)` -> exact tx + TX_BOUND.
- `OnGameSaveStarted()` -> GAME_SAVE_STARTED.
- `OnGameSaveSucceeded()` -> GAME_SAVE_OK.
- `OnRemoteCompleteStarted()` -> REMOTE_COMPLETE_STARTED.
- `OnMismatch(serverTx, profile, stockMatched)` -> reconstruct current server tx with status 1 or 2 according to policy.
- `OnRemoteResolved()` -> cleanup.

- [ ] **Step 1: Write failing lifecycle tests** including repeated callbacks and interrupted recovery attempts.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement runtime-neutral adapter**; do not raw-write game `main`.
- [ ] **Step 4: Verify GREEN plus existing marker/probe/bulk tests**.
- [ ] **Step 5: ARM-compile and check helper/text constraints**.
- [ ] **Step 6: Commit** `feat(bank): add smart recovery runtime core`.

### Task 4: Marker persistence and atomicity contract

**Files:**
- Create: `bank/src/official_recovery_marker_io.h`
- Create: `bank/src/official_recovery_marker_io_core.c`
- Create: `bank/src/official_recovery_marker_io_host_test.c`

**Interfaces:**
- Fixed path `/3ds/Bank/official_bulk_recovery.bin`.
- Encode to a complete 48-byte image before write; readers accept only complete valid image.

- [ ] **Step 1: Write failing tests** for exact-size images, torn/short writes, checksum failure, and idempotent invalidate.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement pure persistence contract**.
- [ ] **Step 4: Verify GREEN**.
- [ ] **Step 5: Commit** `feat(bank): define smart recovery marker persistence`.

### Task 5: Static hook-site verification for stage callbacks

**Files:**
- Modify: `bank/tools/disassemble_recovery_gate.py`
- Create: `bank/tools/verify_smart_recovery_hook_sites.py`
- Create: `bank/tools/test_verify_smart_recovery_hook_sites.py`
- Add/modify branch-specific CI workflow.

**Interfaces:**
- Must prove exact machine-code sites for: state7 tx bind, game-save-start, game-save-success callback, remote-complete-start, state18 mismatch edge, and final resolution cleanup.

- [ ] **Step 1: Write synthetic objdump tests** requiring exact original bytes/site ordering.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement fail-closed verifier** gated by stock size/hash.
- [ ] **Step 4: Verify GREEN on fixtures and expected refusal when stock `.code` is unavailable/wrong**.
- [ ] **Step 5: Commit** `tools(bank): verify smart recovery hook sites`.

### Task 6: Experimental IPS integration when exact bytes are available

**Files:**
- Modify: `bank/src/main_official.s`
- Modify: `bank/src/official_bulk_sync.c` or dedicated recovery runtime unit.
- Modify: `bank/src/verify_official_bulk_sync.py`

- [ ] **Step 1: Add static verifier assertions before patch code** for all overwritten instructions and RX budget.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Add minimal shims at verified sites** to advance stage and recover to stock Commit/Rollback; if exact machine bytes are unavailable, stop rather than guessing.
- [ ] **Step 4: Verify production object, IPS whitelist, bulk V3 regression, and no `.data` code execution**.
- [ ] **Step 5: Commit** `feat(bank): add experimental smart recovery hook`.

### Task 7: A/B validation matrix

**Files:**
- Create: `bank/docs/official-bank-recovery-b-test-guide.zh-cn.md`
- Modify: `bank/docs/README.zh-cn.md`

- [ ] **Step 1: Document fault windows and expected B behavior**, especially pre-game-save rollback versus post-game-save commit.
- [ ] **Step 2: Define evidence capture**: marker stage, server tx fields, stock local/game records, chosen action, remote result, re-entry result.
- [ ] **Step 3: Define direct comparison against Variant A** for the same interrupted transaction class.
- [ ] **Step 4: Run all available host/static/ARM CI and record hardware-only gaps**.
- [ ] **Step 5: Commit** `docs(bank): add smart recovery validation guide`.
