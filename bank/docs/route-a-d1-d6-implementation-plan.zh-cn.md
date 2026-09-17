# Pokémon Bank Route A D1–D6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 Route A 的 PC 镜像模型、PKHeX 兼容视图、安全回灌、`bulk_import.bin` 构建、3DS Offline 白名单应用与离线回归闭环，并为 D6 Official Mode 保留接口但不启用服务器写入。

**Architecture:** PC 端把完整 `0xBB518` current Bank image 作为唯一主模板；PKHeX 只得到 legacy-size `0xACA48` view，回灌时仅复制主 100 Box `0x17C..0xAAF14`。3DS 端读取完整 `bulk_import.bin`，校验后只对白名单区域执行 Apply；R4/R5/R6 未确认区域默认 preserve runtime。Offline Mode 继续复用现有本地 stage/commit/rollback。

**Tech Stack:** Python 3 标准库、`unittest`、C11 freestanding ARMv6K、armips、现有 Pokémon Bank v1.5 patch infrastructure。

**Spec:** `bank/docs/route-a-bulk-import-design.zh-cn.md`

## Global Constraints

- current Bank image 必须严格为 `0xBB518` bytes。
- PKHeX compatibility view 必须严格为 `0xACA48` bytes。
- current header 必须满足 `u16[0x15C] == 2` 与 `u16[0x15E] == 100`。
- PKHeX import-back 只允许覆盖 `0x00017C..0x0AAF14`，不得覆盖 Header、Transfer Box 或 `0xACA44..0xACA47` overlap。
- source summaries、opaque/NKZT、counters、tail 在 R4/R5/R6 未证明前一律 preserve runtime。
- Official/NEX/HPP 上传不属于 D1–D5；D6 第一轮仅允许 1 Pokémon controlled round-trip。
- 所有 Python 工具默认只读源文件，输出必须显式指定。
- 不把 `tag/source/timestamp` 当 occupancy flag。

---

### Task 1: BankV15Image model + PKHeX view primitives

**Files:**
- Create: `ViewerForBankdata/tools/bank_v15_image.py`
- Modify: `ViewerForBankdata/tools/bank_v15_layout.py`
- Create: `ViewerForBankdata/tests/test_bank_v15_image.py`

**Interfaces:**
- Consumes: `bank_v15_layout.validate_current`, region constants。
- Produces:
  - `class BankV15Image`
  - `BankV15Image.from_bytes(data: bytes) -> BankV15Image`
  - `BankV15Image.to_bytes() -> bytes`
  - `BankV15Image.export_pkhex_view() -> bytes`
  - `BankV15Image.import_pkhex_view(view: bytes) -> BankV15Image`
  - `BankV15Image.main_box_bytes() -> bytes`
  - `PKHEX_VIEW_SIZE = 0xACA48`
  - `PKHEX_IMPORT_START = 0x17C`
  - `PKHEX_IMPORT_END = 0xAAF14`

- [ ] **Step 1: Write failing round-trip and PKHeX range tests**

```python
class BankV15ImageTests(unittest.TestCase):
    def test_parse_serialize_is_byte_identical(self):
        raw = make_current_image()
        self.assertEqual(BankV15Image.from_bytes(raw).to_bytes(), raw)

    def test_export_pkhex_view_is_exact_legacy_size(self):
        raw = make_current_image(fill=True)
        view = BankV15Image.from_bytes(raw).export_pkhex_view()
        self.assertEqual(len(view), 0xACA48)
        self.assertEqual(view, raw[:0xACA48])

    def test_import_pkhex_view_only_replaces_main_boxes(self):
        raw = bytearray(make_current_image(fill=True))
        view = bytearray(raw[:0xACA48])
        view[0] ^= 0xFF
        view[0x17C] ^= 0x7F
        view[0xAAF14] ^= 0x55
        view[0xACA44] ^= 0x33
        merged = BankV15Image.from_bytes(bytes(raw)).import_pkhex_view(bytes(view)).to_bytes()
        self.assertEqual(merged[0], raw[0])
        self.assertNotEqual(merged[0x17C], raw[0x17C])
        self.assertEqual(merged[0xAAF14], raw[0xAAF14])
        self.assertEqual(merged[0xACA44], raw[0xACA44])
```

- [ ] **Step 2: Run tests and verify failure before implementation**

Run: `python -m unittest ViewerForBankdata.tests.test_bank_v15_image -v`
Expected: FAIL because `bank_v15_image` does not exist.

- [ ] **Step 3: Implement minimal immutable image wrapper**

Implementation rules:

```python
@dataclass(frozen=True)
class BankV15Image:
    _data: bytes

    @classmethod
    def from_bytes(cls, data: bytes):
        errors = layout.validate_current(data)
        if errors:
            raise ValueError("; ".join(errors))
        return cls(bytes(data))

    def to_bytes(self) -> bytes:
        return self._data

    def export_pkhex_view(self) -> bytes:
        return self._data[:layout.LEGACY_SIZE]

    def import_pkhex_view(self, view: bytes):
        if len(view) != layout.LEGACY_SIZE:
            raise ValueError(...)
        merged = bytearray(self._data)
        merged[layout.BANK_BOXES_START:layout.TRANSFER_BOX_START] = \
            view[layout.BANK_BOXES_START:layout.TRANSFER_BOX_START]
        return type(self)(bytes(merged))
```

