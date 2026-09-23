# Official Bank Recovery Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Identify the exact Pokémon Bank v1.5 Trainer/save mismatch recovery gate after network-interrupted saves, document the data flow, and add a recovery-only experimental probe/bypass without changing normal Bank save semantics.

**Architecture:** Keep `feature/official-bank-bulk-sync` behavior intact as the baseline. Add host-side static-analysis tooling that extracts selected Ghidra functions and direct call edges from `bank/docs/code.bin_all_functions.c`, use CI to publish the recovery-chain report, then only after a concrete compare/error branch is identified add a minimal experimental patch path isolated from the normal V3 hook. The production bulk merge and stock Prepare/Complete/Rollback flow remain unchanged.

**Tech Stack:** Python 3 static-analysis tooling, C host tests, ARMv6K Thumb/ARM patch assembly, GitHub Actions, existing Bank v1.5 Ghidra export.

**Spec:** `bank/docs/official-bank-recovery-research.zh-cn.md`

## Global Constraints

- Baseline stock `.code` SHA-256 remains `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`.
- Do not replace or bypass stock `PrepareUpdateBankObject`, `CompleteUpdateBankObject`, or `RollbackBankObject` in normal operation.
- Do not permanently force Trainer/game identity validation to success.
- Do not hardcode raw game-save offsets until the Bank CIA writer/validator path is identified.
- Any experimental bypass must be recovery-only and separately buildable from the normal V3 payload.
- Preserve the existing V3 mapped `.data` immutability rule and RX text-tail budget unless a separately verified patch range is introduced.

## Review Focus

- Large Ghidra export parsing must not confuse thunk names, duplicate address mentions, or call-site comments with function boundaries.
- Recovery analysis must distinguish server `pStatus/applicationId` state from BankObject source-game records and game-side linkage bookkeeping.
- A local mismatch bypass must not silently run during normal game selection or a clean save session.
- Experimental patching must not consume mapped `.data` or exceed executable patch space.
- CI/report generation must remain deterministic and not depend on network access beyond repository checkout/toolchain installation.

---

### Task 1: Recovery-chain static extractor

**Files:**
- Create: `bank/tools/extract_recovery_chain.py`
- Create: `bank/tools/test_extract_recovery_chain.py`

**Interfaces:**
- Consumes: `bank/docs/code.bin_all_functions.c`
- Produces: CLI that accepts one or more hex function addresses and emits exact function text plus direct `FUN_xxxxxxxx` callees.

- [ ] **Step 1: Write failing parser tests**

Create tests with a small synthetic Ghidra export containing two functions, a thunk, repeated address text in comments, and direct calls. Assert exact function extraction and unique direct-callee ordering.

- [ ] **Step 2: Run tests and verify RED**

Run: `python bank/tools/test_extract_recovery_chain.py`
Expected: FAIL because `extract_recovery_chain` does not exist.

- [ ] **Step 3: Implement the minimal parser/CLI**

Parse function header comments of the exact form `/* #N @ AAAAAAAA : NAME */`; slice until the next such header; derive direct calls with `FUN_([0-9a-fA-F]{8})` and `thunk_FUN_...`, excluding the function's own address.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python bank/tools/test_extract_recovery_chain.py`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `tools(bank): add recovery-chain extractor`

### Task 2: CI recovery report and baseline evidence

**Files:**
- Create: `.github/workflows/official-bank-recovery-research-ci.yml`
- Create: `bank/tools/recovery_targets.txt`

**Interfaces:**
- Consumes: Task 1 CLI.
- Produces: CI log/artifact containing the selected function bodies and direct call edges for state 8/11/17/18/22/23/7.

Target addresses:

```text
002ACBDC
002AF034
002A93F4
002A8760
002A9118
002AD7BC
002B1CF8
```

- [ ] **Step 1: Add a workflow-level smoke test command before report generation**

Run parser tests, then invoke the extractor against the real 11 MB Ghidra export and assert all seven targets are found.

- [ ] **Step 2: Add report generation**

Generate `/tmp/official-bank-recovery-chain.txt`, print a bounded summary to logs, and upload the full report as `official-bank-recovery-chain` artifact.

- [ ] **Step 3: Keep existing bulk-sync checks in the same research CI**

Compile/run `official_bulk_sync_host_test`, compile the ARMv6K Thumb production object, reject forbidden helpers, and enforce the existing payload budget.

- [ ] **Step 4: Commit and inspect CI output**

Commit message: `ci(bank): publish recovery-chain analysis`
Expected: workflow green; report contains all seven target functions.

### Task 3: Close the Trainer-mismatch data flow

**Files:**
- Modify: `bank/docs/official-bank-recovery-research.zh-cn.md`
- Create: `bank/docs/official-bank-recovery-address-map.zh-cn.md`

