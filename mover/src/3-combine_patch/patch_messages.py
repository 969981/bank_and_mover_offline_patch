#!/usr/bin/env python3
"""Append mode-specific messages for the combined Poke Mover patch.

为 Poke Mover 合并补丁追加按模式选择的文本。
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


ARCHIVES = ("0/0/4", "0/0/5", "0/0/6", "0/0/7", "0/0/8", "0/0/9",
            "0/1/0", "0/1/1", "0/1/2", "0/1/3")
MESSAGE_FILE_INDEX = 23
TITLE_HOME_LINE = 39
TITLE_OFFLINE_LINE = 67
TITLE_ORIGINAL_LINE = 68
INITIAL_CONNECT_LINE = 69
BANK_CONNECT_LINE = 70
SAVE_LINE = 71
DISCONNECT_LINE = 72
TITLE_TEXT_BUFFER_LENGTH = 54
R_BUTTON = "\ue005"

TITLE_HOME_SHORT = {
    "0/0/4": "\ue073を押すとHOMEメニューに戻ります",
    "0/0/5": "\ue073を押すとHOMEメニューに戻ります",
    "0/0/6": "Press \ue073 to HOME Menu",
    "0/0/7": "\ue073 : menu HOME",
    "0/0/8": "\ue073: menu HOME",
    "0/0/9": "\ue073: HOME-Menü",
    "0/1/0": "\ue073: menú HOME",
    "0/1/1": "\ue073을 누르면 HOME 메뉴로 돌아갑니다",
    "0/1/2": "如果按\ue073，就会返回HOME菜单。",
    "0/1/3": "按\ue073可返回HOME選單",
}

TITLE_OFFLINE = {
    "0/0/4": f"現在のモード：オフライン（{R_BUTTON}で切替）",
    "0/0/5": f"現在のモード：オフライン（{R_BUTTON}で切替）",
    "0/0/6": f"Current: Offline ({R_BUTTON}:switch mode)",
    "0/0/7": f"Mode : hors ligne ({R_BUTTON} : changer)",
    "0/0/8": f"Modalità: offline ({R_BUTTON}: cambia modo)",
    "0/0/9": f"Modus: Offline ({R_BUTTON}: Modus wechseln)",
    "0/1/0": f"Modo: sin conexión ({R_BUTTON}: cambiar modo)",
    "0/1/1": f"현재 모드: 오프라인 ({R_BUTTON}로 전환)",
    "0/1/2": f"当前模式：离线模式（按{R_BUTTON}键切换模式）",
    "0/1/3": f"目前模式：離線模式（按{R_BUTTON}鍵切換模式）",
}

TITLE_ORIGINAL = {
    "0/0/4": f"現在のモード：オリジナル（{R_BUTTON}で切替）",
    "0/0/5": f"現在のモード：オリジナル（{R_BUTTON}で切替）",
    "0/0/6": f"Current: Original ({R_BUTTON}:switch mode)",
    "0/0/7": f"Mode : original ({R_BUTTON} : changer)",
    "0/0/8": f"Modalità: originale ({R_BUTTON}: cambia modo)",
    "0/0/9": f"Modus: Original ({R_BUTTON}: Modus wechseln)",
    "0/1/0": f"Modo: original ({R_BUTTON}: cambiar modo)",
    "0/1/1": f"현재 모드: 원본 ({R_BUTTON}로 전환)",
    "0/1/2": f"当前模式：原版模式（按{R_BUTTON}键切换模式）",
    "0/1/3": f"目前模式：原版模式（按{R_BUTTON}鍵切換模式）",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-romfs", required=True, type=Path)
    parser.add_argument("--output-romfs", required=True, type=Path)
    args = parser.parse_args()

    source_root = Path(__file__).parents[1]
    offline = load_module("mover_offline_messages", source_root / "2-offline_patch" / "patch_messages.py")
    helper = offline.load_archive_helpers()

    for archive in ARCHIVES:
        source = args.source_romfs / "a" / Path(archive)
        destination = args.output_romfs / "a" / Path(archive)
        version, alignment, entries = helper.read_garc(source.read_bytes())
        entry = entries[MESSAGE_FILE_INDEX]
        original = entry.files[0]
        original_lines = helper.read_message_lines(original)
        if len(original_lines) != TITLE_OFFLINE_LINE:
            raise ValueError(f"unexpected stock line count for {archive}: {len(original_lines)}")
        section_offset = helper._u32(original, 12)

        def flags(line: int) -> int:
            return helper._u16(original, section_offset + 4 + line * 8 + 6)

        offline_title = f"{TITLE_HOME_SHORT[archive]}\n{TITLE_OFFLINE[archive]}"
        original_title = f"{TITLE_HOME_SHORT[archive]}\n{TITLE_ORIGINAL[archive]}"
        for mode, text in (("offline", offline_title), ("original", original_title)):
            if len(text) > TITLE_TEXT_BUFFER_LENGTH:
                raise ValueError(
                    f"{archive} {mode} title text exceeds "
                    f"{TITLE_TEXT_BUFFER_LENGTH} characters: {len(text)}"
                )

        entry.files[0] = helper.patch_message_file(
            original,
            {},
            (
                (offline_title, flags(TITLE_HOME_LINE)),
                (original_title, flags(TITLE_HOME_LINE)),
                (offline.INTERNET_MESSAGES[archive], flags(offline.INTERNET_CONNECTION_LINE)),
                (offline.BANK_CONNECTION_MESSAGES[archive], flags(offline.BANK_CONNECTION_LINE)),
                (offline.SAVE_MESSAGES[archive], flags(offline.SAVE_LINE)),
                (offline.DISCONNECT_MESSAGES[archive], flags(offline.DISCONNECT_LINE)),
            ),
        )
        rebuilt = helper.write_garc(version, alignment, entries)
        rebuilt_lines = helper.read_message_lines(
            helper.read_garc(rebuilt)[2][MESSAGE_FILE_INDEX].files[0]
        )
        expected = {
            TITLE_HOME_LINE: original_lines[TITLE_HOME_LINE],
            TITLE_OFFLINE_LINE: offline_title,
            TITLE_ORIGINAL_LINE: original_title,
            INITIAL_CONNECT_LINE: offline.INTERNET_MESSAGES[archive],
            BANK_CONNECT_LINE: offline.BANK_CONNECTION_MESSAGES[archive],
            SAVE_LINE: offline.SAVE_MESSAGES[archive],
            DISCONNECT_LINE: offline.DISCONNECT_MESSAGES[archive],
        }
        for line, value in expected.items():
            if rebuilt_lines[line] != value:
                raise ValueError(f"message verification failed for {archive}, line {line}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(rebuilt)
        print(f"patched {archive} -> {destination}")


if __name__ == "__main__":
    main()
