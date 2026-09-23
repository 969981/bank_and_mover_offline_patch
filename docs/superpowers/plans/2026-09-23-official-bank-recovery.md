# Official Bank Recovery Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Identify the exact Pokémon Bank v1.5 Trainer/save mismatch decision reached after a network-interrupted save, document its data flow, and add the smallest safe experimental recovery hook only if the root cause is statically localized.

**Architecture:** Preserve the existing Official Bulk Sync V3 runtime-overlay architecture and stock save/upload transaction. First add reusable static-analysis tooling that extracts selected functions and references from the 11 MB Ghidra export, then use that evidence to map state 7/8/11/17/18/22/23 and source-game trainer records. Production behavior changes are gated on a proven recovery-only decision point and are accompanied by host/static tests and patch-layout verification.

**Tech Stack:** Python 3 standard library, C11 host contract tests, ARMv6K Thumb freestanding C/ARM assembly, arm-none-eabi GCC/binutils, armips/flips verification workflow, GitHub Actions.

**Spec:** `bank/docs/official-bank-network-failure-trainer-mismatch-recovery.zh-cn.md`

## Global Constraints

- Base all work on `feature/official-bank-bulk-sync`; do not modify that branch.
- Target only Bank v1.5 stock `.code` SHA-256 `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`.
- Preserve normal Official Bulk Sync behavior and the stock PrepareUpdate/HPP/game-save/Complete-or-Rollback transaction unless a later task proves a recovery-only hook is safe.
- Do not unconditionally bypass Trainer/save validation.
- Do not use mapped `.data` as executable code space.
- Keep unsupported or unproven runtime behavior behind an explicit experimental build path.
- Label conclusions as static confirmation, structural inference, real-hardware confirmation, or unconfirmed hypothesis.

## Review Focus

- Giant Ghidra export parsing: extractor must stop at the next function marker and never silently merge neighboring functions.
- Address spelling/case variants: extractor must accept `0x002AF034`, `002af034`, and `FUN_002af034` without extracting a wrong function.
- Reference scans: source-record offsets must distinguish serialized `0xAD61C` from runtime body/object-offset variants such as `0xAD624`.
- Recovery-only gating: any future bypass must remain inactive during a normal transaction-free Bank launch.
- Text-tail budget: experimental runtime additions must fail verification rather than spill into `.rodata`/`.data`.

---

### Task 1: Static recovery-function extractor

**Files:**
- Create: `bank/tools/extract_recovery_functions.py`
- Create: `bank/tools/test_extract_recovery_functions.py`
- Modify: `.github/workflows/official-bulk-sync-ci.yml`

**Interfaces:**
- Consumes: `bank/docs/code.bin_all_functions.c`, whose functions are introduced by comments of the form `/* #N @ ADDRESS : FUN_ADDRESS */`.
- Produces: CLI `python bank/tools/extract_recovery_functions.py <decompile> --address ADDRESS...` and a deterministic text report containing exact function bodies plus selected literal/callee references.

- [ ] **Step 1: Write failing parser tests**

Create synthetic decompile text with three functions and assert that requesting the middle address returns only that marker/body, supports hex/function-name spellings, and reports a missing address as a non-zero exit.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python -m unittest bank/tools/test_extract_recovery_functions.py -v
```

Expected: FAIL because `extract_recovery_functions` does not yet exist.

- [ ] **Step 3: Implement the minimal extractor**

Implement pure helpers:

```python
def normalize_address(value: str) -> str: ...
def index_functions(text: str) -> dict[str, tuple[int, int]]: ...
def extract_function(text: str, address: str) -> str: ...
def find_reference_context(text: str, needles: list[str], context_lines: int = 4) -> list[str]: ...
```

CLI default research addresses:

```text
002acbdc 002adc50 002af034 002a93f4 002a8760 002a9118 002ad7bc 002b1cf8
```

Default reference needles:

```text
0xad61c 0xad624 0x34 0x35 FUN_001d5d74 FUN_001d5c28
```

- [ ] **Step 4: Run parser unit tests and verify GREEN**

Run the same unittest command; expected PASS.

- [ ] **Step 5: Add a CI research extraction step**

Extend the existing workflow so pushes to `feature/official-bank-recovery-research` run the existing host/ARM checks plus:

```bash
python bank/tools/extract_recovery_functions.py \
  bank/docs/code.bin_all_functions.c \
  --output /tmp/bank-recovery-functions.txt
