# Official Bank Recovery Fault Injection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic A/B real-device fault-injection patches that freeze Pokémon Bank at three verified transaction boundaries and produce reproducible IPS files plus a device test protocol.

**Architecture:** Keep production A/B recovery logic untouched. Start from the already production-patched `.code`, validate the stock Bank v1.5 base and untouched target instruction, replace exactly one verified ARM instruction with `B .` (`FE FF FF EA`), then generate a final IPS against the original stock `.code`. The same injector is used for A and B; only expected recovery outcomes differ.

**Tech Stack:** Python 3, ARM32 machine-code patching, IPS, existing armips/devkitARM build, GitHub Actions.

**Spec:** `bank/docs/official-bank-recovery-production-status.zh-cn.md`

## Global Constraints

- Stock `.code` must be exactly `0x2AC000` bytes with SHA-256 `2DCE4796F54807CF8A67F1CE6297BF472D969B30ED7A7E8E25C2A6C2BDC40ABF`.
- Production recovery A/B logic must not be changed by fault-injection tooling.
- Fault injection may modify exactly one 4-byte instruction outside the existing production patch surface.
- Verified points are `0x002B1E18`, `0x002B1F4C`, and `0x002B20A0` only.
- Target instruction bytes must still match stock before patching; otherwise fail closed.
- Final IPS must replay from the stock base to the exact fault-injected `.code`.
- Fault builds are test-only and must live on `*-fault-injection` branches.

## Review Focus

- Wrong Bank version/base must be rejected before any output is written.
- A production patch that already modified a target instruction must be rejected rather than overwritten.
- IPS generation must handle all existing production differences plus the one new self-loop.
- A/B expected outcomes must differ at `post-game-save` and `pre-complete` but agree on `post-stage`.
- The device procedure must require removing the fault IPS before the recovery launch and must prohibit restoring/modifying the linked game save between freeze and recovery.

---

### Task 1: Fault injector core and RED/GREEN tests

**Files:**
- Create: `bank/tools/test_build_recovery_fault_patch.py`
- Create: `bank/tools/build_recovery_fault_patch.py`

**Interfaces:**
- Produces: `FAULT_POINTS`, `inject_fault(patched, point)`, `make_ips(base, modified)`, `apply_ips(base, ips)`, and CLI `--variant A|B --base ... --patched ... --out-dir ... --point all|<name>`.
- Fault names: `post-stage`, `post-game-save`, `pre-complete`.

- [ ] **Step 1: Write failing unit tests** covering exact addresses/bytes, one-instruction-only mutation, wrong-target rejection, IPS replay, and A/B expected outcome metadata.
- [ ] **Step 2: Run `python -m unittest bank/tools/test_build_recovery_fault_patch.py -v` and verify failure because the implementation module does not exist.**
- [ ] **Step 3: Implement the minimal strict injector.** Use `FE FF FF EA` for ARM `B .`; validate stock SHA and sizes in CLI; validate target bytes in both stock and production-patched input; emit `.dec.code`, `.ips`, and `.json` manifest per point.
- [ ] **Step 4: Run the unit test again and verify all tests pass.**

### Task 2: Build integration

**Files:**
- Modify: `bank/src/Makefile`

**Interfaces:**
- Consumes: Task 1 CLI.
- Produces: `make fault-matrix` output under `release/fault-injection-<A|B>/00040000000C9B00/`.

- [ ] **Step 1: Add a test assertion that the branch Makefile declares the correct `FAULT_VARIANT`.**
- [ ] **Step 2: Verify the assertion fails before Makefile changes.**
- [ ] **Step 3: Add `FAULT_VARIANT`, `FAULT_RELEASE_ROOT`, and `fault-matrix` target that depends on the verified production IPS and invokes the strict injector with `--point all`.**
- [ ] **Step 4: Re-run tests and verify green.**

### Task 3: CI guard

**Files:**
- Create: `.github/workflows/official-bank-recovery-fault-injection-ci.yml`

**Interfaces:**
- Consumes: Tasks 1-2.
- Produces: automatic host verification on both A/B fault-injection branches.

- [ ] **Step 1: Add CI for Python unit tests and branch/variant consistency.**
- [ ] **Step 2: Confirm the workflow runs on both `feature/official-bank-recovery-a-fault-injection` and `feature/official-bank-recovery-b-fault-injection`.**

### Task 4: Real-device protocol

**Files:**
- Create: `bank/docs/official-bank-recovery-fault-injection-test-guide.zh-cn.md`

**Interfaces:**
- Consumes: fault names and expected outcomes from Task 1.
- Produces: exact test sequence and evidence checklist for a physical 3DS.

- [ ] **Step 1: Document clean-start prerequisites and how to generate all three IPS files.**
- [ ] **Step 2: Document the exact run sequence: install one fault IPS → Bulk save → wait for deterministic freeze → power off → remove fault IPS/restore normal A or B production IPS → relaunch using the same untouched game save.**
- [ ] **Step 3: Record expected results:** A = Rollback for all three points; B = Rollback at `post-stage`, Commit at `post-game-save` and `pre-complete`.
- [ ] **Step 4: Add evidence capture:** before/after Bank snapshot, visible UI result, game-save hash when available, fault manifest, and whether state18 recovered or showed mismatch.

### Task 5: Final verification

- [ ] **Step 1: Run the complete fault-injector unit suite.**
- [ ] **Step 2: Confirm the generated self-loop changes exactly one 4-byte target in a synthetic production image.**
- [ ] **Step 3: Confirm IPS replay exactly reproduces every generated fault image.**
- [ ] **Step 4: Confirm no production A/B source file (`official_recovery_wal_thumb.s`, recovery decision logic) was modified on the fault-injection branches.**