**Interfaces:**
- Consumes: Task 2 report and current BankObject layout knowledge.
- Produces: address map with evidence levels for transaction status, source-game record access, active-game identity reads, compare result, error/result branch, and recovery transition.

- [ ] **Step 1: Trace direct callees from state 11/17/18**

For every direct callee, extract its body when it reads `pStatus`, `pApplicationId`, BankObject source record offsets, active game model/profile, player name/TID fields, or sets an outer-state result/error code.

- [ ] **Step 2: Trace source-game record readers/writers**

Search the Ghidra export for constants/derived accesses corresponding to serialized `0xAD61C + n*0x44` or runtime `+8` equivalents and document confirmed functions.

- [ ] **Step 3: Identify the final mismatch decision**

Document the exact function/branch that distinguishes matching from mismatching prior-game identity, including input objects and return/result code. If not statically proven, explicitly leave it unresolved and do not proceed to a permanent bypass.

- [ ] **Step 4: Commit**

Commit message: `docs(bank): map trainer-mismatch recovery path`

### Task 4: Recovery-only classifier/probe contract

**Files:**
- Create: `bank/src/official_recovery_probe.h`
- Create: `bank/src/official_recovery_probe_core.c`
- Create: `bank/src/official_recovery_probe_host_test.c`

**Interfaces:**
- Consumes: confirmed state/branch inputs from Task 3.
- Produces: pure host-testable predicate `OfficialRecovery_ShouldProbe(...)` that returns true only for the confirmed incomplete-transaction/recovery context, never for a clean session.

- [ ] **Step 1: Write RED tests for clean and recovery cases**

Tests must include clean state, `pStatus 52`, `pStatus 53`, wrong outer state, special/HOME path, and unknown status.

- [ ] **Step 2: Run host test and verify RED**

Expected: compile/link failure because classifier is missing.

- [ ] **Step 3: Implement the smallest classifier matching confirmed evidence**

Do not encode guessed Trainer-ID semantics; only classify already-confirmed recovery context.

- [ ] **Step 4: Run all host tests and verify GREEN**

Run both recovery probe and existing bulk-sync host suites.

- [ ] **Step 5: Commit**

Commit message: `test(bank): define recovery-only probe gate`

### Task 5: Minimal experimental hook

**Files:**
- Create or modify only after Task 3 confirms the exact branch/address:
  - `bank/src/main_official_recovery.s`
  - `bank/src/official_recovery_probe.c`
  - `bank/src/verify_official_recovery.py`
- Modify: `.github/workflows/official-bank-recovery-research-ci.yml`

**Interfaces:**
- Consumes: Task 4 predicate and exact Task 3 mismatch branch.
- Produces: a separately built experimental patch that either logs/probes the mismatch path or, if the branch is fully proven, bypasses only that branch while already in the incomplete-transaction recovery context.

- [ ] **Step 1: Add verifier/test that fails without the intended patch**

Verifier must assert stock SHA, exact patch whitelist, unchanged mapped `.data`, and no changes to normal bulk-sync hook/save transaction addresses.

- [ ] **Step 2: Run verifier and verify RED**

Expected: FAIL because experimental patch does not exist.

- [ ] **Step 3: Implement the minimal hook**

Patch only the confirmed decision point. If static evidence cannot distinguish clean selection from recovery, implement logging/probe only; do not bypass.

- [ ] **Step 4: Compile and verify GREEN**

Run ARM build, host suites, payload/whitelist verifier, and existing bulk-sync regression checks.

- [ ] **Step 5: Commit**

Commit message: `exp(bank): add recovery-only trainer mismatch probe`

### Task 6: Real-device experiment matrix and release notes

**Files:**
- Modify: `bank/docs/official-bank-recovery-research.zh-cn.md`
- Create: `bank/docs/official-bank-recovery-test-matrix.zh-cn.md`

**Interfaces:**
- Consumes: experimental patch and diagnostics from Task 5.
- Produces: reproducible manual test protocol and interpretation table.

- [ ] **Step 1: Document control cases**

Include clean save, bulk save success, network failure before Prepare, upload interruption, and suspected post-game-save/pre-Complete failure.

- [ ] **Step 2: Document observations needed after reboot**

Record outer state, `pStatus`, `pApplicationId`, current/updated transaction versions, whether Trainer mismatch gate fires, whether bypass reaches stock recovery, and whether later RMC returns success/conflict/error.

- [ ] **Step 3: Define promotion criteria**

A bypass can move from experimental to default only if it never fires on clean sessions and stock recovery/rollback clears the server state without duplicate/loss behavior across repeated tests.

- [ ] **Step 4: Commit**

Commit message: `docs(bank): add recovery experiment matrix`
