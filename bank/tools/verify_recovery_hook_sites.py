#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

IMAGE_BASE = 0x00100000
EXPECTED_SIZE = 0x2AC000
EXPECTED_SHA256 = "2dce4796f54807cf8a67f1ce6297bf472d969b30ed7a7e8e25c2a6c2bdc40abf"
COMMON = {
    "bulk_state16_entry": (0x002AF460, bytes.fromhex("70 40 2d e9")),
    "state18_mismatch_funnel": (0x002A8AD0, bytes.fromhex("08 00 a0 e3")),
}
AUTO = {
    "state18_invalid_status_funnel": (0x002A8A74, bytes.fromhex("08 00 a0 e3")),
    "state18_error_case8_head": (
        0x002A8B4C,
        bytes.fromhex(
            "04 00 94 e5 67 32 fe eb 00 10 a0 e3 00 f0 20 e3 "
            "30 32 fe eb 00 50 a0 e1 00 20 a0 e3 01 1c a0 e3"
        ),
    ),
}
SMART = {
    "save_case3_tx_bind": (0x002B1E18, bytes.fromhex("08 00 94 e5")),
    "save_case5_game_save_ok": (0x002B1F4C, bytes.fromhex("08 00 94 e5")),
    "save_case9_complete_start": (0x002B20A0, bytes.fromhex("40 00 94 e5")),
}


def sites_for(variant: str):
    if variant not in {"A", "B"}:
        raise ValueError("variant must be A or B")
    sites = dict(COMMON)
    if variant == "A":
        sites.update(AUTO)
    else:
        sites.update(SMART)
    return sites


def verify_blob(blob: bytes, variant: str, check_hash: bool = True):
    errors = []
    if len(blob) != EXPECTED_SIZE:
        errors.append(f"size 0x{len(blob):X} != 0x{EXPECTED_SIZE:X}")
    if check_hash and hashlib.sha256(blob).hexdigest() != EXPECTED_SHA256:
        errors.append("sha256 mismatch")
    if len(blob) >= EXPECTED_SIZE:
        for name, (va, wanted) in sites_for(variant).items():
            off = va - IMAGE_BASE
            got = blob[off:off + len(wanted)]
            if got != wanted:
                errors.append(
                    f"{name} 0x{va:08X}: got {got.hex()} want {wanted.hex()}"
                )
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--variant", choices=["A", "B"], required=True)
    args = parser.parse_args(argv)
    try:
        blob = args.code.read_bytes()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    errors = verify_blob(blob, args.variant)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        f"OK variant={args.variant} size=0x{len(blob):X} "
        f"sha256={hashlib.sha256(blob).hexdigest()}"
    )
    for name, (va, wanted) in sites_for(args.variant).items():
        print(f"{name}=0x{va:08X} bytes={wanted.hex(' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
