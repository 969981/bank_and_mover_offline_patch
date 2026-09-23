#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

CODE_BASE = 0x00100000
EXPECTED_SIZE = 0x2AC000
EXPECTED_SHA256 = "2dce4796f54807cf8a67f1ce6297bf472d969b30ed7a7e8e25c2a6c2bdc40abf"
SELF_LOOP = bytes.fromhex("FE FF FF EA")  # ARM: B .

FAULT_POINTS = {
    "post-stage": {
        "address": 0x002B1E18,
        "stock": bytes.fromhex("08 00 94 E5"),
        "description": "remote Stage succeeded; before game recovery record/save starts",
    },
    "post-game-save": {
        "address": 0x002B1F4C,
        "stock": bytes.fromhex("08 00 94 E5"),
        "description": "game save callback succeeded; before case5 local recovery update",
    },
    "pre-complete": {
        "address": 0x002B20A0,
        "stock": bytes.fromhex("40 00 94 E5"),
        "description": "local recovery persisted; immediately before CompleteUpdateBankObject",
    },
}

EXPECTED_RECOVERY = {
    "A": {
        "post-stage": "rollback",
        "post-game-save": "rollback",
        "pre-complete": "rollback",
    },
    "B": {
        "post-stage": "rollback",
        "post-game-save": "commit",
        "pre-complete": "commit",
    },
}


def _offset(address: int) -> int:
    return address - CODE_BASE


def expected_recovery(variant: str, point: str) -> str:
    variant = variant.upper()
    if variant not in EXPECTED_RECOVERY:
        raise ValueError(f"unknown recovery variant: {variant}")
    if point not in FAULT_POINTS:
        raise ValueError(f"unknown fault point: {point}")
    return EXPECTED_RECOVERY[variant][point]


def inject_fault(patched: bytes, point: str) -> bytes:
    if point not in FAULT_POINTS:
        raise ValueError(f"unknown fault point: {point}")
    if len(patched) != EXPECTED_SIZE:
        raise ValueError(
            f"unexpected patched .code size 0x{len(patched):X}; expected 0x{EXPECTED_SIZE:X}"
        )
    spec = FAULT_POINTS[point]
    off = _offset(spec["address"])
    got = patched[off:off + 4]
    if got != spec["stock"]:
        raise ValueError(
            f"target bytes at 0x{spec['address']:08X} are {got.hex(' ')}, "
            f"expected untouched stock {spec['stock'].hex(' ')}"
        )
    out = bytearray(patched)
    out[off:off + 4] = SELF_LOOP
    return bytes(out)


def make_ips(base: bytes, modified: bytes) -> bytes:
    if len(base) != len(modified):
        raise ValueError("IPS inputs must have the same size")
    if len(base) >= 0x1000000:
        raise ValueError("IPS writer only supports offsets below 0x1000000")

    out = bytearray(b"PATCH")
    i = 0
    n = len(base)
    while i < n:
        if base[i] == modified[i]:
            i += 1
            continue
        start = i
        chunk = bytearray()
        while i < n and base[i] != modified[i] and len(chunk) < 0xFFFF:
            chunk.append(modified[i])
            i += 1
        out.extend(start.to_bytes(3, "big"))
        out.extend(len(chunk).to_bytes(2, "big"))
        out.extend(chunk)
    out.extend(b"EOF")
    return bytes(out)


def apply_ips(base: bytes, patch: bytes) -> bytes:
    if not patch.startswith(b"PATCH") or not patch.endswith(b"EOF"):
        raise ValueError("invalid IPS header/footer")
    out = bytearray(base)
    pos = 5
    while patch[pos:pos + 3] != b"EOF":
        if pos + 5 > len(patch):
            raise ValueError("truncated IPS record")
        off = int.from_bytes(patch[pos:pos + 3], "big")
        pos += 3
        size = int.from_bytes(patch[pos:pos + 2], "big")
        pos += 2
        if size:
            data = patch[pos:pos + size]
            if len(data) != size:
                raise ValueError("truncated IPS data")
            pos += size
        else:
            if pos + 3 > len(patch):
                raise ValueError("truncated IPS RLE record")
            rle_size = int.from_bytes(patch[pos:pos + 2], "big")
            pos += 2
            data = bytes([patch[pos]]) * rle_size
            pos += 1
        end = off + len(data)
        if end > len(out):
            out.extend(b"\0" * (end - len(out)))
        out[off:end] = data
    return bytes(out)


