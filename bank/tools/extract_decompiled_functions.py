# -*- coding: utf-8 -*-
"""Extract complete functions from the checked-in Ghidra pseudocode export."""
from __future__ import annotations

import argparse
import re
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

HEADER_RE = re.compile(
    r"^/\*\s+#\d+\s+@\s+([0-9A-Fa-f]{8})\s+:\s+[^*]+\*/\s*$",
    re.MULTILINE,
)
ADDRESS_RE = re.compile(r"^[0-9A-Fa-f]{8}$")


def _normalize_addresses(addresses: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for address in addresses:
        value = address.strip().lower().removeprefix("0x")
        if not ADDRESS_RE.fullmatch(value):
            raise ValueError(f"invalid address: {address}")
        if value not in normalized:
            normalized.append(value)
    return normalized


def extract_functions(path: Path, addresses: Iterable[str]) -> OrderedDict[str, str]:
    requested = _normalize_addresses(addresses)
    text = path.read_text(encoding="utf-8")
    matches = list(HEADER_RE.finditer(text))
    spans: dict[str, str] = {}
    for index, match in enumerate(matches):
        address = match.group(1).lower()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        spans[address] = text[match.start():end].rstrip() + "\n"

    missing = [address for address in requested if address not in spans]
    if missing:
        raise ValueError("missing address(es): " + ", ".join(missing))

    return OrderedDict((address, spans[address]) for address in requested)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Ghidra code.bin_all_functions.c export")
    parser.add_argument("addresses", nargs="+", help="8-digit virtual addresses, with optional 0x prefix")
    parser.add_argument("-o", "--output", type=Path, help="write combined output to this file")
    args = parser.parse_args()

    extracted = extract_functions(args.input, args.addresses)
    chunks = []
    for address, body in extracted.items():
        chunks.append(f"/* ===== extracted 0x{address.upper()} ===== */\n{body}")
    rendered = "\n".join(chunks)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
