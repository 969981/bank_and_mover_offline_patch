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
    # Hook the two real game-recovery mismatch edges, not the shared state=8 funnel.
    "state18_game_dataid_mismatch_bne": (0x002A89D0, bytes.fromhex("3e 00 00 1a")),
    "state18_game_curversion_mismatch_bne": (0x002A89E0, bytes.fromhex("3a 00 00 1a")),
    # Safe marker cleanup points after stock remote success callbacks.
    "save_complete_callback_success": (0x002B20CC, bytes.fromhex("0d 10 a0 e3")),
    "save_rollback_callback_success": (0x002B210C, bytes.fromhex("10 10 a0 e3")),
}

AUTO = {
    # Earliest currently proven point where state+0x28 contains the exact tx and
    # stock has not yet written GameRecoveryRecord.
    "save_case3_tx_bound": (0x002B1E18, bytes.fromhex("08 00 94 e5")),
    "serialize_stage_call": (0x002B24A0, bytes.fromhex("17 c0 ff eb")),
}

SMART = {
    "save_case3_tx_bound": (0x002B1E18, bytes.fromhex("08 00 94 e5")),
    "save_game_started": (0x002B1F1C, bytes.fromhex("04 00 a0 e3")),
    "save_game_result_dispatch": (0x002B1F48, bytes.fromhex("89 00 00 ea")),
    "save_remote_complete_start": (0x002B20A0, bytes.fromhex("40 00 94 e5")),
    "save_remote_complete_call": (0x002B20AC, bytes.fromhex("30 8f fc eb")),
    "serialize_stage_call": (0x002B24A0, bytes.fromhex("17 c0 ff eb")),
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
