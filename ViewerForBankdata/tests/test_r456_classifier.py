import struct
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import bank_v15_layout as layout
import r456_classifier


def make_image():
    data = bytearray(layout.CURRENT_SIZE)
    struct.pack_into("<HH", data, layout.VERSION_OFFSET, 2, 100)
    return data


class R456ClassifierTests(unittest.TestCase):
    def test_empty_regions_are_reported_as_zero(self):
        result = r456_classifier.classify(bytes(make_image()))
        self.assertEqual(result["source_summaries"]["nonzero_bytes"], 0)
        self.assertEqual(result["tail"]["nonzero_bytes"], 0)

    def test_summary_entries_are_split_by_0x44(self):
        data = make_image()
        data[layout.SOURCE_SUMMARIES_START + 0x44 + 3] = 9
        result = r456_classifier.classify(bytes(data))
        self.assertEqual(result["source_summaries"]["entries"][1]["nonzero_bytes"], 1)

    def test_opaque_block_magic_and_ranges_are_raw(self):
        data = make_image()
        data[layout.POKEDEX_AGGREGATE_START:layout.POKEDEX_AGGREGATE_START + 4] = b"NKZT"
        data[layout.POKEDEX_AGGREGATE_START + 10] = 1
        result = r456_classifier.classify(bytes(data))
        self.assertEqual(result["opaque_7260"]["magic_ascii"], "NKZT")
        self.assertGreaterEqual(result["opaque_7260"]["nonzero_bytes"], 5)

    def test_counter_views_include_u16_and_u32(self):
        data = make_image()
        struct.pack_into("<HH", data, layout.COUNTERS_START, 60, 2)
        result = r456_classifier.classify(bytes(data))
        self.assertEqual(result["counters"]["u16_le"], [60, 2])
        self.assertEqual(result["counters"]["u32_le"], (2 << 16) | 60)

    def test_tail_nonzero_ranges_are_coalesced(self):
        data = make_image()
        data[layout.TAIL_START + 2:layout.TAIL_START + 5] = b"ABC"
        result = r456_classifier.classify(bytes(data))
        self.assertEqual(result["tail"]["ranges"][0]["relative_start"], 2)
        self.assertEqual(result["tail"]["ranges"][0]["length"], 3)


if __name__ == "__main__":
    unittest.main()
