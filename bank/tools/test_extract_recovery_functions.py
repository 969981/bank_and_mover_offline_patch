# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import extract_recovery_functions as erf  # noqa: E402


SAMPLE = r'''/* Ghidra headless pseudocode export. */
/* #100 @ 002a0000 : FUN_002a0000 */

int FUN_002a0000(void)
{
  return 0;
}

/* #101 @ 002af034 : FUN_002af034 */

undefined4 FUN_002af034(int param_1)
{
  if (*(int *)(param_1 + 0x10) == 0x34) {
    FUN_001d5c28();
  }
  return 1;
}

/* #102 @ 002b0000 : FUN_002b0000 */

int FUN_002b0000(void)
{
  return 2;
}
'''


class ExtractRecoveryFunctionsTests(unittest.TestCase):
    def test_normalize_address_accepts_supported_spellings(self) -> None:
        self.assertEqual(erf.normalize_address("0x002AF034"), "002af034")
        self.assertEqual(erf.normalize_address("002af034"), "002af034")
        self.assertEqual(erf.normalize_address("FUN_002af034"), "002af034")

    def test_extract_function_returns_only_requested_body(self) -> None:
        body = erf.extract_function(SAMPLE, "0x002AF034")
        self.assertIn("FUN_002af034", body)
        self.assertIn("0x34", body)
        self.assertIn("FUN_001d5c28", body)
        self.assertNotIn("FUN_002a0000(void)", body)
        self.assertNotIn("FUN_002b0000(void)", body)

    def test_index_functions_tracks_exact_boundaries(self) -> None:
        index = erf.index_functions(SAMPLE)
        start, end = index["002af034"]
        body = SAMPLE[start:end]
        self.assertTrue(body.startswith("/* #101 @ 002af034"))
        self.assertNotIn("/* #102 @ 002b0000", body)

    def test_resolve_function_address_accepts_interior_symbol_address(self) -> None:
        index = erf.index_functions(SAMPLE)
        self.assertEqual(erf.resolve_function_address(index, "002af038"), "002af034")
        self.assertEqual(erf.resolve_function_address(index, "FUN_002af034"), "002af034")

    def test_list_functions_in_range_returns_only_entries_inside_half_open_range(self) -> None:
        index = erf.index_functions(SAMPLE)
        self.assertEqual(
            erf.list_functions_in_range(index, "002a0000", "002b0000"),
            ["002a0000", "002af034"],
        )
        self.assertEqual(
            erf.list_functions_in_range(index, "002af035", "002b0001"),
            ["002b0000"],
        )

    def test_build_report_discloses_requested_and_resolved_addresses(self) -> None:
        report, missing = erf.build_report(SAMPLE, ["002af038"], ["FUN_001d5c28"], 1)
        self.assertEqual(missing, [])
        self.assertIn("requested=0x002AF038", report)
        self.assertIn("resolved_start=0x002AF034", report)
        self.assertIn("FUN_002af034", report)

    def test_reference_context_reports_matching_lines_with_context(self) -> None:
        matches = erf.find_reference_context(SAMPLE, ["0x34", "FUN_001d5c28"], context_lines=1)
        joined = "\n".join(matches)
        self.assertIn("0x34", joined)
        self.assertIn("FUN_001d5c28", joined)

    def test_extract_missing_address_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            erf.extract_function(SAMPLE, "00100000")

    def test_cli_missing_address_returns_nonzero(self) -> None:
        script = HERE / "extract_recovery_functions.py"
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "sample.c"
            source.write_text(SAMPLE, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(script), str(source), "--address", "00100000"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("00100000", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
