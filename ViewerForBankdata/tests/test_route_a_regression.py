import struct
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import bank_v15_layout as layout
from bank_v15_image import BankV15Image


def make_base(fill=0x11):
    raw = bytearray([fill] * layout.CURRENT_SIZE)
    struct.pack_into("<HH", raw, layout.VERSION_OFFSET, 2, 100)
    return raw


def apply(runtime, bulk):
    return BankV15Image.from_bytes(bytes(runtime)).apply_main_boxes_from(
        BankV15Image.from_bytes(bytes(bulk))
    ).to_bytes()


class RouteARegressionTests(unittest.TestCase):
    def assert_outside_main_boxes_preserved(self, before, after):
        self.assertEqual(after[:layout.BANK_BOXES_START], before[:layout.BANK_BOXES_START])
        self.assertEqual(after[layout.TRANSFER_BOX_START:], before[layout.TRANSFER_BOX_START:])

    def test_one_slot_change(self):
        runtime = make_base()
        bulk = bytearray(runtime)
        slot = layout.slot_offsets(59, 0)
        bulk[slot.pokemon + 10] ^= 0x5A
        result = apply(runtime, bulk)
        self.assertEqual(result[slot.pokemon + 10], bulk[slot.pokemon + 10])
        self.assert_outside_main_boxes_preserved(runtime, result)

    def test_one_box_change(self):
        runtime = make_base()
        bulk = bytearray(runtime)
        start = layout.BANK_BOXES_START + 20 * layout.BOX_STRIDE
        end = start + layout.BOX_STRIDE
        bulk[start:end] = bytes([0x22]) * layout.BOX_STRIDE
        result = apply(runtime, bulk)
        self.assertEqual(result[start:end], bulk[start:end])
        self.assert_outside_main_boxes_preserved(runtime, result)

    def test_ten_box_change(self):
        runtime = make_base()
        bulk = bytearray(runtime)
        start = layout.BANK_BOXES_START + 30 * layout.BOX_STRIDE
        end = start + 10 * layout.BOX_STRIDE
        bulk[start:end] = bytes([0x33]) * (end - start)
        result = apply(runtime, bulk)
        self.assertEqual(result[start:end], bulk[start:end])
        self.assert_outside_main_boxes_preserved(runtime, result)

    def test_all_100_boxes_change(self):
        runtime = make_base()
        bulk = bytearray(runtime)
        bulk[layout.BANK_BOXES_START:layout.TRANSFER_BOX_START] = bytes([0x44]) * (
            layout.TRANSFER_BOX_START - layout.BANK_BOXES_START
        )
        result = apply(runtime, bulk)
        self.assertEqual(
            result[layout.BANK_BOXES_START:layout.TRANSFER_BOX_START],
            bulk[layout.BANK_BOXES_START:layout.TRANSFER_BOX_START],
        )
        self.assert_outside_main_boxes_preserved(runtime, result)

    def test_pkhex_unchanged_view_roundtrip_is_identical(self):
        runtime = make_base()
        image = BankV15Image.from_bytes(bytes(runtime))
        restored = image.import_pkhex_view(image.export_pkhex_view())
        self.assertEqual(restored.to_bytes(), bytes(runtime))


if __name__ == "__main__":
    unittest.main()
