#!/usr/bin/env python3
"""Build the ten LayeredFS message archives used by the download patch.

构建下载补丁使用的十套 LayeredFS 消息档案。
"""

from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path


ARCHIVES = (
    "0/0/4",
    "0/0/5",
    "0/0/6",
    "0/0/7",
    "0/0/8",
    "0/0/9",
    "0/1/0",
    "0/1/1",
    "0/1/2",
    "0/1/3",
)
MESSAGE_FILE_INDEX = 39
DISCONNECT_LINE = 13
DOWNLOAD_LINE = 14
MENU_LINE = 41
HOME_MENU_LINE = 86
LOCAL_DOWNLOAD_LINE = 96
SUCCESS_DISCONNECT_LINE = 97
BLANK_DISCONNECT_LINE = 98

MESSAGES = {
    "0/0/4": (
        "データをほんたいにダウンロードしました\n"
        "せつだんしています\n"
        "ゲームをおわり　パッチをかえてください",
        "ポケモンバンクからSDへ\n"
        "ダウンロードしています\n"
        "sd:/3ds/Bank/bankdata.bin",
    ),
    "0/0/5": (
        "銀行データを本体にダウンロードしました\n"
        "切断しています\n"
        "終了してパッチを変更してください",
        "ポケモンバンクからSDへダウンロード中\n"
        "sd:/3ds/Bank/bankdata.bin",
    ),
    "0/0/6": (
        "Bank data downloaded locally. Disconnecting...\n"
        "Close the game and change the patch.",
        "Downloading from Pokémon Bank to the local SD card...\n"
        "sd:/3ds/Bank/bankdata.bin",
    ),
    "0/0/7": (
        "Données de Banque téléchargées localement. Déconnexion…\n"
        "Fermez le jeu et changez de patch.",
        "Téléchargement de Banque Pokémon vers la carte SD…\n"
        "sd:/3ds/Bank/bankdata.bin",
    ),
    "0/0/8": (
        "Dati della Banca scaricati localmente. Disconnessione.\n"
        "Chiudi il gioco e cambia la patch.",
        "Download dalla Banca Pokémon alla scheda SD…\n"
        "sd:/3ds/Bank/bankdata.bin",
    ),
    "0/0/9": (
        "Bankdaten lokal heruntergeladen. Verbindung wird getrennt.\n"
        "Spiel beenden und Patch wechseln.",
        "Bankdaten werden auf die SD-Karte heruntergeladen…\n"
        "sd:/3ds/Bank/bankdata.bin",
    ),
    "0/1/0": (
        "Datos del Banco descargados localmente. Desconectando…\n"
        "Cierra el juego y cambia el parche.",
        "Descargando del Banco de Pokémon a la tarjeta SD…\n"
        "sd:/3ds/Bank/bankdata.bin",
    ),
    "0/1/1": (
        "뱅크 데이터를 로컬에 다운로드했습니다.\n"
        "연결 종료 중입니다.\n"
        "게임 종료 후 패치를 변경해 주십시오.",
        "포켓몬 뱅크에서 SD 카드로\n"
        "다운로드 중입니다.\n"
        "sd:/3ds/Bank/bankdata.bin",
    ),
    "0/1/2": (
        "已下载银行数据到本地，正在断开互联网……\n"
        "请关闭游戏并更换补丁。",
        "正在从宝可梦虚拟银行下载数据到本地 SD 卡：\n"
        "sd:/3ds/Bank/bankdata.bin",
    ),
    "0/1/3": (
        "已下載銀行資料到本機，正在關閉網路連線……\n"
        "請關閉遊戲並更換補丁。",
        "正在從寶可夢虛擬銀行下載資料到本機 SD 卡：\n"
        "sd:/3ds/Bank/bankdata.bin",
    ),
}

