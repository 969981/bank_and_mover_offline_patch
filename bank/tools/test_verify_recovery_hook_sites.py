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

    def test_corrupt_exact_game_dataid_mismatch_branch_fails(self):
        blob = bytearray(self.fixture("B"))
        blob[0x002A89D0 - IMAGE_BASE] ^= 1
        errors = verify_blob(bytes(blob), "B", check_hash=False)
        self.assertTrue(any("state18_game_dataid_mismatch_bne" in error for error in errors))

    def test_a_does_not_require_b_only_sites(self):
        self.assertEqual(verify_blob(self.fixture("A"), "A", check_hash=False), [])


if __name__ == "__main__":
    unittest.main()
