#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract selected functions/references from the large Pokémon Bank Ghidra export.

The repository keeps a >11 MiB `code.bin_all_functions.c`. GitHub's normal
contents API is inconvenient for inspecting individual functions in a file of
that size, so this tool turns stock addresses into a compact, deterministic
research report.

Curated Bank symbols sometimes name an instruction inside a Ghidra function
rather than the function's first instruction. The report therefore always
prints both the requested address and the resolved decompiler function start.
"""
from __future__ import annotations

import argparse
import bisect
import re
import sys
from pathlib import Path

FUNCTION_MARKER_RE = re.compile(
    r"(?m)^/\*\s*#\d+\s+@\s+([0-9A-Fa-f]{8})\s*:\s*FUN_([0-9A-Fa-f]{8})\s*\*/\s*$"
)

DEFAULT_ADDRESSES = (
    "002a5580",
    "002a5a7c",
    "002acbdc",
    "002adc50",
    "002af034",
    "002a93f4",
    "002a9700",
    "002a8760",
    "002a9118",
    "002ad7bc",
    "002b1cf8",
    "002a26ac",
    "002a27c8",
    "002a3144",
    "002d0edc",
    "001d5d74",
    "001d5c28",
    "002cb8a8",
    "002cb8c4",
    "002cb8d0",
    "002cb8dc",
    "002cb8e8",
    "002cb908",
    "001d4d48",
    "001d4d54",
    "001d4d60",
    "001d4d6c",
    "001d4d78",
    "001d4d84",
    "00233a6c",
    "0023234c",
    "00232338",
    "002b4a20",
    "002b4ab4",
)

DEFAULT_REFERENCES = (
    "FUN_002cb8a8",
    "FUN_002cb8c4",
    "FUN_002cb8d0",
    "FUN_002cb8dc",
    "FUN_002cb8e8",
    "FUN_002cb908",
    "FUN_001d4d48",
    "FUN_001d4d54",
    "FUN_001d4d60",
    "FUN_001d4d6c",
    "FUN_001d4d78",
    "FUN_001d4d84",
    "FUN_001d5d74",
    "FUN_001d5c28",
    "FUN_002a3144",
    "FUN_002d0edc",
)


def normalize_address(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("fun_"):
        value = value[4:]
    if value.startswith("0x"):
        value = value[2:]
    if not re.fullmatch(r"[0-9a-f]{1,8}", value):
        raise ValueError(f"invalid address: {value!r}")
    return value.zfill(8)


def index_functions(text: str) -> dict[str, tuple[int, int]]:
    matches = list(FUNCTION_MARKER_RE.finditer(text))
    result: dict[str, tuple[int, int]] = {}
    for index, match in enumerate(matches):
        marker_address = normalize_address(match.group(1))
        function_address = normalize_address(match.group(2))
        if marker_address != function_address:
            raise ValueError(
                f"function marker address mismatch: {marker_address} != {function_address}"
            )
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[marker_address] = (start, end)
    return result


def resolve_function_address(
    functions: dict[str, tuple[int, int]], requested: str
) -> str:
    normalized = normalize_address(requested)
    if normalized in functions:
        return normalized
    target = int(normalized, 16)
    ordered = sorted(int(address, 16) for address in functions)
    position = bisect.bisect_right(ordered, target) - 1
    if position < 0:
        raise KeyError(normalized)
    return f"{ordered[position]:08x}"


def list_functions_in_range(
    functions: dict[str, tuple[int, int]], start: str, end: str
) -> list[str]:
    """Return function entries in the half-open address range [start, end)."""
    start_value = int(normalize_address(start), 16)
    end_value = int(normalize_address(end), 16)
    if start_value >= end_value:
        raise ValueError("range start must be lower than range end")
    return [
        address
        for address in sorted(functions, key=lambda value: int(value, 16))
        if start_value <= int(address, 16) < end_value
    ]


def extract_function(text: str, address: str) -> str:
    normalized = normalize_address(address)
    functions = index_functions(text)
    try:
        start, end = functions[normalized]
    except KeyError:
        raise KeyError(normalized) from None
    return text[start:end].rstrip() + "\n"


def find_reference_context(
    text: str,
    needles: list[str] | tuple[str, ...],
    context_lines: int = 4,
    max_matches_per_needle: int = 120,
) -> list[str]:
    lines = text.splitlines()
    lowered = [line.lower() for line in lines]
    result: list[str] = []
    seen_windows: set[tuple[int, int, str]] = set()

    for needle in needles:
        target = needle.lower()
        hits = [index for index, line in enumerate(lowered) if target in line]
        shown = hits[:max_matches_per_needle]
        result.append(f"### reference {needle} (matches={len(hits)}, shown={len(shown)})")
        if not shown:
            result.append("<no matches>")
            continue
        for hit in shown:
            start = max(0, hit - context_lines)
            end = min(len(lines), hit + context_lines + 1)
            key = (start, end, target)
            if key in seen_windows:
                continue
            seen_windows.add(key)
            result.append(f"-- lines {start + 1}-{end} --")
            for line_number in range(start, end):
                marker = ">" if line_number == hit else " "
                result.append(f"{marker}{line_number + 1:07d}: {lines[line_number]}")
    return result


def build_report(
    text: str,
    addresses: list[str] | tuple[str, ...],
    references: list[str] | tuple[str, ...],
    context_lines: int,
) -> tuple[str, list[str]]:
    function_index = index_functions(text)
    missing: list[str] = []
    out: list[str] = [
        "# Pokémon Bank recovery static extraction",
        "",
        f"indexed_functions={len(function_index)}",
        "",
        "## Selected functions",
    ]

    for requested in addresses:
        normalized = normalize_address(requested)
        try:
            resolved = resolve_function_address(function_index, normalized)
        except KeyError:
            out.extend(["", f"### requested=0x{normalized.upper()}", "<missing>"])
            missing.append(normalized)
            continue
        out.extend(
            [
                "",
                f"### requested=0x{normalized.upper()} resolved_start=0x{resolved.upper()}",
            ]
        )
        start, end = function_index[resolved]
        body = text[start:end].rstrip()
        out.extend(["```c", body, "```"])

    out.extend(["", "## Global reference contexts", ""])
    out.extend(find_reference_context(text, references, context_lines=context_lines))
    out.append("")
    return "\n".join(out), missing


def build_range_report(text: str, range_start: str, range_end: str) -> str:
    function_index = index_functions(text)
    addresses = list_functions_in_range(function_index, range_start, range_end)
    out = [
        "# Pokémon Bank recovery function range",
        "",
        f"range=[0x{normalize_address(range_start).upper()},0x{normalize_address(range_end).upper()})",
        f"functions={len(addresses)}",
    ]
    for address in addresses:
        start, end = function_index[address]
        out.extend(["", f"## 0x{address.upper()}", "```c", text[start:end].rstrip(), "```"])
    out.append("")
    return "\n".join(out)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decompile", type=Path, help="path to code.bin_all_functions.c")
    parser.add_argument(
        "--address",
        action="append",
        dest="addresses",
        help="instruction/function address; repeatable (default: recovery state set)",
    )
    parser.add_argument(
        "--reference",
        action="append",
        dest="references",
        help="literal/function reference to search globally; repeatable",
    )
    parser.add_argument("--context-lines", type=int, default=4)
    parser.add_argument("--range-start", help="enumerate function entries from this address")
    parser.add_argument("--range-end", help="exclusive end address for --range-start")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        text = args.decompile.read_text(encoding="utf-8", errors="replace")
        if bool(args.range_start) != bool(args.range_end):
            raise ValueError("--range-start and --range-end must be supplied together")
        if args.range_start:
            report = build_range_report(text, args.range_start, args.range_end)
            missing: list[str] = []
        else:
            addresses = args.addresses or list(DEFAULT_ADDRESSES)
            references = args.references or list(DEFAULT_REFERENCES)
            report, missing = build_report(text, addresses, references, args.context_lines)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)

    if missing:
        print(
            "error: missing requested address(es): " + ", ".join(missing),
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
