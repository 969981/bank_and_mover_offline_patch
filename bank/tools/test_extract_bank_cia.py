import struct
import unittest

from extract_bank_cia import BankCiaError, align_up, blz_decompress, find_exefs_entry


class ExtractBankCiaTests(unittest.TestCase):
    def test_align_up(self):
        self.assertEqual(align_up(0x2020, 0x40), 0x2040)
        self.assertEqual(align_up(0x2D90, 0x40), 0x2DC0)

    def test_blz_literal_plus_backrefs(self):
        stream = (b"\x00\xF0" * 5) + b"AAA" + bytes([0x1F])
        compressed_size = len(stream) + 8
        wanted_size = 93
        blob = stream + struct.pack("<II", (8 << 24) | compressed_size, wanted_size - compressed_size)
        self.assertEqual(blz_decompress(blob), b"A" * wanted_size)

    def test_find_exefs_code(self):
        exefs = bytearray(0x240)
        exefs[0:8] = b".code\0\0\0"
        struct.pack_into("<II", exefs, 8, 0x10, 4)
        exefs[0x210:0x214] = b"CODE"
        off, size = find_exefs_entry(bytes(exefs), b".code")
        self.assertEqual((off, size), (0x210, 4))

    def test_reject_invalid_blz(self):
        with self.assertRaises(BankCiaError):
            blz_decompress(b"\0" * 8)


if __name__ == "__main__":
    unittest.main()
