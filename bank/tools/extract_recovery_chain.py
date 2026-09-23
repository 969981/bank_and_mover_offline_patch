#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

HEADER_RE = re.compile(
    r'^/\*\s+#(?P<index>\d+)\s+@\s+(?P<addr>[0-9A-Fa-f]{8})\s+:\s+(?P<name>[^*]+?)\s+\*/\s*$',
    re.MULTILINE,
)
CALL_RE = re.compile(r'(?<![A-Za-z0-9_])(?:thunk_)?FUN_([0-9A-Fa-f]{8})\s*\(')


@dataclass(frozen=True)
class GhidraFunction:
    index: int
    address: str
    name: str
    text: str


def normalize_address(value: str) -> str:
    value = value.strip().lower()
    if value.startswith('0x'):
        value = value[2:]
    if not value or any(ch not in '0123456789abcdef' for ch in value):
        raise ValueError(f'invalid hex address: {value!r}')
    if len(value) > 8:
        raise ValueError(f'address wider than 32-bit: {value!r}')
    return value.zfill(8)


def parse_functions(text: str) -> Dict[str, GhidraFunction]:
    matches = list(HEADER_RE.finditer(text))
    result: Dict[str, GhidraFunction] = {}
    for pos, match in enumerate(matches):
        start = match.start()
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(text)
        address = match.group('addr').lower()
        result[address] = GhidraFunction(
            index=int(match.group('index')),
            address=address,
            name=match.group('name').strip(),
            text=text[start:end].rstrip() + '\n',
        )
    return result


def direct_callees(function: GhidraFunction) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for match in CALL_RE.finditer(function.text):
        address = match.group(1).lower()
        if address == function.address or address in seen:
            continue
        seen.add(address)
        ordered.append(address)
    return ordered


def render_report(functions: Dict[str, GhidraFunction], targets: Iterable[str]) -> Tuple[str, List[str]]:
    chunks: List[str] = []
    missing: List[str] = []
    for raw in targets:
        address = normalize_address(raw)
        function = functions.get(address)
        if function is None:
            missing.append(address)
            chunks.append(f'===== MISSING {address} =====\n')
            continue
        callees = direct_callees(function)
        chunks.append(f'===== TARGET {address} {function.name} =====\n')
        chunks.append('DIRECT CALLEES: ' + (', '.join(callees) if callees else '(none)') + '\n\n')
        chunks.append(function.text)
        chunks.append('\n')
    return ''.join(chunks), missing


def _targets_from_file(path: Path) -> List[str]:
    targets: List[str] = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.split('#', 1)[0].strip()
        if line:
            targets.append(line)
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description='Extract selected functions from a Ghidra C export.')
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--targets-file', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--require-all', action='store_true')
    parser.add_argument('addresses', nargs='*')
    args = parser.parse_args()

    targets = list(args.addresses)
    if args.targets_file:
        targets.extend(_targets_from_file(args.targets_file))
    if not targets:
        parser.error('provide at least one address or --targets-file')

    text = args.input.read_text(encoding='utf-8', errors='replace')
    functions = parse_functions(text)
    report, missing = render_report(functions, targets)
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')
    if missing:
        print('missing targets: ' + ', '.join(missing))
    return 2 if args.require_all and missing else 0


if __name__ == '__main__':
    raise SystemExit(main())
