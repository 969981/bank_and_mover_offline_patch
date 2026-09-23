import unittest

from verify_recovery_hook_sites import (
    EXPECTED_SIZE,
    IMAGE_BASE,
    RECOVERY_SESSION_FLAG,
    sites_for,
    verify_blob,
)


class HookSiteTests(unittest.TestCase):
    def fixture(self, variant="A"):
        blob = bytearray(EXPECTED_SIZE)
        for _, (va, wanted) in sites_for(variant).items():
            off = va - IMAGE_BASE
            blob[off:off + len(wanted)] = wanted
        return bytes(blob)

    def test_variant_a_sites(self):
        self.assertEqual(verify_blob(self.fixture("A"), "A", check_hash=False), [])

    def test_variant_b_research_sites(self):
        self.assertEqual(verify_blob(self.fixture("B"), "B", check_hash=False), [])

    def test_corrupt_a_prejournal_entry_fails(self):
        blob = bytearray(self.fixture("A"))
        blob[0x002B1DE4 - IMAGE_BASE] ^= 1
        errors = verify_blob(bytes(blob), "A", check_hash=False)
        self.assertTrue(any("save_case1_prejournal_entry" in error for error in errors))

    def test_corrupt_a_case5_status_fails(self):
        blob = bytearray(self.fixture("A"))
        blob[0x002B1F50 - IMAGE_BASE] ^= 1
        errors = verify_blob(bytes(blob), "A", check_hash=False)
        self.assertTrue(any("save_case5_status_immediate" in error for error in errors))

    def test_corrupt_a_case8_result_fails(self):
        blob = bytearray(self.fixture("A"))
        blob[0x002B2090 - IMAGE_BASE] ^= 1
        errors = verify_blob(bytes(blob), "A", check_hash=False)
        self.assertTrue(any("save_case8_result_cmp" in error for error in errors))

    def test_nonzero_recovery_scratch_fails(self):
        blob = bytearray(self.fixture("A"))
        blob[RECOVERY_SESSION_FLAG - IMAGE_BASE] = 1
        errors = verify_blob(bytes(blob), "A", check_hash=False)
        self.assertTrue(any("recovery_session_scratch" in error for error in errors))

    def test_a_does_not_require_b_only_state18_sites(self):
        blob = bytearray(self.fixture("A"))
        self.assertEqual(blob[0x002A8968 - IMAGE_BASE:0x002A896C - IMAGE_BASE], b"\x00" * 4)
        self.assertEqual(verify_blob(bytes(blob), "A", check_hash=False), [])


if __name__ == "__main__":
    unittest.main()