MENU_MESSAGES = {
    "0/0/4": "ぎんこうデータを　ほんたいにダウンロード",
    "0/0/5": "銀行データを本体にダウンロード",
    "0/0/6": "Download Bank Data",
    "0/0/7": "Télécharger les données",
    "0/0/8": "Scarica dati Banca",
    "0/0/9": "Bankdaten laden",
    "0/1/0": "Descargar datos del Banco",
    "0/1/1": "뱅크 데이터 다운로드",
    "0/1/2": "下载银行数据到本地",
    "0/1/3": "下載銀行資料到本機",
}

LANGUAGE_MENU_MESSAGES = {
    "0/0/4": "げんごを\u3000えらぶ",
    "0/0/5": "言語を選ぶ",
    "0/0/6": "Choose Language",
    "0/0/7": "Choisir la langue",
    "0/0/8": "Scegli la lingua",
    "0/0/9": "Sprache wählen",
    "0/1/0": "Elegir idioma",
    "0/1/1": "언어 선택",
    "0/1/2": "选择语言",
    "0/1/3": "選擇語言",
}

@dataclass
class GarcEntry:
    flags: int
    files: dict[int, bytes]


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _decrypt_line(data: bytes, line_key: int) -> list[int]:
    result: list[int] = []
    key = line_key
    for (encrypted,) in struct.iter_unpack("<H", data):
        result.append(encrypted ^ key)
        key = ((key << 3) | (key >> 13)) & 0xFFFF
    return result


def _encrypt_line(values: list[int], line_key: int) -> bytes:
    output = bytearray()
    key = line_key
    for value in values:
        output += struct.pack("<H", value ^ key)
        key = ((key << 3) | (key >> 13)) & 0xFFFF
    return bytes(output)


def _text_values(text: str) -> list[int]:
    encoded = text.encode("utf-16le")
    values = list(struct.unpack(f"<{len(encoded) // 2}H", encoded))
    values.append(0)
    if len(values) & 1:
        values.append(0)
    return values


def patch_message_file(
    data: bytes,
    replacements: dict[int, str],
    appended_lines: tuple[tuple[str, int], ...] = (),
) -> bytes:
    if len(data) < 0x18 or _u16(data, 0) != 1 or _u32(data, 12) != 0x10:
        raise ValueError("unsupported message-file header")

    line_count = _u16(data, 2)
    section_offset = _u32(data, 12)
    entries_offset = section_offset + 4
    lines: list[tuple[list[int], int]] = []
    line_key = 0x7C89

    for index in range(line_count):
        entry_offset = entries_offset + index * 8
        text_offset, length, flags = struct.unpack_from("<IHH", data, entry_offset)
        start = section_offset + text_offset
        encrypted = data[start : start + length * 2]
        if len(encrypted) != length * 2:
            raise ValueError(f"message line {index} extends past the file")
        values = _decrypt_line(encrypted, line_key)
        if index in replacements:
            values = _text_values(replacements[index])
        lines.append((values, flags))
        line_key = (line_key + 0x2983) & 0xFFFF

    lines.extend((_text_values(text), flags) for text, flags in appended_lines)
    line_count = len(lines)
    section = bytearray(4 + line_count * 8)
    line_key = 0x7C89
    for index, (values, flags) in enumerate(lines):
        text_offset = len(section)
        encrypted = _encrypt_line(values, line_key)
        struct.pack_into("<IHH", section, 4 + index * 8, text_offset, len(values), flags)
        section += encrypted
        while len(section) & 3:
            section.append(0)
        line_key = (line_key + 0x2983) & 0xFFFF

    struct.pack_into("<I", section, 0, len(section))
    header = bytearray(data[:section_offset])
    struct.pack_into("<H", header, 2, line_count)
    struct.pack_into("<I", header, 4, len(section))
    return bytes(header + section)


def read_message_lines(data: bytes) -> list[str]:
    line_count = _u16(data, 2)
    section_offset = _u32(data, 12)
    lines: list[str] = []
    line_key = 0x7C89
    for index in range(line_count):
        entry_offset = section_offset + 4 + index * 8
        text_offset, length, _flags = struct.unpack_from("<IHH", data, entry_offset)
        start = section_offset + text_offset
        values = _decrypt_line(data[start : start + length * 2], line_key)
        if 0 in values:
            values = values[: values.index(0)]
        encoded = struct.pack(f"<{len(values)}H", *values) if values else b""
        lines.append(encoded.decode("utf-16le"))
        line_key = (line_key + 0x2983) & 0xFFFF
    return lines


