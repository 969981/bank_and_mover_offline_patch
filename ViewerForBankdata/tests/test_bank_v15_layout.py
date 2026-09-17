import struct
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import bank_v15_layout as layout


class BankV15LayoutTests(unittest.TestCase):
    def test_regions_are_contiguous_and_end_at_current_size(self):
        expected = [
            ("header", 0x000000, 0x00017C),
            ("bank_boxes", 0x00017C, 0x0AAF14),
            ("transfer_box", 0x0AAF14, 0x0ACA44),
            ("bank_tags", 0x0ACA44, 0x0AD5FC),
            ("transfer_tags", 0x0AD5FC, 0x0AD61A),
            ("alignment", 0x0AD61A, 0x0AD61C),
            ("source_summaries", 0x0AD61C, 0x0AD83C),
            ("pokedex_aggregate", 0x0AD83C, 0x0B4A9C),
            ("counters", 0x0B4A9C, 0x0B4AA0),
            ("source_software", 0x0B4AA0, 0x0B5658),
            ("timestamps", 0x0B5658, 0x0BB418),
            ("tail", 0x0BB418, 0x0BB518),
        ]
        self.assertEqual([(r.name, r.start, r.end) for r in layout.REGIONS], expected)
        for left, right in zip(layout.REGIONS, layout.REGIONS[1:]):
            self.assertEqual(left.end, right.start)
        self.assertEqual(layout.REGIONS[-1].end, layout.CURRENT_SIZE)

    def test_legacy_copy_overlaps_first_four_current_tag_bytes(self):
        self.assertEqual(layout.LEGACY_OVERLAP_START, layout.BANK_TAGS_START)
        self.assertEqual(layout.LEGACY_OVERLAP_END, layout.LEGACY_SIZE)
        self.assertEqual(layout.LEGACY_OVERLAP_SIZE, 4)
        self.assertEqual(layout.CURRENT_ONLY_START, layout.LEGACY_SIZE)

    def test_first_and_last_slot_offsets_share_one_linear_index(self):
        first = layout.slot_offsets(0, 0)
        self.assertEqual(first.index, 0)
        self.assertEqual(first.pokemon, 0x17C)
        self.assertEqual(first.tag, 0xACA44)
        self.assertEqual(first.source_software, 0xB4AA0)
        self.assertEqual(first.timestamp, 0xB5658)

        last = layout.slot_offsets(99, 29)
        self.assertEqual(last.index, 2999)
        self.assertEqual(last.pokemon, 0x17C + 99 * 0x1B56 + 29 * 0xE8)
        self.assertEqual(last.tag, 0xACA44 + 2999)
        self.assertEqual(last.source_software, 0xB4AA0 + 2999)
        self.assertEqual(last.timestamp, 0xB5658 + 2999 * 8)
        self.assertEqual(last.timestamp + 8, 0xBB418)

    def test_slot_index_rejects_out_of_range_coordinates(self):
        for box, slot in [(-1, 0), (100, 0), (0, -1), (0, 30)]:
            with self.subTest(box=box, slot=slot):
                with self.assertRaises(ValueError):
                    layout.slot_index(box, slot)

    def test_region_for_offset_distinguishes_slot_payload_and_box_metadata(self):
        self.assertEqual(layout.region_for_offset(0x17C), "bank_slot_payload")
        self.assertEqual(layout.region_for_offset(0x17C + 30 * 0xE8), "box_metadata")
        self.assertEqual(layout.region_for_offset(0xAAF14), "transfer_box")
        self.assertEqual(layout.region_for_offset(0xACA44), "bank_tags")
        self.assertEqual(layout.region_for_offset(0xBB418), "tail")
        with self.assertRaises(ValueError):
            layout.region_for_offset(layout.CURRENT_SIZE)

    def test_validate_current_checks_length_version_and_box_count(self):
        data = bytearray(layout.CURRENT_SIZE)
        struct.pack_into("<HH", data, layout.VERSION_OFFSET, 2, 100)
        self.assertEqual(layout.validate_current(data), [])

        bad_version = bytearray(data)
        struct.pack_into("<H", bad_version, layout.VERSION_OFFSET, 1)
        self.assertIn("version", " ".join(layout.validate_current(bad_version)).lower())

        bad_count = bytearray(data)
        struct.pack_into("<H", bad_count, layout.BOX_COUNT_OFFSET, 99)
        self.assertIn("box", " ".join(layout.validate_current(bad_count)).lower())

        self.assertIn("size", " ".join(layout.validate_current(data[:-1])).lower())


if __name__ == "__main__":
    unittest.main()