- [ ] **Step 4: Run Task 1 tests to green**
- [ ] **Step 5: Run existing D0 tests for regression**
- [ ] **Step 6: Commit Task 1**

---

### Task 2: bankbulk CLI — validate / inspect / export-pkhex / import-pkhex / build

**Files:**
- Create: `ViewerForBankdata/tools/bankbulk.py`
- Create: `ViewerForBankdata/tests/test_bankbulk.py`
- Modify: `ViewerForBankdata/tools/README.zh-cn.md`
- Modify: `ViewerForBankdata/tools/README.md`

**Interfaces:**
- Consumes: `BankV15Image`。
- Produces CLI:

```text
python bankbulk.py validate FULL.bin
python bankbulk.py inspect FULL.bin
python bankbulk.py export-pkhex FULL.bin -o VIEW.bin
python bankbulk.py import-pkhex FULL_TEMPLATE.bin EDITED_VIEW.bin -o bulk_import.bin
python bankbulk.py build FULL_TEMPLATE.bin -o bulk_import.bin
```

- [ ] **Step 1: Write failing CLI tests**

Required assertions:

```python
export-pkhex output size == 0xACA48
import-pkhex output size == 0xBB518
import-pkhex preserves bytes before 0x17C
import-pkhex preserves bytes from 0xAAF14 onward
build is byte-identical copy after validation
invalid current image exits nonzero
wrong-size PKHeX view exits nonzero
```

- [ ] **Step 2: Run tests and verify failure**
- [ ] **Step 3: Implement argparse subcommands**
- [ ] **Step 4: Run tests to green**
- [ ] **Step 5: Add README examples including PowerShell commands**
- [ ] **Step 6: Commit Task 2**

---

### Task 3: R4/R5/R6 research classifier and baseline report

**Files:**
- Create: `ViewerForBankdata/tools/inspect_bank_metadata.py`
- Create: `ViewerForBankdata/tests/test_inspect_bank_metadata.py`
- Create: `bank/docs/r4-r6-metadata-strategy.zh-cn.md`

**Interfaces:**
- Produces:
  - `inspect_metadata(data: bytes) -> dict`
  - summary-entry nonzero ranges/counts
  - opaque/NKZT magic + nonzero ranges
  - counters as raw bytes + `<HH>` + `<I>` views
  - tail nonzero ranges
  - policy table with `UNKNOWN_PRESERVE` default

- [ ] **Step 1: Add synthetic classification tests**
- [ ] **Step 2: Run tests and verify failure**
- [ ] **Step 3: Implement raw classifier without speculative names**
- [ ] **Step 4: Run on uploaded baseline `bankdata.bin` and capture exact statistics**
- [ ] **Step 5: Perform static reference scan against existing Ghidra/code-analysis material and document confirmed/inferred/unknown separately**
- [ ] **Step 6: Write `r4-r6-metadata-strategy.zh-cn.md` with final V0 policy**
- [ ] **Step 7: Commit Task 3**

---

### Task 4: Metadata policy + host-side ApplyBulkImport reference model

**Files:**
- Create: `ViewerForBankdata/tools/bulk_apply.py`
- Create: `ViewerForBankdata/tests/test_bulk_apply.py`

**Interfaces:**
- Produces:
  - `enum/str policies` for each region
  - `apply_bulk_import(runtime: bytes, bulk: bytes, *, copy_slot_metadata=False) -> bytes`
  - V0 default copies only main 100 Box range
  - optional experimental per-slot metadata copy can be enabled only in Offline test tooling

- [ ] **Step 1: Write failing whitelist tests**

Default apply must:

```text
COPY 0x17C..0xAAF14
PRESERVE header
PRESERVE transfer box
PRESERVE bank tags
PRESERVE summaries
PRESERVE NKZT
PRESERVE counters
PRESERVE source software
PRESERVE timestamps
PRESERVE tail
```

Experimental flag may copy `bank_tags`, `source_software`, `timestamps` slotwise, but must not be default.

- [ ] **Step 2: Verify failure**
- [ ] **Step 3: Implement reference apply**
- [ ] **Step 4: Add changed-range assertions using `diff_bank_file`**
- [ ] **Step 5: Run full Python suite**
- [ ] **Step 6: Commit Task 4**

---

### Task 5: 3DS pure-C Bulk Apply core

**Files:**
- Create: `bank/src/bulk_import.h`
- Create: `bank/src/bulk_import.c`
- Create: `bank/src/bulk_import_host_test.c`

**Interfaces:**

```c
#define BANK_V15_SIZE 0xBB518u
#define BANK_MAIN_BOX_START 0x17Cu
#define BANK_MAIN_BOX_END 0xAAF14u

int BankBulk_Validate(const unsigned char *body, unsigned int size);
void BankBulk_ApplyMainBoxes(unsigned char *runtimeBody, const unsigned char *bulkBody);
```

