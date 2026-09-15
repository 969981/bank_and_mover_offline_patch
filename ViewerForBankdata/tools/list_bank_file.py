# -*- coding: utf-8 -*-
"""
Dump a per-tray listing of every non-empty Pokemon slot in a BankFileData dump,
using the official PKSM-Core Chinese species names.

Usage:
  python list_bank_file.py [--input DUMP.bin] [--range T1 T2] [--grid] [--nonempty]
  python list_bank_file.py --grid --range 0 10
"""

import argparse
import struct
from pathlib import Path

from parse_bank_file import BOX_LENGTH, decrypt_ek6, fmt_u16

def load_names(path):
    names = {0: "蛋"}
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if line:
            names[i] = line
    return names


def disp_width(s):
    """Display width: CJK chars count as 2 columns."""
    return sum(2 if ord(c) > 0xFF else 1 for c in s)


def pad_disp(s, width):
    return s + " " * max(0, width - disp_width(s))


def read_tray_name(data, tray, slot_base, stride):
    off = slot_base + tray * stride + 30 * BOX_LENGTH
    raw = data[off:off + 34]
    try:
        name = raw.decode("utf-16-le", errors="replace")
    except Exception:
        name = ""
    return name.rstrip("\x00 ")


def read_group_names(data):
    """BankFileLayout groupLabels[GROUP_MAX=10][17] starts at core+8 (file+16)."""
    names = []
    for i in range(10):
        raw = data[16 + i * 34:16 + (i + 1) * 34]
        try:
            name = raw.decode("utf-16-le", errors="replace")
            name = name.split("\x00", 1)[0]
        except Exception:
            name = ""
        names.append(name)
    return names


def tray_group_order(data, tray, slot_base, stride):
    off = slot_base + tray * stride
    group = data[off + 0x1B53]
    order = struct.unpack_from("<H", data, off + 0x1B54)[0]
    return group, order


def main():
    parser = argparse.ArgumentParser(description="List BankFileData trays")
    parser.add_argument("--input", required=True, help="bankdata file selected by the user")
    parser.add_argument("--names", type=Path, help="optional UTF-8 name list, one numbered entry per line")
    parser.add_argument("--output", type=Path, help="optional report file; defaults to standard output")
    parser.add_argument("--range", nargs=2, type=int, metavar=("T1", "T2"),
                        help="tray range (0-based start, exclusive end), e.g. --range 0 3")
    parser.add_argument("--grid", action="store_true", help="6x5 grid layout")
    parser.add_argument("--nonempty", action="store_true", help="skip empty trays")
    args = parser.parse_args()
    path = args.input
    tray_range = tuple(args.range) if args.range else None
    grid = args.grid
    only_nonempty = args.nonempty

    data = open(path, "rb").read()
    if len(data) == 767256:  # core-only (server serialized) input: pad 8-byte object header
        data = b"\x00" * 8 + data
    names = load_names(args.names) if args.names else {}
    dump = data

    slot_base = 0x184
    stride = 0x1B56
    start_tray, end_tray = tray_range if tray_range else (0, 100)

    group_names = read_group_names(dump)
    group_label = {g: f"群组{g+1}({group_names[g]})" for g in range(10)}

    # sort trays by (group, order), then by physical tray index as tiebreak
    tray_order = []
    for tray in range(start_tray, end_tray):
        g, o = tray_group_order(dump, tray, slot_base, stride)
        tray_order.append((g, o, tray))
    tray_order.sort()

    lines = []
    last_group = None
    for g, o, tray in tray_order:
        cells = []
        for pos in range(30):
            off = slot_base + tray * stride + pos * 0xE8
            if off + 232 > len(data):
                break
            slot = data[off:off + 232]
            if slot[:4] == b"\xff\xff\xff\xff":
                cells.append(".")
                continue
            dec = decrypt_ek6(slot)
            sp = fmt_u16(dec, 0x08) if dec else 0
            if sp == 0:
                cells.append(".")
            else:
                cells.append(f"{sp}:{names.get(sp, '?')}")

        nonempty_count = sum(1 for c in cells if c != ".")
        if only_nonempty and nonempty_count == 0:
            continue

        tray_name = read_tray_name(dump, tray, slot_base, stride)
        if grid:
            # game box layout: 6 columns x 5 rows
            if g != last_group:
                lines.append(f"===== {group_label.get(g, f'群组{g+1}')} (group {g}) =====")
                last_group = g
            title = f"TRAY 物理{tray+1:3d} (6x5) [{nonempty_count}/30]  order={o}"
            if tray_name:
                title += f"  {tray_name}"
            lines.append(title)
            for r in range(5):
                cells_row = []
                for c in range(6):
                    idx = r * 6 + c
                    cell = cells[idx] if idx < len(cells) else "."
                    cells_row.append(pad_disp(cell, 14))
                lines.append("  " + " | ".join(cells_row))
        else:
            if g != last_group:
                lines.append(f"===== {group_label.get(g, f'群组{g+1}')} (group {g}) =====")
                last_group = g
            lines.append(f"TRAY 物理{tray+1:3d} order={o} {tray_name}: " + " | ".join(cells))

    report = "\n".join(lines)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"wrote {args.output} ({len(lines)} lines)")
    else:
        print(report)


if __name__ == "__main__":
    main()
