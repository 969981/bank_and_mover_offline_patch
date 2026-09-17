import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import bank_v15_layout as layout
import diff_bank_file


def make_image():
    data = bytearray(layout.CURRENT_SIZE)
    struct.pack_into("<HH", data, layout.VERSION_OFFSET, 2, 100)
    return data


class DiffBankFileTests(unittest.TestCase):
    def test_pokemon_byte_change_is_attributed_to_correct_slot(self):
        before = make_image()
        after = bytearray(before)
        off = layout.slot_offsets(12, 7)
        after[off.pokemon + 10] = 0x5A

        result = diff_bank_file.compare_bank_images(bytes(before), bytes(after))

        self.assertEqual(result["changed_byte_count"], 1)
        self.assertEqual(len(result["changed_slots"]), 1)
        slot = result["changed_slots"][0]
        self.assertEqual((slot["box"], slot["slot"], slot["index"]), (12, 7, 367))
        self.assertTrue(slot["pokemon_changed"])
        self.assertNotIn("tag", slot)
        self.assertEqual(result["regions"]["bank_slot_payload"]["changed_bytes"], 1)

    def test_parallel_metadata_changes_are_grouped_with_same_slot(self):
        before = make_image()
        after = bytearray(before)
        off = layout.slot_offsets(2, 3)
        after[off.tag] = 7
        after[off.source_software] = 4
        struct.pack_into("<Q", after, off.timestamp, 0x1122334455667788)

        result = diff_bank_file.compare_bank_images(bytes(before), bytes(after))
        self.assertEqual(len(result["changed_slots"]), 1)
        slot = result["changed_slots"][0]
        self.assertEqual(slot["index"], 63)
        self.assertEqual(slot["tag"], {"before": 0, "after": 7})
        self.assertEqual(slot["source_software"], {"before": 0, "after": 4})
        self.assertEqual(slot["timestamp"], {"before": 0, "after": 0x1122334455667788})
        self.assertFalse(slot["pokemon_changed"])

    def test_non_slot_regions_are_reported_without_creating_fake_slots(self):
        before = make_image()
        after = bytearray(before)
        after[layout.POKEDEX_AGGREGATE_START + 5] = 1
        after[layout.TAIL_START + 9] = 2

        result = diff_bank_file.compare_bank_images(bytes(before), bytes(after))
        self.assertEqual(result["changed_slots"], [])
        self.assertEqual(result["regions"]["pokedex_aggregate"]["changed_bytes"], 1)
        self.assertEqual(result["regions"]["tail"]["changed_bytes"], 1)

    def test_contiguous_region_changes_are_coalesced_into_one_range(self):
        before = make_image()
        after = bytearray(before)
        start = layout.SOURCE_SUMMARIES_START + 4
        after[start:start + 4] = b"ABCD"

        result = diff_bank_file.compare_bank_images(bytes(before), bytes(after))
        ranges = result["regions"]["source_summaries"]["ranges"]
        self.assertEqual(ranges, [{"start": start, "end": start + 4, "length": 4}])

    def test_compare_rejects_wrong_sized_images(self):
        good = bytes(make_image())
        with self.assertRaises(ValueError):
            diff_bank_file.compare_bank_images(good[:-1], good)
        with self.assertRaises(ValueError):
            diff_bank_file.compare_bank_images(good, good[:-1])

    def test_cli_writes_json_report(self):
        before = make_image()
        after = bytearray(before)
        off = layout.slot_offsets(0, 0)
        after[off.tag] = 6

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            before_path = td / "before.bin"
            after_path = td / "after.bin"
            json_path = td / "diff.json"
            before_path.write_bytes(before)
            after_path.write_bytes(after)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = diff_bank_file.main([
                    str(before_path),
                    str(after_path),
                    "--json", str(json_path),
                    "--only-changed-slots",
                ])
            self.assertEqual(rc, 0)
            report = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(report["changed_slots"][0]["tag"]["after"], 6)
            self.assertIn("Box 01 Slot 00", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