Default C core does not copy tag/source/timestamp or R4/R5/R6 regions.

- [ ] **Step 1: Write host C test first**

Test fills runtime with `0x11`, bulk with `0x22`, fixes each image's version/count, applies, then asserts:

```text
runtime[0x000000] remains 0x11
runtime[0x00017C] becomes 0x22
runtime[0x0AAF13] becomes 0x22
runtime[0x0AAF14] remains 0x11
runtime[0x0ACA44] remains 0x11
runtime[0x0BB517] remains 0x11
```

- [ ] **Step 2: Compile test before implementation and verify link/compile failure**
- [ ] **Step 3: Implement C core with simple loops, no libc dependency**
- [ ] **Step 4: Compile/run host test to green**
- [ ] **Step 5: Commit Task 5**

---

### Task 6: Integrate bulk_import.bin loader into Offline patch

**Files:**
- Modify: `bank/src/patch.c`
- Modify: `bank/src/Makefile`
- Modify: `bank/src/main.s`
- Modify: `bank/src/verify_patch.py`
- Modify: `bank/src/README.zh-cn.md`
- Modify: `bank/src/README.md`

**Interfaces:**
- New SD path: `/3ds/Bank/bulk_import.bin`
- New function in `patch.c`:

```c
int OfflinePatch_ApplyBulkImportIfPresent(u8 *object);
```

Behavior:

```text
missing bulk_import.bin -> success/no-op
wrong size/header -> fail closed, do not alter BankObject
valid file -> BankBulk_ApplyMainBoxes(object+8, bulkBuffer)
```

Because allocating another `0xBB518` stack/static buffer is unacceptable, loader must stream/copy only the required main-box range or reuse a controlled scratch allocation. V0 should prefer streaming reads directly into the runtime main-box range after validation via small header read + file-size check, with a pre-apply backup snapshot already represented by `bankdata.bin` on SD.

- [ ] **Step 1: Add verification expectations before hook/code change**
- [ ] **Step 2: Extend Makefile to build/import `bulk_import.o`**
- [ ] **Step 3: Add path + safe read/validate/apply wrapper**
- [ ] **Step 4: Call wrapper only after `OfflinePatch_LoadBankData` succeeds and before resuming stock substate 6**
- [ ] **Step 5: Missing file remains stock Offline behavior**
- [ ] **Step 6: Invalid file returns error state rather than partially applying**
- [ ] **Step 7: Build/verify if ARM toolchain and base ROM are available; otherwise run host C test and static verifier additions, explicitly mark binary build as environment-blocked**
- [ ] **Step 8: Commit Task 6**

---

### Task 7: D5 Offline regression suite + real baseline conversion

**Files:**
- Create: `ViewerForBankdata/tests/test_route_a_regression.py`
- Modify: `bank/docs/route-a-bulk-import-design.zh-cn.md`

**Interfaces:**
- Uses the uploaded baseline `bankdata.bin` only as a local test fixture; do not commit user Bank data.

- [ ] **Step 1: Add synthetic 1-slot / 1-box / 10-box / 100-box tests**
- [ ] **Step 2: Add PKHeX export→mutate-main-box→import test**
- [ ] **Step 3: Prove import preserves `0xAAF14..0xBB518` exactly**
- [ ] **Step 4: Run `bankbulk export-pkhex` on real baseline and compare SHA/size with previously generated compatibility view**
- [ ] **Step 5: Run `bankbulk import-pkhex` with an unmodified view and prove final `0xBB518` output is byte-identical to baseline**
- [ ] **Step 6: Run complete Python + host-C suite**
- [ ] **Step 7: Document 3DS manual regression checklist for save/restart/reload**
- [ ] **Step 8: Commit Task 7**

---

### Task 8: D6 interface reservation only

**Files:**
- Create: `bank/docs/d6-official-roundtrip-test-plan.zh-cn.md`

**Interfaces:**
- No server write code in this task.
- Documents exact state-16 insertion point, one-Pokémon test fixture, `server_before/bulk/runtime_expected/server_after` artifacts, and rollback/stop conditions.

- [ ] **Step 1: Document hook boundary after full BankObject load and before Box UI**
- [ ] **Step 2: Define 1-Pokémon whitelist and expected binary diff**
- [ ] **Step 3: Define abort conditions: unexpected summary/NKZT/counter/tail mutation, HTTP conflict, transaction recovery state**
- [ ] **Step 4: Commit Task 8**

---

### Task 9: Final verification

- [ ] Run: `python -m unittest discover -s ViewerForBankdata/tests -v`
- [ ] Run host C Bulk Apply test with system compiler.
- [ ] Run real-baseline `validate`, `export-pkhex`, unmodified `import-pkhex`, and byte comparison.
- [ ] Confirm no user `bankdata.bin` fixture is committed.
- [ ] Compare branch changed files against pre-implementation commit and verify only planned paths changed.
- [ ] If devkitARM/base ROM are unavailable, state clearly that 3DS binary build verification is pending environment availability; do not claim IPS build success.