def _validate_stock_base(base: bytes) -> None:
    if len(base) != EXPECTED_SIZE:
        raise ValueError(
            f"unexpected stock .code size 0x{len(base):X}; expected 0x{EXPECTED_SIZE:X}"
        )
    digest = hashlib.sha256(base).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(
            f"unexpected stock .code SHA-256 {digest}; expected {EXPECTED_SHA256}"
        )


def _preflight(base: bytes, patched: bytes, points: list[str]) -> None:
    _validate_stock_base(base)
    if len(patched) != EXPECTED_SIZE:
        raise ValueError(
            f"unexpected production-patched .code size 0x{len(patched):X}; "
            f"expected 0x{EXPECTED_SIZE:X}"
        )
    for point in points:
        spec = FAULT_POINTS[point]
        off = _offset(spec["address"])
        stock_got = base[off:off + 4]
        patched_got = patched[off:off + 4]
        if stock_got != spec["stock"]:
            raise ValueError(
                f"stock target bytes at 0x{spec['address']:08X} are "
                f"{stock_got.hex(' ')}, expected {spec['stock'].hex(' ')}"
            )
        if patched_got != spec["stock"]:
            raise ValueError(
                f"production patch already changed target bytes at "
                f"0x{spec['address']:08X}: {patched_got.hex(' ')}"
            )


def _manifest(
    variant: str,
    point: str,
    base: bytes,
    patched: bytes,
    fault: bytes,
    ips: bytes,
) -> dict[str, object]:
    spec = FAULT_POINTS[point]
    return {
        "format": "official-bank-recovery-fault-v1",
        "variant": variant,
        "point": point,
        "virtual_address": f"0x{spec['address']:08X}",
        "stock_instruction": spec["stock"].hex(" ").upper(),
        "fault_instruction": SELF_LOOP.hex(" ").upper(),
        "fault_semantics": "ARM B . deterministic freeze; hard power-cycle only after freeze",
        "description": spec["description"],
        "expected_recovery": expected_recovery(variant, point),
        "stock_sha256": hashlib.sha256(base).hexdigest(),
        "production_patched_sha256": hashlib.sha256(patched).hexdigest(),
        "fault_code_sha256": hashlib.sha256(fault).hexdigest(),
        "ips_sha256": hashlib.sha256(ips).hexdigest(),
    }


def build_outputs(
    variant: str,
    base_path: Path,
    patched_path: Path,
    out_dir: Path,
    point: str,
) -> list[Path]:
    variant = variant.upper()
    if variant not in EXPECTED_RECOVERY:
        raise ValueError("variant must be A or B")
    if point == "all":
        points = list(FAULT_POINTS)
    elif point in FAULT_POINTS:
        points = [point]
    else:
        raise ValueError(f"unknown fault point: {point}")

    base = base_path.read_bytes()
    patched = patched_path.read_bytes()
    _preflight(base, patched, points)

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in points:
        fault = inject_fault(patched, name)
        ips = make_ips(base, fault)
        if apply_ips(base, ips) != fault:
            raise AssertionError(f"IPS replay mismatch for {name}")

        stem = f"code-fi-{name}"
        code_path = out_dir / f"{stem}.dec.code"
        ips_path = out_dir / f"{stem}.ips"
        manifest_path = out_dir / f"{stem}.json"
        code_path.write_bytes(fault)
        ips_path.write_bytes(ips)
        manifest_path.write_text(
            json.dumps(
                _manifest(variant, name, base, patched, fault, ips),
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        written.extend([code_path, ips_path, manifest_path])
    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic Pokémon Bank recovery fault-injection IPS files."
    )
    parser.add_argument("--variant", choices=["A", "B"], required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--patched", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--point",
        choices=["all", *FAULT_POINTS.keys()],
        default="all",
    )
    args = parser.parse_args()

    try:
        written = build_outputs(
            args.variant, args.base, args.patched, args.out_dir, args.point
        )
    except (OSError, ValueError, AssertionError) as exc:
        parser.error(str(exc))

    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