def read_garc(data: bytes) -> tuple[int, int, list[GarcEntry]]:
    if data[:4] != b"CRAG":
        raise ValueError("not a little-endian GARC archive")
    header_length = _u32(data, 4)
    version = _u16(data, 10)
    alignment = _u32(data, 32) if version == 0x0600 else 4
    fato = header_length
    if data[fato : fato + 4] != b"OTAF":
        raise ValueError("missing FATO section")
    fato_length = _u32(data, fato + 4)
    entry_count = _u16(data, fato + 8)
    fat_offsets = struct.unpack_from(f"<{entry_count}I", data, fato + 12)
    fatb = fato + fato_length
    if data[fatb : fatb + 4] != b"BTAF":
        raise ValueError("missing FATB section")
    fatb_length = _u32(data, fatb + 4)
    fat_table = fatb + 12
    fimb = fatb + fatb_length
    if data[fimb : fimb + 4] != b"BMIF":
        raise ValueError("missing FIMB section")
    data_offset = fimb + _u32(data, fimb + 4)

    entries: list[GarcEntry] = []
    for fat_offset in fat_offsets:
        cursor = fat_table + fat_offset
        flags = _u32(data, cursor)
        cursor += 4
        files: dict[int, bytes] = {}
        for subindex in range(32):
            if flags & (1 << subindex):
                start, _end, length = struct.unpack_from("<III", data, cursor)
                cursor += 12
                files[subindex] = data[data_offset + start : data_offset + start + length]
        entries.append(GarcEntry(flags, files))
    return version, alignment, entries


def write_garc(version: int, alignment: int, entries: list[GarcEntry]) -> bytes:
    if version not in (0x0400, 0x0600):
        raise ValueError(f"unsupported GARC version 0x{version:04X}")
    header_length = 36 if version == 0x0600 else 28
    fato_length = 12 + 4 * len(entries)
    fat_records = bytearray()
    fat_offsets: list[int] = []
    file_data = bytearray()
    largest_unpadded = 0
    largest_padded = 0
    subentry_count = 0

    for entry in entries:
        fat_offsets.append(len(fat_records))
        fat_records += struct.pack("<I", entry.flags)
        for subindex in range(32):
            if not (entry.flags & (1 << subindex)):
                continue
            payload = entry.files[subindex]
            start = len(file_data)
            file_data += payload
            length = len(payload)
            while len(file_data) % alignment:
                file_data.append(0)
            end = len(file_data)
            fat_records += struct.pack("<III", start, end, length)
            largest_unpadded = max(largest_unpadded, length)
            largest_padded = max(largest_padded, end - start)
            subentry_count += 1

    fatb_length = 12 + len(fat_records)
    data_offset = header_length + fato_length + fatb_length + 12
    file_length = data_offset + len(file_data)
    header = bytearray()
    header += struct.pack("<4sIHHIII", b"CRAG", header_length, 0xFEFF, version, 4, data_offset, file_length)
    if version == 0x0600:
        header += struct.pack("<III", largest_padded, largest_unpadded, alignment)
    else:
        header += struct.pack("<I", largest_unpadded)
    fato = struct.pack("<4sIHH", b"OTAF", fato_length, len(entries), 0xFFFF)
    fato += struct.pack(f"<{len(fat_offsets)}I", *fat_offsets)
    fatb = struct.pack("<4sII", b"BTAF", fatb_length, subentry_count) + fat_records
    fimb = struct.pack("<4sII", b"BMIF", 12, len(file_data))
    return bytes(header + fato + fatb + fimb + file_data)


