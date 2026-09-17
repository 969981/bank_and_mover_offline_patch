# -*- coding: utf-8 -*-
"""Route A helper CLI for Pokemon Bank v1.5 full-image workflows."""

import argparse
from pathlib import Path
import struct
import sys

import bank_v15_layout as layout
from bank_v15_image import BankV15Image


def _load_current(path: Path) -> BankV15Image:
    return BankV15Image.from_bytes(path.read_bytes())


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def cmd_validate(args) -> int:
    image = _load_current(args.input)
    raw = image.to_bytes()
    version, box_count = struct.unpack_from("<HH", raw, layout.VERSION_OFFSET)
    print(
        f"valid Pokemon Bank v1.5 image: size=0x{len(raw):X}, "
        f"version={version}, boxes={box_count}"
    )
    return 0


def cmd_inspect(args) -> int:
    image = _load_current(args.input)
    raw = image.to_bytes()
    version, box_count = struct.unpack_from("<HH", raw, layout.VERSION_OFFSET)
    print("Pokemon Bank v1.5 image")
    print(f"  size: 0x{len(raw):X} ({len(raw)})")
    print(f"  version: {version}")
    print(f"  boxes: {box_count}")
    print(
        f"  main boxes: 0x{layout.BANK_BOXES_START:06X}-"
        f"0x{layout.TRANSFER_BOX_START - 1:06X}"
    )
    print(f"  PKHeX compatibility view size: 0x{layout.LEGACY_SIZE:X}")
    return 0


def cmd_export_pkhex(args) -> int:
    image = _load_current(args.input)
    data = image.export_pkhex_view()
    _write(args.output, data)
    print(f"wrote PKHeX compatibility view: {args.output} (0x{len(data):X} bytes)")
    return 0


def cmd_import_pkhex(args) -> int:
    image = _load_current(args.template)
    view = args.view.read_bytes()
    merged = image.import_pkhex_view(view).to_bytes()
    _write(args.output, merged)
    print(f"wrote full current image: {args.output} (0x{len(merged):X} bytes)")
    return 0


def cmd_build(args) -> int:
    image = _load_current(args.template)
    data = image.to_bytes()
    _write(args.output, data)
    print(f"wrote bulk import image: {args.output} (0x{len(data):X} bytes)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pokemon Bank v1.5 Route A full-image and PKHeX-view helper"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="validate a full 0xBB518 current image")
    p.add_argument("input", type=Path)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("inspect", help="show current-image layout basics")
    p.add_argument("input", type=Path)
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("export-pkhex", help="export a 0xACA48 PKHeX Bank7 compatibility view")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, required=True)
    p.set_defaults(func=cmd_export_pkhex)

    p = sub.add_parser(
        "import-pkhex",
        help="merge only the edited 100 main boxes from a PKHeX view into a full current template",
    )
    p.add_argument("template", type=Path)
    p.add_argument("view", type=Path)
    p.add_argument("-o", "--output", type=Path, required=True)
    p.set_defaults(func=cmd_import_pkhex)

    p = sub.add_parser("build", help="validate and copy a full current template to bulk_import.bin")
    p.add_argument("template", type=Path)
    p.add_argument("-o", "--output", type=Path, required=True)
    p.set_defaults(func=cmd_build)

    return parser


def main(argv=None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
