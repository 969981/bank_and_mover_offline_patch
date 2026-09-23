#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

IMAGE_BASE = 0x00100000
STOCK_SIZE = 0x2AC000
STOCK_SHA256 = "2dce4796f54807cf8a67f1ce6297bf472d969b30ed7a7e8e25c2a6c2bdc40abf"

SITES = {
    # state18 game-recovery mismatch edges
    0x002A89D0: bytes.fromhex("3e 00 00 1a"),
    0x002A89E0: bytes.fromhex("3a 00 00 1a"),

    # state7 transaction/game-save/remote-complete lifecycle
    0x002B1E18: bytes.fromhex("08 00 94 e5"),
    0x002B1F1C: bytes.fromhex("04 00 a0 e3"),
    0x002B1F48: bytes.fromhex("89 00 00 ea"),
    0x002B20A0: bytes.fromhex("40 00 94 e5"),
    0x002B20AC: bytes.fromhex("30 8f fc eb"),
    0x002B20CC: bytes.fromhex("0d 10 a0 e3"),
    0x002B20E8: bytes.fromhex("ce 8e fc eb"),
    0x002B210C: bytes.fromhex("10 10 a0 e3"),

    # serialize/stage seam
    0x002B24A0: bytes.fromhex("17 c0 ff eb"),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("code", type=Path)
    args = ap.parse_args()

    if not args.code.is_file():
        print(f"missing stock .code: {args.code}", file=sys.stderr)
        return 2
    if args.code.stat().st_size != STOCK_SIZE:
        print(f"wrong size: 0x{args.code.stat().st_size:X}", file=sys.stderr)
        return 3
    digest = sha256_file(args.code)
    if digest.lower() != STOCK_SHA256:
        print(f"wrong SHA-256: {digest}", file=sys.stderr)
        return 4

    data = args.code.read_bytes()
    failed = False
    for address, expected in SITES.items():
        off = address - IMAGE_BASE
        actual = data[off:off + len(expected)]
        ok = actual == expected
        print(f"0x{address:08X} {'OK' if ok else 'FAIL'} expected={expected.hex()} actual={actual.hex()}")
        failed |= not ok
    return 5 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