```

Upload `/tmp/bank-recovery-functions.txt` as `bank-recovery-static-report`.

- [ ] **Step 6: Commit**

Commit message:

```text
tools(bank): extract recovery state functions from decompile
```

### Task 2: Static recovery-chain evidence report

**Files:**
- Create: `bank/docs/official-bank-recovery-static-report.zh-cn.md`
- Modify: `bank/docs/official-bank-network-failure-trainer-mismatch-recovery.zh-cn.md`

**Interfaces:**
- Consumes: Task 1 extraction artifact/log plus stock state/address table.
- Produces: exact per-state pseudocode summaries, callee/address table, pStatus/applicationId handling, source-game-record read/write references, and a named candidate mismatch decision with confidence level.

- [ ] **Step 1: Run the extractor against the real decompile in CI and retrieve its artifact/log**

Expected: report includes all eight requested functions or explicitly reports each missing address.

- [ ] **Step 2: Trace state 11 backwards and forwards**

Document every conditional controlling transitions to state 17/18/16/error; record structure offsets read from the state/context object and every helper call.

- [ ] **Step 3: Trace source-game trainer records**

Search both serialized/runtime offset forms and identify writers/readers. Do not label a reader as the Trainer mismatch comparator unless its data flow reaches the recovery decision.

- [ ] **Step 4: Trace save-error path**

Map state 7 failure result into state 22/23 and identify whether rollback is requested before or after any game-side save completion signal.

- [ ] **Step 5: Update the main research document**

Promote or reject H1-H4 with explicit evidence and leave unresolved points marked as unresolved rather than guessed.

- [ ] **Step 6: Commit**

Commit message:

```text
docs(bank): map stock recovery and trainer mismatch flow
```

### Task 3: Recovery-decision host model and tests

**Files:**
- Create: `bank/src/official_recovery_policy.h`
- Create: `bank/src/official_recovery_policy.c`
- Create: `bank/src/official_recovery_policy_host_test.c`

**Interfaces:**
- Consumes: exact decision inputs established by Task 2.
- Produces: a pure host-testable classifier only; it does not alter stock runtime by itself.

- [ ] **Step 1: Write failing policy tests**

Tests must include normal no-pending state, exact identity match, known recovery mismatch, genuinely different Trainer/save identity, unsupported/unknown status, and malformed input.

- [ ] **Step 2: Verify RED**

Compile the test before implementation and confirm the missing classifier causes failure.

- [ ] **Step 3: Implement the minimal classifier**

Expose only the fields proven necessary by Task 2. Do not model speculative 0x20 fields or source-summary fields unless the static trace proved they feed the decision.

- [ ] **Step 4: Verify GREEN and full host suite**

Run both recovery-policy and Official Bulk Sync host tests.

- [ ] **Step 5: Commit**

Commit message:

```text
test(bank): model recovery-only trainer mismatch policy
```

### Task 4: Experimental recovery hook, only if Task 2 proves a local gate

**Files:**
- Modify: `bank/src/main_official.s`
- Modify: `bank/src/official_bulk_sync_prod.c` or create a smaller dedicated assembly/C unit if text budget requires it
- Modify: `bank/src/verify_official_bulk_sync.py`
- Modify: `.github/workflows/official-bulk-sync-ci.yml`
- Modify: `bank/docs/official-bank-recovery-static-report.zh-cn.md`

**Interfaces:**
- Consumes: proven recovery-only decision address and Task 3 classifier semantics.
- Produces: an explicit experimental build that bypasses only the identified stale/recovery mismatch branch and then returns to the original stock reconciliation path.

- [ ] **Step 1: Add failing static verifier assertions**

Verifier must reject a patch that touches the recovery decision outside its exact instruction whitelist, changes normal state-16 hook bytes unexpectedly, or exceeds executable-space budget.

- [ ] **Step 2: Verify RED**

Run verifier against a fixture/expected-symbol map lacking the new hook and confirm the new recovery assertions fail for the intended reason.

- [ ] **Step 3: Implement the smallest recovery-only hook**

Requirements:

```text
no global TrainerCheck=true
no normal-flow bypass
no direct Complete/Rollback token fabrication
return to stock state 17/18/23 reconciliation
```

If the current RX tail cannot fit the hook, stop production implementation and document the code-space blocker rather than using `.data`.

- [ ] **Step 4: Verify GREEN**

Run host tests, ARM compile, unexpected-runtime-helper checks, text-budget checks, and patch verifier.

- [ ] **Step 5: Mark runtime status accurately**

Until tested on real hardware against a reproducible interrupted transaction, label the hook `EXPERIMENTAL / STATICALLY VERIFIED ONLY`.

- [ ] **Step 6: Commit**

Commit message:

```text
feat(bank): add experimental recovery-only mismatch hook
```

### Task 5: Final verification and operator guide

**Files:**
- Create: `bank/docs/official-bank-recovery-test-guide.zh-cn.md`
- Modify: `bank/docs/README.zh-cn.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: reproducible real-hardware test matrix and branch documentation.

- [ ] **Step 1: Document safe reproduction points**

Test matrix must distinguish failure before Prepare, during HPP upload, after game save/before Complete, and clean success; where exact network interruption timing cannot be controlled, document the observable transaction state instead of pretending timing is known.

- [ ] **Step 2: Document evidence to capture**

Record Bank error text, selected game/profile, `pStatus/pApplicationId` if instrumented, fresh Bank backup filename, whether stock recovery reaches state 16, and whether a subsequent clean save succeeds.

- [ ] **Step 3: Run full available CI/test suite**

Expected: all existing Official Bulk Sync tests and all new recovery tooling/policy/verifier tests pass.

- [ ] **Step 4: Commit**

Commit message:

```text
docs(bank): add official recovery validation guide
```
