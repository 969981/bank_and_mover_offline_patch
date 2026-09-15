# -*- coding: utf-8 -*-
"""
Brute-force scan of a BankFileData dump for slots that decrypt to a given species
with a valid EK6 checksum. Used to locate tray boundaries when the layout is
uncertain.

Usage:
  python find_species.py [dump.bin] <species_id>
"""

import argparse
import struct

from parse_bank_file import (
    BOX_LENGTH,
    BLOCK_LENGTH,
    ENCRYPTION_START,
    BLOCK_POSITIONS,
    decrypt_ek6,
)

def checksum_ok(dec):
    chk = struct.unpack_from("<H", dec, 0x06)[0]
    calc = sum(struct.unpack_from("<H", dec, i)[0] for i in range(0x08, BOX_LENGTH, 2)) & 0xFFFF
    return chk == calc


def main():
    parser = argparse.ArgumentParser(description="Scan BankFileData dump for a species")
    parser.add_argument("species", type=lambda x: int(x, 0), help="species id (decimal or 0x hex)")
    parser.add_argument("--input", required=True, help="bankdata file selected by the user")
    args = parser.parse_args()
    path = args.input
    target = args.species
    data = open(path, "rb").read()

    core_off = 8
    slot_base = core_off + 0x17C  # tray0 slot0 (file offset 0x184)

    print(f"target species={target} (0x{target:04x})")
    hits = []
    # scan every 4-byte aligned offset across the whole file
    for off in range(slot_base, len(data) - BOX_LENGTH, 4):
        slot = data[off:off + BOX_LENGTH]
        if slot[:4] == b"\xff\xff\xff\xff":
            continue
        dec = decrypt_ek6(slot)
        if dec is None:
            continue
        sp = struct.unpack_from("<H", dec, 0x08)[0]
        if sp == target and checksum_ok(dec):
            hits.append(off)
            print(f"  HIT off=0x{off:06x} (tray0-relative 0x{off-slot_base:06x}, +0x{off-0x184:06x})")

    print(f"total hits: {len(hits)}")
    if hits:
        # derive tray stride candidates from hit spacing
        if len(hits) >= 2:
            print("spacings:", [hex(hits[i+1] - hits[i]) for i in range(len(hits) - 1)])


if __name__ == "__main__":
    main()