def patch_archive(
    source: Path,
    destination: Path,
    disconnect: str,
    download: str,
    menu: str,
    language_menu: str,
) -> None:
    version, alignment, entries = read_garc(source.read_bytes())
    original_files = [dict(entry.files) for entry in entries]
    message_entry = entries[MESSAGE_FILE_INDEX]
    if message_entry.flags != 1 or 0 not in message_entry.files:
        raise ValueError(f"message entry {MESSAGE_FILE_INDEX} is not a plain file")
    original_message = message_entry.files[0]
    section_offset = _u32(original_message, 12)
    disconnect_flags = _u16(
        original_message, section_offset + 4 + DISCONNECT_LINE * 8 + 6
    )
    download_flags = _u16(
        original_message, section_offset + 4 + DOWNLOAD_LINE * 8 + 6
    )
    original_lines = read_message_lines(original_message)
    message_entry.files[0] = patch_message_file(
        original_message,
        {
            MENU_LINE: menu,
            HOME_MENU_LINE: language_menu,
        },
        (
            (download, download_flags),
            (disconnect, disconnect_flags),
            ("", disconnect_flags),
        ),
    )

    rebuilt = write_garc(version, alignment, entries)
    rebuilt_version, rebuilt_alignment, rebuilt_entries = read_garc(rebuilt)
    if (rebuilt_version, rebuilt_alignment) != (version, alignment):
        raise ValueError("GARC header changed during rebuild")
    for index, rebuilt_entry in enumerate(rebuilt_entries):
        if (
            index != MESSAGE_FILE_INDEX
            and rebuilt_entry.files != original_files[index]
        ):
            raise ValueError(f"unmodified GARC entry {index} changed")
    rebuilt_lines = read_message_lines(rebuilt_entries[MESSAGE_FILE_INDEX].files[0])
    rebuilt_message = rebuilt_entries[MESSAGE_FILE_INDEX].files[0]
    rebuilt_section_offset = _u32(rebuilt_message, 12)
    local_download_flags = _u16(
        rebuilt_message,
        rebuilt_section_offset + 4 + LOCAL_DOWNLOAD_LINE * 8 + 6,
    )
    rebuilt_disconnect_flags = _u16(
        rebuilt_message,
        rebuilt_section_offset + 4 + DISCONNECT_LINE * 8 + 6,
    )
    success_disconnect_flags = _u16(
        rebuilt_message,
        rebuilt_section_offset + 4 + SUCCESS_DISCONNECT_LINE * 8 + 6,
    )
    blank_disconnect_flags = _u16(
        rebuilt_message,
        rebuilt_section_offset + 4 + BLANK_DISCONNECT_LINE * 8 + 6,
    )
    if (
        rebuilt_lines[DISCONNECT_LINE] != original_lines[DISCONNECT_LINE]
        or rebuilt_lines[DOWNLOAD_LINE] != original_lines[DOWNLOAD_LINE]
        or rebuilt_lines[MENU_LINE] != menu
        or rebuilt_lines[HOME_MENU_LINE] != language_menu
        or rebuilt_lines[87:91] != original_lines[87:91]
        or rebuilt_lines[LOCAL_DOWNLOAD_LINE] != download
        or rebuilt_lines[SUCCESS_DISCONNECT_LINE] != disconnect
        or rebuilt_lines[BLANK_DISCONNECT_LINE] != ""
        or local_download_flags != download_flags
        or rebuilt_disconnect_flags != disconnect_flags
        or success_disconnect_flags != disconnect_flags
        or blank_disconnect_flags != disconnect_flags
    ):
        raise ValueError("message verification failed after GARC rebuild")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(rebuilt)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-romfs", required=True, type=Path)
    parser.add_argument("--output-romfs", required=True, type=Path)
    args = parser.parse_args()

    for archive in ARCHIVES:
        source = args.source_romfs / "a" / Path(archive)
        destination = args.output_romfs / "a" / Path(archive)
        if not source.is_file():
            raise FileNotFoundError(f"required RomFS archive not found: {source}")
        disconnect, download = MESSAGES[archive]
        patch_archive(
            source,
            destination,
            disconnect,
            download,
            MENU_MESSAGES[archive],
            LANGUAGE_MENU_MESSAGES[archive],
        )
        print(f"patched {archive} -> {destination}")


if __name__ == "__main__":
    main()
