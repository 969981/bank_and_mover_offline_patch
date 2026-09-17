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
from bank_v15_image import BankV15Image


def make_image(seed: int) -> bytes:
    raw = bytearray(((i * seed + seed) & 0xFF) for i in range(layout.CURRENT_SIZE))
    struct.pack_into("<HH", raw, layout.VERSION_OFFSET, 2, 100)
    return bytes(raw)


class VerifyV0Tests(unittest.TestCase):
    def test_exact_expected_image_passes_default_and_strict(self):
        runtime = make_image(5)
        bulk = make_image(7)
        expected = BankV15Image.from_bytes(runtime).apply_main_boxes_from(
            BankV15Image.from_bytes(bulk)
        ).to_bytes()
        result = bankbulk.verify_v0(runtime, bulk, expected)
        self.assertTrue(result["main_boxes_match_expected"])
        self.assertTrue(result["strict_byte_match_expected"])
        self.assertEqual(result["changed_byte_count_vs_expected"], 0)

    def test_outside_metadata_change_passes_default_but_not_strict(self):
        runtime = make_image(5)
        bulk = make_image(7)
        saved = bytearray(
            BankV15Image.from_bytes(runtime).apply_main_boxes_from(
                BankV15Image.from_bytes(bulk)
            ).to_bytes()
        )
        saved[layout.TAIL_START + 9] ^= 0x55
        result = bankbulk.verify_v0(runtime, bulk, bytes(saved))
        self.assertTrue(result["main_boxes_match_expected"])
        self.assertFalse(result["strict_byte_match_expected"])
        self.assertIn("tail", result["stock_or_runtime_metadata_changes"])
        self.assertEqual(result["main_box_mismatch_regions"], {})

    def test_main_box_mismatch_fails(self):
        runtime = make_image(5)
        bulk = make_image(7)
        saved = bytearray(
            BankV15Image.from_bytes(runtime).apply_main_boxes_from(
                BankV15Image.from_bytes(bulk)
            ).to_bytes()
        )
        saved[layout.BANK_BOXES_START + 3] ^= 0x11
        result = bankbulk.verify_v0(runtime, bulk, bytes(saved))
        self.assertFalse(result["main_boxes_match_expected"])
        self.assertIn("bank_slot_payload", result["main_box_mismatch_regions"])

    def test_cli_exit_codes_distinguish_default_and_strict(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            runtime = make_image(5)
            bulk = make_image(7)
            saved = bytearray(
                BankV15Image.from_bytes(runtime).apply_main_boxes_from(
                    BankV15Image.from_bytes(bulk)
                ).to_bytes()
            )
            saved[layout.TAIL_START] ^= 1
            rp, bp, sp = td / "runtime.bin", td / "bulk.bin", td / "saved.bin"
            jp = td / "verify.json"
            rp.write_bytes(runtime)
            bp.write_bytes(bulk)
            sp.write_bytes(saved)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    bankbulk.main([
                        "verify-v0", str(rp), str(bp), str(sp), "--json", str(jp)
                    ]),
                    0,
                )
                self.assertEqual(
                    bankbulk.main([
                        "verify-v0", str(rp), str(bp), str(sp), "--strict"
                    ]),
                    3,
                )
            self.assertTrue(jp.exists())


if __name__ == "__main__":
    unittest.main()
