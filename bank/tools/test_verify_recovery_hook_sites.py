import unittest

from verify_recovery_hook_sites import EXPECTED_SIZE, IMAGE_BASE, sites_for, verify_blob


class HookSiteTests(unittest.TestCase):
    def fixture(self, variant="B"):
        blob = bytearray(EXPECTED_SIZE)
        for _, (va, wanted) in sites_for(variant).items():
            off = va - IMAGE_BASE
            blob[off:off + len(wanted)] = wanted
        return bytes(blob)

    def test_variant_a_sites(self):
        self.assertEqual(verify_blob(self.fixture("A"), "A", check_hash=False), [])

    def test_variant_b_sites(self):
        self.assertEqual(verify_blob(self.fixture("B"), "B", check_hash=False), [])

    def test_corrupt_a_prejournal_entry_fails(self):
        blob = bytearray(self.fixture("A"))
        blob[0x002B1DE4 - IMAGE_BASE] ^= 1
        errors = verify_blob(bytes(blob), "A", check_hash=False)
        self.assertTrue(any("save_case1_prejournal_entry" in error for error in errors))

    def test_corrupt_b_wal_game_funnel_fails(self):
        blob = bytearray(self.fixture("B"))
        blob[0x002A8AD0 - IMAGE_BASE] ^= 1
        errors = verify_blob(bytes(blob), "B", check_hash=False)
        self.assertTrue(any("state18_game_mismatch_funnel" in error for error in errors))

    def test_a_does_not_require_b_only_sites(self):
        self.assertEqual(verify_blob(self.fixture("A"), "A", check_hash=False), [])


if __name__ == "__main__":
    unittest.main()
