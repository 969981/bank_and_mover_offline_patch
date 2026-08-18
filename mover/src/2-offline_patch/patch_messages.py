#!/usr/bin/env python3
"""Replace Poke Mover's network lines with local-offline messages.

把 Poke Mover 的原版联网文本替换为本地离线提示。
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


ARCHIVES = ("0/0/4", "0/0/5", "0/0/6", "0/0/7", "0/0/8", "0/0/9",
            "0/1/0", "0/1/1", "0/1/2", "0/1/3")
MESSAGE_FILE_INDEX = 23
INTERNET_CONNECTION_LINE = 13
BANK_CONNECTION_LINE = 15
SAVE_LINE = 9
DISCONNECT_LINE = 14
INTERNET_MESSAGES = {
    "0/0/4": "せつぞくしています……",
    "0/0/5": "接続しています……",
    "0/0/6": "Connecting...",
    "0/0/7": "Connexion…",
    "0/0/8": "Connessione in corso...",
    "0/0/9": "Verbindung wird hergestellt...",
    "0/1/0": "Conectando...",
    "0/1/1": "연결 중입니다…",
    "0/1/2": "正在连接中……",
    "0/1/3": "正在連線中……",
}
BANK_CONNECTION_MESSAGES = {
    "0/0/4": "ローカル オフラインデータに\nせつぞくしています……",
    "0/0/5": "ローカルオフラインデータに\n接続しています……",
    "0/0/6": "Communicating with the local offline\nPokemon Bank data...",
    "0/0/7": "Connexion aux données locales hors ligne\nde Banque Pokémon…",
    "0/0/8": "Connessione ai dati locali offline\ndella Banca Pokémon...",
    "0/0/9": "Verbindung mit den lokalen Offline-Daten\nder Pokémon Bank...",
    "0/1/0": "Conectando con los datos locales sin conexión\ndel Banco de Pokémon...",
    "0/1/1": "로컬 오프라인 포켓몬 뱅크 데이터에\n연결 중입니다…",
    "0/1/2": "正在和宝可梦虚拟银行的\n本地离线数据进行连接……",
    "0/1/3": "正在和寶可夢虛擬銀行的\n本機離線資料進行連線……",
}
SAVE_MESSAGES = {
    "0/0/4": "レポートを\u3000かいて\nポケモンを\u3000ローカル オフラインデータに\nほぞん\u3000しています\nでんげんを\u3000きらないで\u3000ください",
    "0/0/5": "レポートを\u3000書いて\nポケモンをローカルオフラインデータに\n保存しています\n電源を\u3000切らないで\u3000ください",
    "0/0/6": "Your game is being saved and your Pokémon moved\nto the local offline Bank data.\nDon’t turn off the power.",
    "0/0/7": "Sauvegarde du jeu et transfert des Pokémon\nvers les données locales hors ligne…\nNe pas éteindre la console.",
    "0/0/8": "Salvataggio del gioco e dei Pokémon\nnei dati offline locali in corso.\nNon spegnere la console.",
    "0/0/9": "Spielstand und Pokémon werden in den lokalen\nOffline-Bankdaten gespeichert...\nBitte das System nicht ausschalten.",
    "0/1/0": "Guardando la partida y los Pokémon en los datos\nlocales sin conexión del Banco...\nNo apagues la consola.",
    "0/1/1": "리포트를 기록하고 포켓몬을\n로컬 오프라인 데이터에 저장하고 있습니다\n전원을 끄지 않도록 해주십시오",
    "0/1/2": "正在写入记录，\n并将宝可梦写入本地离线数据。\n请勿切断电源。",
    "0/1/3": "正在寫入記錄，\n並將寶可夢寫入本機離線資料。\n請勿關閉電源。",
}
DISCONNECT_MESSAGES = {
    "0/0/4": "せつだん\u3000しています……",
    "0/0/5": "接続を切っています……",
    "0/0/6": "Disconnecting...",
    "0/0/7": "Déconnexion…",
    "0/0/8": "Disconnessione…",
    "0/0/9": "Verbindung wird getrennt...",
    "0/1/0": "Desconectando...",
    "0/1/1": "연결을 종료하는 중입니다…",
    "0/1/2": "正在断开连接……",
    "0/1/3": "正在中斷連線……",
}


def load_archive_helpers():
    # Reuse the repository's independently implemented GARC/message codec.
    # 复用本仓库自行实现的 GARC/消息编解码器。
    helper_path = Path(__file__).parents[3] / "bank" / "src" / "1-download_patch" / "patch_messages.py"
    spec = importlib.util.spec_from_file_location("bank_message_archive", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load message helper: {helper_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-romfs", required=True, type=Path)
    parser.add_argument("--output-romfs", required=True, type=Path)
    args = parser.parse_args()
    helper = load_archive_helpers()

    for archive in ARCHIVES:
        source = args.source_romfs / "a" / Path(archive)
        destination = args.output_romfs / "a" / Path(archive)
        version, alignment, entries = helper.read_garc(source.read_bytes())
        entry = entries[MESSAGE_FILE_INDEX]
        entry.files[0] = helper.patch_message_file(
            entry.files[0],
            {
                INTERNET_CONNECTION_LINE: INTERNET_MESSAGES[archive],
                BANK_CONNECTION_LINE: BANK_CONNECTION_MESSAGES[archive],
                SAVE_LINE: SAVE_MESSAGES[archive],
                DISCONNECT_LINE: DISCONNECT_MESSAGES[archive],
            },
        )
        rebuilt = helper.write_garc(version, alignment, entries)
        check_entries = helper.read_garc(rebuilt)[2]
        lines = helper.read_message_lines(check_entries[MESSAGE_FILE_INDEX].files[0])
        if lines[INTERNET_CONNECTION_LINE] != INTERNET_MESSAGES[archive]:
            raise ValueError(f"Internet-message verification failed: {archive}")
        if lines[BANK_CONNECTION_LINE] != BANK_CONNECTION_MESSAGES[archive]:
            raise ValueError(f"Bank-message verification failed: {archive}")
        if lines[SAVE_LINE] != SAVE_MESSAGES[archive]:
            raise ValueError(f"save-message verification failed: {archive}")
        if lines[DISCONNECT_LINE] != DISCONNECT_MESSAGES[archive]:
            raise ValueError(f"disconnect-message verification failed: {archive}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(rebuilt)
        print(f"patched {archive} -> {destination}")


if __name__ == "__main__":
    main()
