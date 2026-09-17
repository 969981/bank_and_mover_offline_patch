import contextlib
import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import bank_v15_layout as layout
import bankbulk


def make_current_image(fill=False, seed=17):
    if fill:
        data = bytearray((i * seed + 3) & 0xFF for i in range(layout.CURRENT_SIZE))
    else:
        data = bytearray(layout.CURRENT_SIZE)
    struct.pack_into("<HH", data, layout.VERSION_OFFSET, 2, 100)
    return bytes(data)


class BankBulkCliTests(unittest.TestCase):
    def test_export_pkhex_and_import_back_preserve_non_box_regions(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            full = td / "bankdata.bin"
            view = td / "view.bin"
            edited = td / "edited.bin"
            output = td / "bulk_import.bin"
            original = make_current_image(fill=True)
            full.write_bytes(original)

            self.assertEqual(bankbulk.main(["export-pkhex", str(full), "-o", str(view)]), 0)
            self.assertEqual(view.stat().st_size, layout.LEGACY_SIZE)
            mutable = bytearray(view.read_bytes())
            mutable[0] ^= 0x11
            mutable[layout.BANK_BOXES_START + 5] ^= 0x22
            mutable[layout.TRANSFER_BOX_START] ^= 0x33
            mutable[layout.BANK_TAGS_START] ^= 0x44
            edited.write_bytes(mutable)

            self.assertEqual(bankbulk.main(["import-pkhex", str(full), str(edited), "-o", str(output)]), 0)
            merged = output.read_bytes()
            self.assertEqual(len(merged), layout.CURRENT_SIZE)
            self.assertEqual(merged[:layout.BANK_BOXES_START], original[:layout.BANK_BOXES_START])
            self.assertNotEqual(merged[layout.BANK_BOXES_START + 5], original[layout.BANK_BOXES_START + 5])
            self.assertEqual(merged[layout.TRANSFER_BOX_START:], original[layout.TRANSFER_BOX_START:])

    def test_build_is_validated_byte_identical_copy(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "src.bin"
            dst = td / "dst.bin"
            raw = make_current_image(fill=True)
            src.write_bytes(raw)
            self.assertEqual(bankbulk.main(["build", str(src), "-o", str(dst)]), 0)
            self.assertEqual(dst.read_bytes(), raw)

    def test_apply_v0_uses_bulk_boxes_and_runtime_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            runtime_path = td / "runtime.bin"
            bulk_path = td / "bulk_import.bin"
            output_path = td / "expected.bin"
            runtime = make_current_image(fill=True, seed=7)
            bulk = make_current_image(fill=True, seed=23)
            runtime_path.write_bytes(runtime)
            bulk_path.write_bytes(bulk)

            self.assertEqual(
                bankbulk.main([
                    "apply-v0", str(runtime_path), str(bulk_path),
                    "-o", str(output_path),
                ]),
                0,
            )
            result = output_path.read_bytes()
            self.assertEqual(result[:layout.BANK_BOXES_START], runtime[:layout.BANK_BOXES_START])
            self.assertEqual(
                result[layout.BANK_BOXES_START:layout.TRANSFER_BOX_START],
                bulk[layout.BANK_BOXES_START:layout.TRANSFER_BOX_START],
            )
            self.assertEqual(result[layout.TRANSFER_BOX_START:], runtime[layout.TRANSFER_BOX_START:])

    def test_validate_and_inspect(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bank.bin"
            path.write_bytes(make_current_image())
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(bankbulk.main(["validate", str(path)]), 0)
                self.assertEqual(bankbulk.main(["inspect", str(path)]), 0)
            text = out.getvalue()
            self.assertIn("valid", text.lower())
            self.assertIn("0xBB518", text)
            self.assertIn("100", text)

    def test_invalid_current_image_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.bin"
            path.write_bytes(b"x" * 10)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertNotEqual(bankbulk.main(["validate", str(path)]), 0)

    def test_wrong_size_pkhex_view_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            full = td / "bank.bin"
            view = td / "view.bin"
            out = td / "out.bin"
            full.write_bytes(make_current_image())
            view.write_bytes(b"\0" * (layout.LEGACY_SIZE - 1))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertNotEqual(bankbulk.main(["import-pkhex", str(full), str(view), "-o", str(out)]), 0)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
