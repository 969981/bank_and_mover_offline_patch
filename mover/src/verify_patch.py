#!/usr/bin/env python3
"""Statically verify the combined Poke Mover patch.

静态校验 Poke Mover 合并补丁。
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path


IMAGE_BASE = 0x00100000
EXPECTED_BASE_SHA256 = "001C20ADA74016507C969BB44A0A50F8EDF803EC06A3FC46834263BA8DF0FD2F"
CAVE_START = 0x00261C74
CAVE_END = 0x00262C10
PAYLOAD_START = 0x0028D1B0
PAYLOAD_END = 0x0028E000


def symbols(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        fields = line.split()
        if len(fields) == 2:
            result[fields[1].lower()] = int(fields[0], 16)
    return result


def word(image: bytes, address: int) -> int:
    offset = address - IMAGE_BASE
    return int.from_bytes(image[offset:offset + 4], "little")


def branch_target(image: bytes, address: int) -> tuple[int, bool, int]:
    instruction = word(image, address)
    if ((instruction >> 25) & 7) != 5:
        raise ValueError(f"expected branch at {address:08X}, found {instruction:08X}")
    displacement = (instruction & 0xFFFFFF) << 2
    if displacement & 0x02000000:
        displacement -= 0x04000000
    return address + 8 + displacement, bool(instruction & 0x01000000), instruction >> 28


def apply_ips(base: bytes, patch: bytes) -> bytes:
    if not patch.startswith(b"PATCH") or not patch.endswith(b"EOF"):
        raise ValueError("invalid IPS stream")
    output = bytearray(base)
    cursor = 5
    while patch[cursor:cursor + 3] != b"EOF":
        offset = int.from_bytes(patch[cursor:cursor + 3], "big")
        length = int.from_bytes(patch[cursor + 3:cursor + 5], "big")
        cursor += 5
        if length:
            output[offset:offset + length] = patch[cursor:cursor + length]
            cursor += length
        else:
            count = int.from_bytes(patch[cursor:cursor + 2], "big")
            output[offset:offset + count] = bytes([patch[cursor + 2]]) * count
            cursor += 3
    return bytes(output)


def load_helper(path: Path):
    spec = importlib.util.spec_from_file_location("combined_messages", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--patched", required=True, type=Path)
    parser.add_argument("--symbols", required=True, type=Path)
    parser.add_argument("--ips", required=True, type=Path)
    parser.add_argument("--source-romfs", required=True, type=Path)
    parser.add_argument("--output-romfs", required=True, type=Path)
    args = parser.parse_args()

    base = args.base.read_bytes()
    patched = args.patched.read_bytes()
    digest = hashlib.sha256(base).hexdigest().upper()
    if digest != EXPECTED_BASE_SHA256:
        raise ValueError(f"unsupported base code SHA-256: {digest}")
    if len(base) != len(patched):
        raise ValueError("patched image length differs from base")
    if apply_ips(base, args.ips.read_bytes()) != patched:
        raise ValueError("release IPS does not reproduce the patched image")

    sym = symbols(args.symbols)
    required = {
        "combinepatch_codeusedend", "combinepatch_offlinepayloadusedend",
        "combinepatch_titletextinitialize", "combinepatch_titlestateupdate",
        "combinepatch_titleprocessmodetoggle", "combinepatch_networkupdate",
        "combinepatch_networkavailability", "combinepatch_ticketupdate",
        "combinepatch_eligibilityupdate", "combinepatch_getpokemonupdate",
        "combinepatch_saveskipremotejob",
        "offlinepatch_networkupdate", "offlinepatch_stage", "offlinepatch_commit",
        "offlinepatch_rollback",
    }
    missing = sorted(required - sym.keys())
    if missing:
        raise ValueError(f"missing armips symbols: {', '.join(missing)}")
    if not CAVE_START < sym["combinepatch_codeusedend"] <= CAVE_END:
        raise ValueError("mode wrappers exceed the audited code cave")
    if not PAYLOAD_START < sym["combinepatch_offlinepayloadusedend"] <= PAYLOAD_END:
        raise ValueError("offline payload exceeds the executable tail")

    expected_base_words = {
        0x0024BA84: 0xEBFD4261,
        0x00249F20: 0xE5D0103C,
        0x00248A08: 0xE92D4070,
        0x00248B88: 0xEBFB1ACF,
        0x00248B98: 0xE594100C,
        0x00248BC0: 0xE3A0100D,
        0x00249600: 0xE92D43F8,
        0x00248814: 0xE92D41F0,
        0x00248C68: 0xE92D4070,
        0x002455D0: 0xE92D4FF0,
        0x00246A5C: 0xE3A0100F,
        0x00245728: 0xE59F0C74,
        0x002460B8: 0xE59F02E4,
        0x00248360: 0xE92D4070,
        0x0024709C: 0xE92D4010,
        0x00247288: 0xE3A0100E,
        0x00247290: 0xE594100C,
        0x00242D4C: 0x03A0000E,
        0x0024A150: 0xE59F04F4,
        0x0024A240: 0xEBFFD1E9,
        0x0024A258: 0xE5D41044,
        0x0024A3E4: 0xEBFD454C,
        0x0024A3EC: 0x13A0000B,
        0x0024A420: 0xEBFD44EA,
        0x0024A428: 0x13A0000D,
        0x0024A6F0: 0xE3A01009,
    }
    for address, expected in expected_base_words.items():
        actual = word(base, address)
        if actual != expected:
            raise ValueError(
                f"unexpected base instruction at {address:08X}: "
                f"expected {expected:08X}, found {actual:08X}"
            )

    hooks = {
        0x0024BA84: ("combinepatch_titletextinitialize", True, 0xE),
        0x00249F20: ("combinepatch_titlestateupdate", False, 0xE),
        0x00248A08: ("combinepatch_networkupdate", False, 0xE),
        0x00248B88: ("combinepatch_networkavailability", True, 0xE),
        0x00248B98: ("combinepatch_networkskipremotejob", False, 0xE),
        0x00248BC0: ("combinepatch_selectinitialconnectmessage", True, 0xE),
        0x00249600: ("combinepatch_ticketupdate", False, 0xE),
        0x00248814: ("combinepatch_remotecheckupdate", False, 0xE),
        0x00248C68: ("combinepatch_eligibilityupdate", False, 0xE),
        0x002455D0: ("combinepatch_getpokemonupdate", False, 0xE),
        0x00246A5C: ("combinepatch_selectbankconnectmessage", True, 0xE),
        0x00245728: ("combinepatch_gen5validation", False, 0xE),
        0x002460B8: ("combinepatch_gen12validation", False, 0xE),
        0x00248360: ("combinepatch_notransferupdate", False, 0xE),
        0x0024709C: ("combinepatch_disconnectupdate", False, 0xE),
        0x00247288: ("combinepatch_selectdisconnectmessage", True, 0xE),
        0x00247290: ("combinepatch_disconnectskipremotejob", False, 0xE),
        0x00242D4C: ("combinepatch_remotechecksuccessstate", False, 0x0),
        0x0024A150: ("combinepatch_saveskipremotejob", False, 0xE),
        0x0024A240: ("combinepatch_stage", True, 0xE),
        0x0024A258: ("combinepatch_savewait", False, 0xE),
        0x0024A3E4: ("combinepatch_commit", True, 0xE),
        0x0024A3EC: ("combinepatch_aftercommit", False, 0x1),
        0x0024A420: ("combinepatch_rollback", True, 0xE),
        0x0024A428: ("combinepatch_afterrollback", False, 0x1),
        0x0024A6F0: ("combinepatch_selectsavemessage", True, 0xE),
    }
    for address, (name, link, condition) in hooks.items():
        target, actual_link, actual_condition = branch_target(patched, address)
        if (target, actual_link, actual_condition) != (sym[name], link, condition):
            raise ValueError(f"incorrect hook at {address:08X}")

    messages = load_helper(Path(__file__).with_name("patch_messages.py"))
    for archive in messages.ARCHIVES:
        source_entries = messages.message_codec.read_garc(
            (args.source_romfs / "a" / Path(archive)).read_bytes()
        )[2]
        output_entries = messages.message_codec.read_garc(
            (args.output_romfs / "a" / Path(archive)).read_bytes()
        )[2]
        source_lines = messages.message_codec.read_message_lines(
            source_entries[messages.MESSAGE_FILE_INDEX].files[0]
        )
        output_lines = messages.message_codec.read_message_lines(
            output_entries[messages.MESSAGE_FILE_INDEX].files[0]
        )
        if output_lines[:len(source_lines)] != source_lines:
            raise ValueError(f"stock messages changed in {archive}")
        if len(output_lines) != messages.DISCONNECT_LINE + 1:
            raise ValueError(f"unexpected appended line count in {archive}")

    print("combined Mover patch verification passed")


if __name__ == "__main__":
    main()
