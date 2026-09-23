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
    # Verified invariant: state+0x28 is already the exact transaction passed to Stage.
    "save_stage_tx_load": (0x002B2494, bytes.fromhex("28 30 94 e5")),
    "save_stage_call": (0x002B24A0, bytes.fromhex("17 c0 ff eb")),
}

AUTO = {
    # Variant A adds only the pre-RMC52 diversion and case8 journal result hook.
    # case7 keeps stock status=1 and state18 remains completely stock.
    "save_case1_prejournal_entry": (0x002B1DE4, bytes.fromhex("04 00 a0 e1")),
    "save_case8_result_cmp": (0x002B2090, bytes.fromhex("01 00 50 e3")),
}

SMART = {
    # Kept for cross-branch research fixtures; B has additional production hooks.
    "save_case1_prejournal_entry": (0x002B1DE4, bytes.fromhex("04 00 a0 e1")),
    "save_case7_status_immediate": (0x002B1FFC, bytes.fromhex("01 10 a0 e3")),
    "save_case8_result_cmp": (0x002B2090, bytes.fromhex("01 00 50 e3")),
    "state18_local_status_decision": (0x002A8968, bytes.fromhex("01 00 50 e3")),
    "state18_game_dataid_mismatch_bne": (0x002A89D0, bytes.fromhex("3e 00 00 1a")),
    "state18_game_curversion_mismatch_bne": (0x002A89E0, bytes.fromhex("3a 00 00 1a")),
    "state18_game_mismatch_decision_block": (
        0x002A8A64,
        bytes.fromhex(
            "00 20 a0 e3 02 10 a0 e1 02 00 a0 e1 00 00 a0 e1 "
            "08 00 a0 e3 00 f0 20 e3"
        ),
    ),
}


def sites_for(variant: str):
    if variant not in {"A", "B"}:
        raise ValueError("variant must be A or B")
    sites = dict(COMMON)
    sites.update(AUTO if variant == "A" else SMART)
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
                errors.append(f"{name} 0x{va:08X}: got {got.hex()} want {wanted.hex()}")
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
    print(f"OK variant={args.variant} size=0x{len(blob):X} sha256={hashlib.sha256(blob).hexdigest()}")
    for name, (va, wanted) in sites_for(args.variant).items():
        print(f"{name}=0x{va:08X} bytes={wanted.hex(' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
