# -*- coding: utf-8 -*-
"""Raw R4/R5/R6 classifier for Pokemon Bank v1.5 metadata regions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

import bank_v15_layout as layout


def _ranges(block: bytes) -> list[dict[str, int]]:
    ranges: list[dict[str, int]] = []
    start = previous = None
    for offset, value in enumerate(block):
        if value == 0:
            continue
        if start is None:
            start = previous = offset
            continue
        if offset == previous + 1:
            previous = offset
            continue
        ranges.append({
            "relative_start": start,
            "relative_end": previous + 1,
            "length": previous + 1 - start,
        })
        start = previous = offset
    if start is not None:
        ranges.append({
            "relative_start": start,
            "relative_end": previous + 1,
            "length": previous + 1 - start,
        })
    return ranges


def _summary_entries(block: bytes) -> list[dict]:
    entries = []
    for index in range(8):
        entry = block[index * 0x44:(index + 1) * 0x44]
        entries.append({
            "index": index,
            "nonzero_bytes": sum(value != 0 for value in entry),
            "ranges": _ranges(entry),
            "hex": entry.hex(),
        })
    return entries


def classify(data: bytes) -> dict:
    errors = layout.validate_current(data)
    if errors:
        raise ValueError("; ".join(errors))

    summaries = data[layout.SOURCE_SUMMARIES_START:layout.POKEDEX_AGGREGATE_START]
    opaque = data[layout.POKEDEX_AGGREGATE_START:layout.COUNTERS_START]
    counters = data[layout.COUNTERS_START:layout.SOURCE_SOFTWARE_START]
    tail = data[layout.TAIL_START:layout.CURRENT_SIZE]
    magic = opaque[:4]

    return {
        "format": "PokemonBankV15",
        "source_summaries": {
            "size": len(summaries),
            "nonzero_bytes": sum(value != 0 for value in summaries),
            "entries": _summary_entries(summaries),
        },
        "opaque_7260": {
            "size": len(opaque),
            "magic_hex": magic.hex(),
            "magic_ascii": "".join(chr(value) if 32 <= value < 127 else "." for value in magic),
            "nonzero_bytes": sum(value != 0 for value in opaque),
            "ranges": _ranges(opaque),
        },
        "counters": {
            "raw_hex": counters.hex(),
            "u16_le": list(struct.unpack("<HH", counters)),
            "u32_le": struct.unpack("<I", counters)[0],
        },
        "tail": {
            "size": len(tail),
            "nonzero_bytes": sum(value != 0 for value in tail),
            "ranges": _ranges(tail),
            "hex": tail.hex(),
        },
    }


def render_text(result: dict) -> str:
    lines = ["Pokemon Bank v1.5 R4/R5/R6 raw metadata classifier"]
    summaries = result["source_summaries"]
    lines.append(
        f"source summaries: {summaries['nonzero_bytes']} nonzero / "
        f"0x{summaries['size']:X} bytes"
    )
    for entry in summaries["entries"]:
        lines.append(f"  entry {entry['index']}: {entry['nonzero_bytes']} nonzero bytes")

    opaque = result["opaque_7260"]
    lines.append(
        f"opaque 0x7260: magic={opaque['magic_ascii']!r} ({opaque['magic_hex']}), "
        f"nonzero={opaque['nonzero_bytes']}"
    )
    counters = result["counters"]
    lines.append(
        f"counters: raw={counters['raw_hex']} u16={counters['u16_le']} "
        f"u32={counters['u32_le']}"
    )
    tail = result["tail"]
    lines.append(f"tail: {tail['nonzero_bytes']} nonzero / 0x{tail['size']:X} bytes")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify R4/R5/R6 Bank v1.5 metadata without assigning guessed semantics"
    )
    parser.add_argument("bankdata", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)

    result = classify(args.bankdata.read_bytes())
    print(render_text(result))
    if args.json:
        args.json.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
