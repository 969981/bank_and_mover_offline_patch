import unittest

from extract_recovery_chain import direct_callees, normalize_address, parse_functions, render_report

SAMPLE = r'''/* Ghidra headless pseudocode export. */
/* #10 @ 002af034 : FUN_002af034 */
undefined4 FUN_002af034(int param_1)
{
  FUN_00111111(param_1);
  thunk_FUN_00222222();
  FUN_00111111(param_1 + 4);
  /* mention FUN_002af034 itself; do not report self */
  return 1;
}

/* #11 @ 00111111 : FUN_00111111 */
void FUN_00111111(int x)
{
  FUN_00333333(x);
}

/* #12 @ 00222222 : thunk_FUN_00222222 */
void thunk_FUN_00222222(void)
{
  FUN_00333333();
}
'''


class RecoveryExtractorTests(unittest.TestCase):
    def test_normalize_address_accepts_hex_forms(self):
        self.assertEqual(normalize_address('0x2af034'), '002af034')
        self.assertEqual(normalize_address('002AF034'), '002af034')

    def test_parse_extracts_exact_function_body(self):
        funcs = parse_functions(SAMPLE)
        self.assertEqual(set(funcs), {'002af034', '00111111', '00222222'})
        body = funcs['002af034'].text
        self.assertIn('undefined4 FUN_002af034', body)
        self.assertIn('return 1;', body)
        self.assertNotIn('void FUN_00111111', body)

    def test_direct_callees_are_unique_ordered_and_exclude_self(self):
        funcs = parse_functions(SAMPLE)
        self.assertEqual(direct_callees(funcs['002af034']), ['00111111', '00222222'])

    def test_render_report_marks_missing_targets(self):
        funcs = parse_functions(SAMPLE)
        report, missing = render_report(funcs, ['002af034', '00abcdef'])
        self.assertEqual(missing, ['00abcdef'])
        self.assertIn('TARGET 002af034', report)
        self.assertIn('DIRECT CALLEES: 00111111, 00222222', report)
        self.assertIn('MISSING 00abcdef', report)


if __name__ == '__main__':
    unittest.main()
