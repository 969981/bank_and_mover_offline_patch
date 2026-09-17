# -*- coding: utf-8 -*-
"""Route A helper CLI for Pokemon Bank v1.5 full-image workflows."""

import argparse
import json
from pathlib import Path
import struct
import sys

import bank_v15_layout as layout
import diff_bank_file
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


def cmd_apply_v0(args) -> int:
    runtime = _load_current(args.runtime)
    bulk = _load_current(args.bulk)
    expected = runtime.apply_main_boxes_from(bulk).to_bytes()
    _write(args.output, expected)
    print(
        f"wrote Route A V0 expected image: {args.output} "
        f"(copied 0x{layout.BANK_BOXES_START:X}-0x{layout.TRANSFER_BOX_START:X}, "
        "preserved all other runtime bytes)"
    )
    return 0


def verify_v0(runtime: bytes, bulk: bytes, saved: bytes) -> dict:
    runtime_image = BankV15Image.from_bytes(runtime)
    bulk_image = BankV15Image.from_bytes(bulk)
    saved_image = BankV15Image.from_bytes(saved)
    expected = runtime_image.apply_main_boxes_from(bulk_image).to_bytes()
    saved_raw = saved_image.to_bytes()

    start = layout.BANK_BOXES_START
    end = layout.TRANSFER_BOX_START
    main_boxes_match = saved_raw[start:end] == expected[start:end]
    strict_match = saved_raw == expected
    post_save_diff = diff_bank_file.compare_bank_images(expected, saved_raw)

    outside_regions = {
        name: info
        for name, info in post_save_diff["regions"].items()
        if name not in {"bank_slot_payload", "box_metadata"}
    }
    main_box_regions = {
        name: info
        for name, info in post_save_diff["regions"].items()
        if name in {"bank_slot_payload", "box_metadata"}
    }

    return {
        "format": "PokemonBankRouteAV0Verification",
        "main_boxes_match_expected": main_boxes_match,
        "strict_byte_match_expected": strict_match,
        "main_box_mismatch_regions": main_box_regions,
        "stock_or_runtime_metadata_changes": outside_regions,
        "changed_byte_count_vs_expected": post_save_diff["changed_byte_count"],
        "changed_slots_vs_expected": post_save_diff["changed_slots"],
    }


def cmd_verify_v0(args) -> int:
    runtime = _load_current(args.runtime).to_bytes()
    bulk = _load_current(args.bulk).to_bytes()
    saved = _load_current(args.saved).to_bytes()
    result = verify_v0(runtime, bulk, saved)

    print("Pokemon Bank Route A V0 verification")
    print(
        "  main 100 boxes: "
        + ("MATCH expected" if result["main_boxes_match_expected"] else "MISMATCH")
    )
    print(
        "  full image: "
        + ("byte-identical" if result["strict_byte_match_expected"] else "has post-save differences")
    )
    print(f"  changed bytes vs expected: {result['changed_byte_count_vs_expected']}")

    outside = result["stock_or_runtime_metadata_changes"]
    if outside:
        print("  current-only / outside-box changes:")
        for name, info in outside.items():
            print(f"    {name}: {info['changed_bytes']} bytes")
    else:
        print("  current-only / outside-box changes: none")

    if result["main_box_mismatch_regions"]:
        print("  main-box mismatch regions:")
        for name, info in result["main_box_mismatch_regions"].items():
            print(f"    {name}: {info['changed_bytes']} bytes")

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.strict:
        return 0 if result["strict_byte_match_expected"] else 3
    return 0 if result["main_boxes_match_expected"] else 3


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

    p = sub.add_parser(
        "apply-v0",
        help="simulate the 3DS V0 whitelist: main boxes from bulk, all other bytes from runtime",
    )
    p.add_argument("runtime", type=Path, help="current runtime/bankdata 0xBB518 image")
    p.add_argument("bulk", type=Path, help="bulk_import.bin 0xBB518 image")
    p.add_argument("-o", "--output", type=Path, required=True)
    p.set_defaults(func=cmd_apply_v0)

    p = sub.add_parser(
        "verify-v0",
        help="verify a saved Offline image against Route A V0 expected main boxes",
    )
    p.add_argument("runtime", type=Path, help="bankdata before applying bulk")
    p.add_argument("bulk", type=Path, help="bulk_import.bin used by the 3DS")
    p.add_argument("saved", type=Path, help="bankdata copied back after Offline save/reload")
    p.add_argument("--json", dest="json_output", type=Path, help="optional JSON report")
    p.add_argument(
        "--strict",
        action="store_true",
        help="require the entire saved image to be byte-identical to the V0 expected image",
    )
    p.set_defaults(func=cmd_verify_v0)

    return parser


def main(argv=None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except (OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
