import struct
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import bank_v15_layout as layout
from bank_v15_image import BankV15Image


def make_image(seed: int) -> BankV15Image:
    raw = bytearray(((i * seed + seed) & 0xFF) for i in range(layout.CURRENT_SIZE))
    struct.pack_into("<HH", raw, layout.VERSION_OFFSET, 2, 100)
    return BankV15Image.from_bytes(bytes(raw))


class BulkApplyV0Tests(unittest.TestCase):
    def test_only_main_box_range_is_copied(self):
        runtime = make_image(7)
        bulk = make_image(13)
        result = runtime.apply_main_boxes_from(bulk).to_bytes()
        runtime_raw = runtime.to_bytes()
        bulk_raw = bulk.to_bytes()

        self.assertEqual(
            result[:layout.BANK_BOXES_START],
            runtime_raw[:layout.BANK_BOXES_START],
        )
        self.assertEqual(
            result[layout.BANK_BOXES_START:layout.TRANSFER_BOX_START],
            bulk_raw[layout.BANK_BOXES_START:layout.TRANSFER_BOX_START],
        )
        self.assertEqual(
            result[layout.TRANSFER_BOX_START:],
            runtime_raw[layout.TRANSFER_BOX_START:],
        )

    def test_current_only_metadata_is_preserved_from_runtime(self):
        runtime = make_image(5)
        bulk = make_image(19)
        result = runtime.apply_main_boxes_from(bulk).to_bytes()
        runtime_raw = runtime.to_bytes()

        preserved_ranges = [
            (0, layout.BANK_BOXES_START),
            (layout.TRANSFER_BOX_START, layout.BANK_TAGS_START),
            (layout.BANK_TAGS_START, layout.TRANSFER_TAGS_START),
            (layout.SOURCE_SUMMARIES_START, layout.POKEDEX_AGGREGATE_START),
            (layout.POKEDEX_AGGREGATE_START, layout.COUNTERS_START),
            (layout.COUNTERS_START, layout.SOURCE_SOFTWARE_START),
            (layout.SOURCE_SOFTWARE_START, layout.TIMESTAMPS_START),
            (layout.TIMESTAMPS_START, layout.TAIL_START),
            (layout.TAIL_START, layout.CURRENT_SIZE),
        ]
        for start, end in preserved_ranges:
            with self.subTest(start=hex(start), end=hex(end)):
                self.assertEqual(result[start:end], runtime_raw[start:end])

    def test_self_apply_is_byte_identical(self):
        runtime = make_image(11)
        self.assertEqual(
            runtime.apply_main_boxes_from(runtime).to_bytes(),
            runtime.to_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
