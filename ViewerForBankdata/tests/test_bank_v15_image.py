import struct
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import bank_v15_layout as layout
from bank_v15_image import BankV15Image


def make_current_image(fill=False):
    if fill:
        data = bytearray((i * 37 + 11) & 0xFF for i in range(layout.CURRENT_SIZE))
    else:
        data = bytearray(layout.CURRENT_SIZE)
    struct.pack_into("<HH", data, layout.VERSION_OFFSET, layout.CURRENT_VERSION, layout.BANK_BOX_COUNT)
    return bytes(data)


class BankV15ImageTests(unittest.TestCase):
    def test_parse_serialize_is_byte_identical(self):
        raw = make_current_image(fill=True)
        self.assertEqual(BankV15Image.from_bytes(raw).to_bytes(), raw)

    def test_export_pkhex_view_is_exact_legacy_size(self):
        raw = make_current_image(fill=True)
        view = BankV15Image.from_bytes(raw).export_pkhex_view()
        self.assertEqual(len(view), 0xACA48)
        self.assertEqual(view, raw[:0xACA48])

    def test_import_pkhex_view_only_replaces_main_boxes(self):
        raw = bytearray(make_current_image(fill=True))
        view = bytearray(raw[:0xACA48])
        original_header = raw[0]
        original_transfer = raw[0xAAF14]
        original_overlap = raw[0xACA44]
        view[0] ^= 0xFF
        view[0x17C] ^= 0x7F
        view[0xAAF14] ^= 0x55
        view[0xACA44] ^= 0x33
        merged = BankV15Image.from_bytes(bytes(raw)).import_pkhex_view(bytes(view)).to_bytes()
        self.assertEqual(merged[0], original_header)
        self.assertNotEqual(merged[0x17C], raw[0x17C])
        self.assertEqual(merged[0xAAF14], original_transfer)
        self.assertEqual(merged[0xACA44], original_overlap)

    def test_import_pkhex_rejects_wrong_size(self):
        raw = make_current_image()
        image = BankV15Image.from_bytes(raw)
        with self.assertRaises(ValueError):
            image.import_pkhex_view(b"\0" * (layout.LEGACY_SIZE - 1))

    def test_from_bytes_rejects_invalid_current_image(self):
        raw = bytearray(make_current_image())
        struct.pack_into("<H", raw, layout.VERSION_OFFSET, 1)
        with self.assertRaises(ValueError):
            BankV15Image.from_bytes(bytes(raw))


if __name__ == "__main__":
    unittest.main()
