# -*- coding: utf-8 -*-
"""Structured binary diff for Pokemon Bank v1.5 0xBB518 BankObject bodies."""

import argparse
import json
from pathlib import Path
import struct
from typing import Iterable

import bank_v15_layout as layout


def _coalesce(offsets: Iterable[int]) -> list[dict[str, int]]:
    values = sorted(offsets)
    if not values:
        return []
    ranges: list[dict[str, int]] = []
    start = previous = values[0]
    for offset in values[1:]:
        if offset == previous + 1:
            previous = offset
            continue
        ranges.append({"start": start, "end": previous + 1, "length": previous + 1 - start})
        start = previous = offset
    ranges.append({"start": start, "end": previous + 1, "length": previous + 1 - start})
    return ranges


def _require_current_size(name: str, data: bytes) -> None:
    if len(data) != layout.CURRENT_SIZE:
        raise ValueError(
            f"{name} size mismatch: got 0x{len(data):X}, expected 0x{layout.CURRENT_SIZE:X}"
        )


def compare_bank_images(before: bytes, after: bytes) -> dict:
    _require_current_size("before", before)
    _require_current_size("after", after)

    changed_by_region: dict[str, list[int]] = {}
    changed_byte_count = 0
    for offset, (old, new) in enumerate(zip(before, after)):
        if old == new:
            continue
        changed_byte_count += 1
        region = layout.region_for_offset(offset)
        changed_by_region.setdefault(region, []).append(offset)

    changed_slots: list[dict] = []
    for box in range(layout.BANK_BOX_COUNT):
        for slot in range(layout.SLOTS_PER_BOX):
            offsets = layout.slot_offsets(box, slot)
            old_pokemon = before[offsets.pokemon:offsets.pokemon + layout.POKEMON_SIZE]
            new_pokemon = after[offsets.pokemon:offsets.pokemon + layout.POKEMON_SIZE]
            pokemon_changed = old_pokemon != new_pokemon
            old_tag = before[offsets.tag]
            new_tag = after[offsets.tag]
            old_source = before[offsets.source_software]
            new_source = after[offsets.source_software]
            old_time = struct.unpack_from("<Q", before, offsets.timestamp)[0]
            new_time = struct.unpack_from("<Q", after, offsets.timestamp)[0]

            if not (pokemon_changed or old_tag != new_tag or old_source != new_source or old_time != new_time):
                continue

            item = {
                "index": offsets.index,
                "box": box,
                "slot": slot,
                "pokemon_changed": pokemon_changed,
            }
            if old_tag != new_tag:
                item["tag"] = {"before": old_tag, "after": new_tag}
            if old_source != new_source:
                item["source_software"] = {"before": old_source, "after": new_source}
            if old_time != new_time:
                item["timestamp"] = {"before": old_time, "after": new_time}
            changed_slots.append(item)

    regions = {
        name: {"changed_bytes": len(offsets), "ranges": _coalesce(offsets)}
        for name, offsets in sorted(changed_by_region.items())
    }

    return {
        "format": "PokemonBankV15",
        "size": layout.CURRENT_SIZE,
        "changed_byte_count": changed_byte_count,
        "before_validation": layout.validate_current(before),
        "after_validation": layout.validate_current(after),
        "changed_slots": changed_slots,
        "regions": regions,
    }


def _fmt_pair(change: dict, width: int = 2) -> str:
    old = change["before"]
    new = change["after"]
    return f"0x{old:0{width}X} -> 0x{new:0{width}X}"


def render_text(result: dict, only_changed_slots: bool = False) -> str:
    lines = [
        "Pokemon Bank v1.5 structured diff",
        f"changed bytes: {result['changed_byte_count']}",
        f"changed slots: {len(result['changed_slots'])}",
    ]
    if result["before_validation"]:
        lines.append("before warnings: " + "; ".join(result["before_validation"]))
    if result["after_validation"]:
        lines.append("after warnings: " + "; ".join(result["after_validation"]))

    for item in result["changed_slots"]:
        lines.append("")
        lines.append(f"Box {item['box'] + 1:02d} Slot {item['slot']:02d} (index {item['index']})")
        lines.append(f"  Pokemon  {'changed' if item['pokemon_changed'] else 'unchanged'}")
        if "tag" in item:
            lines.append("  Tag      " + _fmt_pair(item["tag"]))
        if "source_software" in item:
            lines.append("  Source   " + _fmt_pair(item["source_software"]))
        if "timestamp" in item:
            old = item["timestamp"]["before"]
            new = item["timestamp"]["after"]
            lines.append(f"  Time     0x{old:016X} -> 0x{new:016X}")

    if not only_changed_slots:
        lines.append("")
        lines.append("Changed regions:")
        if not result["regions"]:
            lines.append("  (none)")
        for name, info in result["regions"].items():
            ranges = ", ".join(
                f"0x{r['start']:06X}-0x{r['end'] - 1:06X}" for r in info["ranges"]
            )
            lines.append(f"  {name}: {info['changed_bytes']} bytes [{ranges}]")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Structured diff for Pokemon Bank v1.5 bankdata")
    parser.add_argument("before", type=Path, help="baseline 0xBB518 bankdata.bin")
    parser.add_argument("after", type=Path, help="modified 0xBB518 bankdata.bin")
    parser.add_argument("--json", dest="json_output", type=Path, help="optional JSON report path")
    parser.add_argument(
        "--only-changed-slots",
        action="store_true",
        help="omit the region-range section from text output",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    before = args.before.read_bytes()
    after = args.after.read_bytes()
    result = compare_bank_images(before, after)
    print(render_text(result, args.only_changed_slots))
    if args.json_output:
        args.json_output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
