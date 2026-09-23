# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from extract_decompiled_functions import extract_functions


SAMPLE = r'''/* Ghidra headless pseudocode export. */
/* #1 @ 00100000 : FUN_00100000 */

void FUN_00100000(void)
{
  return;
}

/* #2 @ 002af034 : FUN_002af034 */

undefined4 FUN_002af034(int param_1)
{
  if (param_1 == 0x34) {
    return 0;
  }
  return 1;
}

/* #3 @ 002a93f4 : FUN_002a93f4 */

void FUN_002a93f4(void)
{
  FUN_001d5c28();
  return;
}
'''


class ExtractDecompilerFunctionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "code.bin_all_functions.c"
        self.path.write_text(SAMPLE, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_extracts_complete_function_by_case_insensitive_address(self) -> None:
        result = extract_functions(self.path, ["002AF034"])
        self.assertEqual(list(result), ["002af034"])
        text = result["002af034"]
        self.assertIn("/* #2 @ 002af034 : FUN_002af034 */", text)
        self.assertIn("if (param_1 == 0x34)", text)
        self.assertNotIn("FUN_002a93f4", text)

    def test_extracts_requested_functions_in_request_order(self) -> None:
        result = extract_functions(self.path, ["002A93F4", "00100000"])
        self.assertEqual(list(result), ["002a93f4", "00100000"])
        self.assertIn("FUN_001d5c28", result["002a93f4"])
        self.assertIn("void FUN_00100000", result["00100000"])

    def test_missing_address_is_an_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "002a9118"):
            extract_functions(self.path, ["002A9118"])

    def test_rejects_invalid_address(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid address"):
            extract_functions(self.path, ["trainer-error"])


if __name__ == "__main__":
    unittest.main()
