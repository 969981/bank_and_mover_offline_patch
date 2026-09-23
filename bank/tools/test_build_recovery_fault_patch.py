import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_recovery_fault_patch import (  # noqa: E402
    CODE_BASE,
    EXPECTED_SIZE,
    FAULT_POINTS,
    SELF_LOOP,
    apply_ips,
    expected_recovery,
    inject_fault,
    make_ips,
)


class RecoveryFaultPatchTests(unittest.TestCase):
    def fixture(self, point):
        blob = bytearray(EXPECTED_SIZE)
        spec = FAULT_POINTS[point]
        off = spec["address"] - CODE_BASE
        blob[off:off + 4] = spec["stock"]
        return bytes(blob)

    def test_verified_fault_points_are_exact(self):
        self.assertEqual(
            FAULT_POINTS["post-stage"]["address"], 0x002B1E18
        )
        self.assertEqual(
            FAULT_POINTS["post-stage"]["stock"], bytes.fromhex("08 00 94 E5")
        )
        self.assertEqual(
            FAULT_POINTS["post-game-save"]["address"], 0x002B1F4C
        )
        self.assertEqual(
            FAULT_POINTS["post-game-save"]["stock"], bytes.fromhex("08 00 94 E5")
        )
        self.assertEqual(
            FAULT_POINTS["pre-complete"]["address"], 0x002B20A0
        )
        self.assertEqual(
            FAULT_POINTS["pre-complete"]["stock"], bytes.fromhex("40 00 94 E5")
        )
        self.assertEqual(SELF_LOOP, bytes.fromhex("FE FF FF EA"))

    def test_injection_changes_only_one_instruction(self):
        original = self.fixture("post-game-save")
        modified = inject_fault(original, "post-game-save")
        off = FAULT_POINTS["post-game-save"]["address"] - CODE_BASE
        self.assertEqual(modified[off:off + 4], SELF_LOOP)
        changed = [i for i, (a, b) in enumerate(zip(original, modified)) if a != b]
        self.assertEqual(changed, [off, off + 1, off + 2, off + 3])

    def test_wrong_target_bytes_fail_closed(self):
        blob = bytes(EXPECTED_SIZE)
        with self.assertRaisesRegex(ValueError, "target bytes"):
            inject_fault(blob, "pre-complete")

    def test_unknown_fault_point_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown fault point"):
            inject_fault(bytes(EXPECTED_SIZE), "after-everything")

    def test_ips_round_trip_reproduces_fault_image(self):
        base = bytearray(EXPECTED_SIZE)
        spec = FAULT_POINTS["post-stage"]
        off = spec["address"] - CODE_BASE
        base[off:off + 4] = spec["stock"]
        production = bytearray(base)
        # Synthetic existing production difference outside the fault site.
        production[0x1234:0x1238] = b"WAL!"
        fault = inject_fault(bytes(production), "post-stage")
        ips = make_ips(bytes(base), fault)
        self.assertEqual(apply_ips(bytes(base), ips), fault)

    def test_expected_recovery_matrix(self):
        self.assertEqual(expected_recovery("A", "post-stage"), "rollback")
        self.assertEqual(expected_recovery("A", "post-game-save"), "rollback")
        self.assertEqual(expected_recovery("A", "pre-complete"), "rollback")
        self.assertEqual(expected_recovery("B", "post-stage"), "rollback")
        self.assertEqual(expected_recovery("B", "post-game-save"), "commit")
        self.assertEqual(expected_recovery("B", "pre-complete"), "commit")

    def test_branch_makefile_declares_variant_b(self):
        makefile = (Path(__file__).resolve().parents[1] / "src" / "Makefile").read_text(
            encoding="utf-8"
        )
        self.assertIn("FAULT_VARIANT := B", makefile)


if __name__ == "__main__":
    unittest.main()
