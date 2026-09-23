#!/usr/bin/env python3
"""Extract and verify Pokémon Bank v1.5 stock .code from a NoCrypto CIA.

This intentionally supports the exact Bank CIA baseline used by this repository.
It parses the CIA section layout, verifies the first content is a NoCrypto NCCH,
extracts ExeFS/.code, performs Nintendo 3DS BLZ backward decompression, and
verifies the resulting stock image before writing it.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path

EXPECTED_TITLE_ID = 0x00040000000C9B00
EXPECTED_CODE_SIZE = 0x2AC000
EXPECTED_CODE_SHA256 = "2dce4796f54807cf8a67f1ce6297bf472d969b30ed7a7e8e25c2a6c2bdc40abf"
MEDIA_UNIT = 0x200
CIA_ALIGN = 0x40
NCCH_MAGIC_OFF = 0x100
NCCH_FLAGS_OFF = 0x188
NCCH_EXEFS_OFF = 0x1A0
NCCH_EXEFS_SIZE_OFF = 0x1A4
NCCH_PROGRAM_ID_OFF = 0x118
EXEFS_HEADER_SIZE = 0x200


class BankCiaError(ValueError):
    pass


def align_up(value: int, alignment: int) -> int:
    if alignment <= 0 or alignment & (alignment - 1):
        raise BankCiaError("alignment must be a positive power of two")
    return (value + alignment - 1) & ~(alignment - 1)


def parse_cia_content_offset(blob: bytes) -> tuple[int, int]:
    if len(blob) < 0x20:
        raise BankCiaError("CIA too small")
    header_size, _, _, cert_size, ticket_size, tmd_size, meta_size, content_size = struct.unpack_from(
        "<IHHIIIIQ", blob, 0
    )
    if header_size < 0x20 or header_size > len(blob):
        raise BankCiaError("invalid CIA header size")
    off = align_up(header_size, CIA_ALIGN)
    off = align_up(off + cert_size, CIA_ALIGN)
    off = align_up(off + ticket_size, CIA_ALIGN)
    off = align_up(off + tmd_size, CIA_ALIGN)
    if off + content_size > len(blob):
        raise BankCiaError("CIA content extends past end of file")
    # meta lives after all content and does not affect the first content offset.
    _ = meta_size
    return off, content_size


def parse_ncch_exefs(blob: bytes, content_off: int) -> tuple[int, int]:
    if content_off < 0 or content_off + 0x200 > len(blob):
        raise BankCiaError("NCCH header outside CIA")
    if blob[content_off + NCCH_MAGIC_OFF:content_off + NCCH_MAGIC_OFF + 4] != b"NCCH":
        raise BankCiaError("first CIA content is not NCCH")
    flags = blob[content_off + NCCH_FLAGS_OFF:content_off + NCCH_FLAGS_OFF + 8]
    if len(flags) != 8 or (flags[7] & 0x04) == 0:
        raise BankCiaError("NCCH is encrypted; NoCrypto flag is not set")
    program_id = struct.unpack_from("<Q", blob, content_off + NCCH_PROGRAM_ID_OFF)[0]
    if program_id != EXPECTED_TITLE_ID:
        raise BankCiaError(f"unexpected program id 0x{program_id:016X}")
    exefs_units = struct.unpack_from("<I", blob, content_off + NCCH_EXEFS_OFF)[0]
    exefs_size_units = struct.unpack_from("<I", blob, content_off + NCCH_EXEFS_SIZE_OFF)[0]
    exefs_off = content_off + exefs_units * MEDIA_UNIT
    exefs_size = exefs_size_units * MEDIA_UNIT
    if exefs_off + exefs_size > len(blob):
        raise BankCiaError("ExeFS extends past end of file")
    return exefs_off, exefs_size


def find_exefs_entry(exefs: bytes, wanted: bytes) -> tuple[int, int]:
    if len(wanted) > 8:
        raise BankCiaError("ExeFS name too long")
    if len(exefs) < EXEFS_HEADER_SIZE:
        raise BankCiaError("ExeFS too small")
    for i in range(10):
        ent = exefs[i * 0x10:(i + 1) * 0x10]
        name = ent[:8].split(b"\0", 1)[0]
        off, size = struct.unpack_from("<II", ent, 8)
        if name == wanted:
            data_off = EXEFS_HEADER_SIZE + off
            if data_off + size > len(exefs):
                raise BankCiaError(f"ExeFS entry {wanted!r} is truncated")
            return data_off, size
    raise BankCiaError(f"ExeFS entry {wanted!r} not found")


def blz_decompress(src: bytes) -> bytes:
    if len(src) < 8:
        raise BankCiaError("BLZ input too small")
    encoded_info, add_size = struct.unpack_from("<II", src, len(src) - 8)
    header_size = (encoded_info >> 24) & 0xFF
    encoded_size = encoded_info & 0x00FFFFFF
    if header_size < 8 or header_size > len(src):
        raise BankCiaError("invalid BLZ header size")
    if encoded_size < header_size or encoded_size > len(src):
        raise BankCiaError("invalid BLZ encoded size")
    out_size = len(src) + add_size
    out = bytearray(out_size)
    out[:len(src)] = src

    src_pos = len(src) - header_size
    src_start = len(src) - encoded_size
    dst_pos = out_size

    while src_pos > src_start:
        src_pos -= 1
        flags = src[src_pos]
        for _ in range(8):
            if src_pos <= src_start:
                break
            if flags & 0x80:
                if src_pos - 2 < src_start:
                    raise BankCiaError("truncated BLZ back-reference")
                src_pos -= 2
                token = src[src_pos] | (src[src_pos + 1] << 8)
                length = (token >> 12) + 3
                displacement = (token & 0x0FFF) + 3
                for _ in range(length):
                    if dst_pos <= 0 or dst_pos + displacement > out_size:
                        raise BankCiaError("invalid BLZ back-reference")
                    dst_pos -= 1
                    out[dst_pos] = out[dst_pos + displacement]
            else:
                if src_pos <= src_start or dst_pos <= 0:
                    raise BankCiaError("truncated BLZ literal")
                src_pos -= 1
                dst_pos -= 1
                out[dst_pos] = src[src_pos]
            flags = (flags << 1) & 0xFF

    if src_pos != src_start or dst_pos != src_start:
        raise BankCiaError(
            f"BLZ did not converge: src=0x{src_pos:X} dst=0x{dst_pos:X} start=0x{src_start:X}"
        )
    return bytes(out)


def extract_stock_code(cia: bytes) -> tuple[bytes, dict[str, int | str]]:
    content_off, content_size = parse_cia_content_offset(cia)
    exefs_off, exefs_size = parse_ncch_exefs(cia, content_off)
    exefs = cia[exefs_off:exefs_off + exefs_size]
    code_off, code_size = find_exefs_entry(exefs, b".code")
    compressed = exefs[code_off:code_off + code_size]
    code = blz_decompress(compressed)
    digest = hashlib.sha256(code).hexdigest()
    if len(code) != EXPECTED_CODE_SIZE:
        raise BankCiaError(f"unexpected decompressed .code size 0x{len(code):X}")
    if digest != EXPECTED_CODE_SHA256:
        raise BankCiaError(f"unexpected decompressed .code SHA-256 {digest}")
    return code, {
        "cia_content_offset": content_off,
        "cia_content_size": content_size,
        "exefs_offset": exefs_off,
        "exefs_size": exefs_size,
        "compressed_code_size": code_size,
        "decompressed_code_size": len(code),
        "sha256": digest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cia", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        cia = args.cia.read_bytes()
        code, info = extract_stock_code(cia)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(code)
    except (OSError, BankCiaError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for key, value in info.items():
        if isinstance(value, int):
            print(f"{key}=0x{value:X}")
        else:
            print(f"{key}={value}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
