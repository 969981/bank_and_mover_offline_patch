#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

STOCK_SHA256 = "2dce4796f54807cf8a67f1ce6297bf472d969b30ed7a7e8e25c2a6c2bdc40abf"
STOCK_SIZE = 0x2AC000
IMAGE_BASE = 0x00100000
DEFAULT_START = 0x002A8760
DEFAULT_END = 0x002A8D30
DEFAULT_CODE = Path("bank/rom/exefs/00040000000C9B00.dec.code")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_address(value: str) -> int:
    return int(value, 0)


def build_objdump_command(objdump: str, code: Path, start: int, end: int) -> list[str]:
    return [objdump, "-D", "-b", "binary", "-m", "arm", "-EL",
            f"--adjust-vma=0x{IMAGE_BASE:08x}",
            f"--start-address=0x{start:08x}",
            f"--stop-address=0x{end:08x}", str(code)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify stock Bank v1.5 .code and disassemble state18 recovery gate.")
    parser.add_argument("--code", type=Path, default=DEFAULT_CODE)
    parser.add_argument("--start", type=parse_address, default=DEFAULT_START)
    parser.add_argument("--end", type=parse_address, default=DEFAULT_END)
    parser.add_argument("--objdump", default="arm-none-eabi-objdump")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if not args.code.is_file():
        print(f"missing stock .code: {args.code}", file=sys.stderr)
        return 2
    size = args.code.stat().st_size
    if size != STOCK_SIZE:
        print(f"wrong stock .code size: 0x{size:X} (expected 0x{STOCK_SIZE:X})", file=sys.stderr)
        return 3
    digest = sha256_file(args.code)
    if digest.lower() != STOCK_SHA256:
        print(f"wrong stock .code SHA-256: {digest}", file=sys.stderr)
        return 4
    if not (IMAGE_BASE <= args.start < args.end <= IMAGE_BASE + STOCK_SIZE):
        print("requested range is outside the verified image", file=sys.stderr)
        return 5

    objdump = shutil.which(args.objdump) if Path(args.objdump).name == args.objdump else args.objdump
    if not objdump:
        print(f"objdump not found: {args.objdump}", file=sys.stderr)
        return 6
    result = subprocess.run(build_objdump_command(objdump, args.code, args.start, args.end),
                            check=False, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode
    if args.output:
        args.output.write_text(result.stdout, encoding="utf-8")
    else:
        sys.stdout.write(result.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
