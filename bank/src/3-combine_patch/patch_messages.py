"""Build the ten localized resources used by the combined Bank patch.

构建合并 Bank 补丁使用的十套本地化资源。
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SOURCE_ROOT = Path(__file__).parents[1]
OFFLINE = load_module("combine_offline_messages", SOURCE_ROOT / "2-offline_patch" / "patch_messages.py")
HELPER = load_module("combine_message_archive", SOURCE_ROOT / "1-download_patch" / "patch_messages.py")

SUPPORT_LINE = 43
MOVER_DOWNLOAD_LINE = 44
MOVER_INSTALLED_LINE = 45
HOME_LINE = 86
TITLE_HOME_LINE = 77
TITLE_VERSION_LINE = 78
MENU_MESSAGE_FILE_INDEX = 37
MENU_GREETING_LINE = 17
OFFLINE_MENU_GREETING_LINE = 27
DOWNLOAD_MENU_GREETING_LINE = 28
BLANK_LINE = 96
DOWNLOAD_PROGRESS_LINE = 97
DOWNLOAD_SUCCESS_LINE = 98
DOWNLOAD_USE_BANK_LINE = 99
OFFLINE_INITIAL_CONNECT_LINE = 100
OFFLINE_BANK_CONNECTION_LINE = 101
OFFLINE_SAVE_LINE = 102
OFFLINE_DISCONNECT_LINE = 103
TITLE_MODE_OFFLINE_LINE = 104
TITLE_MODE_DOWNLOAD_LINE = 105
DISABLED_LINE = 106
LANGUAGE_MENU_LINE = 107
DOWNLOAD_GAME_SELECTION_LINE = 108
TITLE_TEXT_BUFFER_LENGTH = 54

DISABLED_MESSAGES = {
    "0/0/4": "つかえません",
    "0/0/5": "使用できません",
    "0/0/6": "Disabled",
    "0/0/7": "Indisponible",
    "0/0/8": "Non disponibile",
    "0/0/9": "Deaktiviert",
    "0/1/0": "Desactivado",
    "0/1/1": "사용할 수 없습니다",
    "0/1/2": "已禁用",
    "0/1/3": "已停用",
}

# These stock greetings occupy multiple lines in the listed archives. Keep
# their original meaning in a one-line form so the mode explanation remains
# visible without requiring an extra page advance.
# 下列语言的原版欢迎语会占用多行。将其含义保留为一行，使后续模式说明无需翻页
# 即可显示。
SHORT_MENU_GREETINGS = {
    "0/0/4": "ポケモンバンクへ ようこそ！",
    "0/0/5": "ポケモンバンクへようこそ！",
    "0/0/6": "Welcome to Pokémon Bank!",
    "0/1/1": "포켓몬 뱅크에 어서 와!",
}

# Use the same private-use R-button glyph in every localized title hint.
# 所有语言的标题提示统一使用同一个专用区 R 键字形。
R_BUTTONS = {
    "0/0/4": "\ue005",
    "0/0/5": "\ue005",
    "0/0/6": "\ue005",
    "0/0/7": "\ue005",
    "0/0/8": "\ue005",
    "0/0/9": "\ue005",
    "0/1/0": "\ue005",
    "0/1/1": "\ue005",
    "0/1/2": "\ue005",
    "0/1/3": "\ue005",
}

# The Western stock HOME sentences leave too little room for a localized
# mode-switch instruction inside the title pane's 54-character buffer.
# 西欧语言的原版 HOME 句子会挤占标题窗格的 54 字符缓冲区，因此使用本地化短句为
# 完整的模式切换说明留出空间。
SHORT_TITLE_HOME_MESSAGES = {
    "0/0/6": "Press\ue073: HOME Menu",
    "0/0/7": "Appuyez\ue073: menu HOME",
    "0/0/8": "Premi\ue073: menu HOME",
    "0/0/9": "\ue073drücken: HOME-Menü",
    "0/1/0": "Pulsa\ue073: menú HOME",
}

# Two appended BMG entries replace the wide bottom HOME-help line while the
# stock version pane remains unchanged. The title hook rebinds this line after
# each R press.
# 两条追加 BMG 条目替换宽大的底部 HOME 帮助行，原版版本号窗格保持不变。标题钩子会在
# 每次按下 R 后重新绑定该行。
TITLE_MODE_OFFLINE_MESSAGES = {
    "0/0/4": f"現在のモード：オフライン（{R_BUTTONS['0/0/4']}で切替）",
    "0/0/5": f"現在のモード：オフライン（{R_BUTTONS['0/0/5']}で切替）",
    "0/0/6": f"Mode: Offline ({R_BUTTONS['0/0/6']}:switch mode)",
    "0/0/7": f"Mode: Hors ligne ({R_BUTTONS['0/0/7']}:changer)",
    "0/0/8": f"Modalità: Offline ({R_BUTTONS['0/0/8']}:cambia modo)",
    "0/0/9": f"Modus: Offline({R_BUTTONS['0/0/9']}:Modus wechseln)",
    "0/1/0": f"Modo: Sin conexión ({R_BUTTONS['0/1/0']}:cambiar modo)",
    "0/1/1": f"현재 모드: 오프라인 ({R_BUTTONS['0/1/1']}으로 전환)",
    "0/1/2": f"当前模式：离线模式（按{R_BUTTONS['0/1/2']}键切换模式）",
    "0/1/3": f"目前模式：離線模式（按{R_BUTTONS['0/1/3']}鍵切換模式）",
}

TITLE_MODE_DOWNLOAD_MESSAGES = {
    "0/0/4": f"現在のモード：ダウンロード（{R_BUTTONS['0/0/4']}で切替）",
    "0/0/5": f"現在のモード：ダウンロード（{R_BUTTONS['0/0/5']}で切替）",
    "0/0/6": f"Mode: Download ({R_BUTTONS['0/0/6']}:switch mode)",
    "0/0/7": f"Mode: Téléchargement ({R_BUTTONS['0/0/7']}:changer)",
    "0/0/8": f"Modalità: Download ({R_BUTTONS['0/0/8']}:cambia modo)",
    "0/0/9": f"Modus: Download({R_BUTTONS['0/0/9']}:Modus wechseln)",
    "0/1/0": f"Modo: Descarga ({R_BUTTONS['0/1/0']}:cambiar modo)",
    "0/1/1": f"현재 모드: 다운로드 ({R_BUTTONS['0/1/1']}으로 전환)",
    "0/1/2": f"当前模式：下载模式（按{R_BUTTONS['0/1/2']}键切换模式）",
    "0/1/3": f"目前模式：下載模式（按{R_BUTTONS['0/1/3']}鍵切換模式）",
}

# Keep the four state-specific offline message sets visible in this combined
# source while continuing to use the already verified Step 2 translations.
# 在本合并源码中明确列出四组状态专用离线文本，同时继续使用已验证的第 2 步翻译。
OFFLINE_INITIAL_CONNECT_MESSAGES = OFFLINE.INTERNET_MESSAGES
OFFLINE_BANK_CONNECTION_MESSAGES = OFFLINE.BANK_CONNECTION_MESSAGES
OFFLINE_SAVE_MESSAGES = OFFLINE.SAVE_MESSAGES
OFFLINE_DISCONNECT_MESSAGES = OFFLINE.DISCONNECT_MESSAGES

OFFLINE_MENU_GREETINGS = {
    "0/0/4": "げんざいのモード：オフラインモード\nローカルデータは サーバーデータと べつです",
    "0/0/5": "現在のモード：オフラインモード\nローカルデータはサーバーデータと別です",
    "0/0/6": "Current Mode: Offline Mode\nLocal Bank data is separate from server data.",
    "0/0/7": "Mode actuel : Mode hors ligne\nLes données locales sont séparées du serveur.",
    "0/0/8": "Modalità attuale: Offline\nI dati locali sono separati dal server.",
    "0/0/9": "Aktueller Modus: Offline\nLokale Daten sind von Serverdaten getrennt.",
    "0/1/0": "Modo actual: Sin conexión\nLos datos locales son independientes del servidor.",
    "0/1/1": "현재 모드: 오프라인 모드\n로컬 뱅크 데이터는 서버 데이터와 분리됩니다.",
    "0/1/2": "当前模式：离线模式\n本地银行数据与服务器数据彼此独立。",
    "0/1/3": "目前模式：離線模式\n本機銀行資料與伺服器資料彼此獨立。",
}

DOWNLOAD_MENU_GREETINGS = {
    "0/0/4": "げんざいのモード：ダウンロードモード\nサーバーのデータを ほんたいに ほぞんして うわがきします",
    "0/0/5": "現在のモード：ダウンロードモード\nサーバーのデータを本体に保存して上書きします",
    "0/0/6": "Current Mode: Download Mode\nServer data is downloaded to SD and overwrites local data.",
    "0/0/7": "Mode actuel : Téléchargement\nLes données du serveur remplaceront les données locales.",
    "0/0/8": "Modalità attuale: Download\nI dati del server sovrascriveranno quelli locali.",
    "0/0/9": "Aktueller Modus: Download\nServerdaten überschreiben lokale Bankdaten.",
    "0/1/0": "Modo actual: Descarga\nLos datos del servidor reemplazarán los datos locales.",
    "0/1/1": "현재 모드: 다운로드 모드\n서버 데이터를 로컬 뱅크 데이터에 덮어씁니다.",
    "0/1/2": "当前模式：下载模式\n将服务器银行数据下载到本地并覆盖现有数据。",
    "0/1/3": "目前模式：下載模式\n將伺服器銀行資料下載到本機並覆蓋現有資料。",
}

DOWNLOAD_SUCCESS_MESSAGES = {
    "0/0/4": "ぎんこうデータを SDカードに\nダウンロードしました\nタイトルにもどります……",
    "0/0/5": "銀行データをSDカードに\nダウンロードしました\nタイトルに戻ります……",
    "0/0/6": "Bank data was downloaded to the local SD card.\nReturning to the title screen...",
    "0/0/7": "Les données de Banque ont été téléchargées\nsur la carte SD locale. Retour à l’écran-titre…",
    "0/0/8": "I dati della Banca sono stati scaricati\nsulla scheda SD locale. Ritorno al titolo...",
    "0/0/9": "Bankdaten wurden auf die lokale SD-Karte\ngeladen. Rückkehr zum Titelbildschirm...",
    "0/1/0": "Los datos del Banco se descargaron\nen la tarjeta SD local. Volviendo al título...",
    "0/1/1": "뱅크 데이터를 로컬 SD 카드에\n다운로드했습니다. 타이틀 화면으로 돌아갑니다…",
    "0/1/2": "已将银行数据下载到本地 SD 卡。\n正在返回标题界面……",
    "0/1/3": "已將銀行資料下載到本機 SD 卡。\n正在返回標題畫面……",
}

DOWNLOAD_GAME_SELECTION_MESSAGES = {
    "0/0/4": "どのゲームソフトでも\nかんぜんな ぎんこうデータを\nSDカードに ダウンロードできます。",
    "0/0/5": "どのゲームソフトを選んでも\n完全な銀行データを本体に\nダウンロードできます。",
    "0/0/6": "Select any game software to download\nthe complete Bank data to local storage.",
    "0/0/7": "Sélectionnez n’importe quel jeu pour\ntélécharger toutes les données de Banque\nen local.",
    "0/0/8": "Seleziona un gioco qualsiasi per\nscaricare localmente tutti i dati\ndella Banca.",
    "0/0/9": "Wähle ein beliebiges Spiel, um\nalle Bankdaten lokal herunterzuladen.",
    "0/1/0": "Elige cualquier juego para descargar\nlocalmente todos los datos del Banco.",
    "0/1/1": "어떤 게임 소프트웨어를 선택해도\n전체 뱅크 데이터를 로컬에\n다운로드할 수 있습니다.",
    "0/1/2": "选择任意游戏软件，\n均可将完整银行数据下载到本地。",
    "0/1/3": "選擇任意遊戲軟體，\n均可將完整銀行資料下載到本機。",
}


def verify_kana_archive_messages() -> None:
    """Reject kanji in every custom string emitted for the kana-only archive.

    拒绝写入假名专用文本库的任何自定义汉字。
    """
    archive = "0/0/4"
    # The stock HOME hint in this archive already contains kanji. Its two
    # appended title-mode variants intentionally follow the same convention;
    # the remaining custom messages stay kana-only.
    # 此档案的原版 HOME 提示本身已包含汉字，因此追加的两条标题模式文本也有意
    # 使用相同写法；其余自定义文本仍保持纯假名。
    texts = (
        DISABLED_MESSAGES[archive],
        OFFLINE_INITIAL_CONNECT_MESSAGES[archive],
        OFFLINE_BANK_CONNECTION_MESSAGES[archive],
        OFFLINE_SAVE_MESSAGES[archive],
        OFFLINE_DISCONNECT_MESSAGES[archive],
        OFFLINE_MENU_GREETINGS[archive],
        DOWNLOAD_MENU_GREETINGS[archive],
        DOWNLOAD_SUCCESS_MESSAGES[archive],
        HELPER.MESSAGES[archive][0],
        HELPER.MESSAGES[archive][1],
        HELPER.MENU_MESSAGES[archive],
        HELPER.LANGUAGE_MENU_MESSAGES[archive],
        DOWNLOAD_GAME_SELECTION_MESSAGES[archive],
    )
    for text in texts:
        kanji = [char for char in text if "\u3400" <= char <= "\u9fff" or "\uf900" <= char <= "\ufaff"]
        if kanji:
            raise ValueError(f"kana archive contains kanji: {''.join(kanji)} in {text!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-romfs", required=True, type=Path)
    parser.add_argument("--output-romfs", required=True, type=Path)
    parser.add_argument(
        "--title-r-glyph-test",
        action="store_true",
        help="append only the private-use R glyph to the stock HOME line",
    )
    args = parser.parse_args()
    verify_kana_archive_messages()

    for archive in OFFLINE.ARCHIVES:
        source = args.source_romfs / "a" / Path(archive)
        destination = args.output_romfs / "a" / Path(archive)
        version, alignment, entries = HELPER.read_garc(source.read_bytes())
        entry = entries[OFFLINE.MESSAGE_FILE_INDEX]
        original = entry.files[0]
        original_lines = HELPER.read_message_lines(original)
        section_offset = HELPER._u32(original, 12)
        disconnect_flags = HELPER._u16(
            original, section_offset + 4 + OFFLINE.DISCONNECT_LINE * 8 + 6
        )
        bank_flags = HELPER._u16(
            original, section_offset + 4 + OFFLINE.BANK_CONNECTION_LINE * 8 + 6
        )
        use_bank_flags = HELPER._u16(
            original, section_offset + 4 + HELPER.MENU_LINE * 8 + 6
        )
        game_selection_flags = HELPER._u16(
            original, section_offset + 4 + 3 * 8 + 6
        )
        title_mode_flags = HELPER._u16(
            original, section_offset + 4 + TITLE_HOME_LINE * 8 + 6
        )
        internet_flags = HELPER._u16(
            original, section_offset + 4 + OFFLINE.INTERNET_CONNECTION_LINE * 8 + 6
        )
        save_flags = HELPER._u16(
            original, section_offset + 4 + OFFLINE.SAVE_LINE * 8 + 6
        )
        if args.title_r_glyph_test:
            # Diagnostic archive: isolate private-use glyph rendering from
            # multiline layout and localized text length.
            # 诊断档案：将专用区字形渲染与多行布局、本地化文本长度完全分离。
            title_mode_offline = original_lines[TITLE_HOME_LINE] + R_BUTTONS[archive]
            title_mode_download = title_mode_offline
        else:
            title_home = SHORT_TITLE_HOME_MESSAGES.get(
                archive, original_lines[TITLE_HOME_LINE]
            )
            title_mode_offline = (
                f"{title_home}\n"
                f"{TITLE_MODE_OFFLINE_MESSAGES[archive]}"
            )
            title_mode_download = (
                f"{title_home}\n"
                f"{TITLE_MODE_DOWNLOAD_MESSAGES[archive]}"
            )
        # The stock title TextBox reserves 54 UTF-16 characters. The renderer
        # clears the whole pane instead of truncating an oversized string.
        # 原版标题 TextBox 仅预留 54 个 UTF-16 字符；越界时渲染器会清空整个
        # 文本窗格，而不是截断字符串。
        for mode_name, title_text in (
            ("offline", title_mode_offline),
            ("download", title_mode_download),
        ):
            if len(title_text) > TITLE_TEXT_BUFFER_LENGTH:
                raise ValueError(
                    f"{archive} {mode_name} title text exceeds "
                    f"{TITLE_TEXT_BUFFER_LENGTH} characters: {len(title_text)}"
                )
        entry.files[0] = HELPER.patch_message_file(
            original,
            {},
            (
                ("", disconnect_flags),
                (HELPER.MESSAGES[archive][1], bank_flags),
                (DOWNLOAD_SUCCESS_MESSAGES[archive], disconnect_flags),
                (HELPER.MENU_MESSAGES[archive], use_bank_flags),
                (OFFLINE_INITIAL_CONNECT_MESSAGES[archive], internet_flags),
                (OFFLINE_BANK_CONNECTION_MESSAGES[archive], bank_flags),
                (OFFLINE_SAVE_MESSAGES[archive], save_flags),
                (OFFLINE_DISCONNECT_MESSAGES[archive], disconnect_flags),
                (title_mode_offline, title_mode_flags),
                (title_mode_download, title_mode_flags),
                (DISABLED_MESSAGES[archive], use_bank_flags),
                (HELPER.LANGUAGE_MENU_MESSAGES[archive], use_bank_flags),
                (DOWNLOAD_GAME_SELECTION_MESSAGES[archive], game_selection_flags),
            ),
        )
        greeting_entry = entries[MENU_MESSAGE_FILE_INDEX]
        greeting_original = greeting_entry.files[0]
        greeting_section_offset = HELPER._u32(greeting_original, 12)
        greeting_flags = HELPER._u16(
            greeting_original, greeting_section_offset + 4 + MENU_GREETING_LINE * 8 + 6
        )
        # Keep the stock line untouched and append two complete mode-specific
        # alternatives. Each alternative starts with the stock greeting (or
        # its one-line equivalent) and then adds the selected-mode explanation.
        # 原版行保持不变，另行追加两条完整的模式文本。每条先放原版欢迎语（或其
        # 一行等义版本），再追加所选模式说明。
        greeting_original_lines = HELPER.read_message_lines(greeting_original)
        menu_greeting = SHORT_MENU_GREETINGS.get(
            archive, greeting_original_lines[MENU_GREETING_LINE]
        )
        offline_menu_greeting = (
            f"{menu_greeting}\n"
            f"{OFFLINE_MENU_GREETINGS[archive]}"
        )
        download_menu_greeting = (
            f"{menu_greeting}\n"
            f"{DOWNLOAD_MENU_GREETINGS[archive]}"
        )
        greeting_entry.files[0] = HELPER.patch_message_file(
            greeting_original,
            {},
            (
                (offline_menu_greeting, greeting_flags),
                (download_menu_greeting, greeting_flags),
            ),
        )
        rebuilt = HELPER.write_garc(version, alignment, entries)
        rebuilt_entries = HELPER.read_garc(rebuilt)[2]
        rebuilt_lines = HELPER.read_message_lines(
            rebuilt_entries[OFFLINE.MESSAGE_FILE_INDEX].files[0]
        )
        rebuilt_greetings = HELPER.read_message_lines(
            rebuilt_entries[MENU_MESSAGE_FILE_INDEX].files[0]
        )
        expected = {
            SUPPORT_LINE: original_lines[SUPPORT_LINE],
            MOVER_DOWNLOAD_LINE: original_lines[MOVER_DOWNLOAD_LINE],
            MOVER_INSTALLED_LINE: original_lines[MOVER_INSTALLED_LINE],
            HOME_LINE: original_lines[HOME_LINE],
            BLANK_LINE: "",
            DOWNLOAD_PROGRESS_LINE: HELPER.MESSAGES[archive][1],
            DOWNLOAD_SUCCESS_LINE: DOWNLOAD_SUCCESS_MESSAGES[archive],
            DOWNLOAD_USE_BANK_LINE: HELPER.MENU_MESSAGES[archive],
            OFFLINE_INITIAL_CONNECT_LINE: OFFLINE_INITIAL_CONNECT_MESSAGES[archive],
            OFFLINE_BANK_CONNECTION_LINE: OFFLINE_BANK_CONNECTION_MESSAGES[archive],
            OFFLINE_SAVE_LINE: OFFLINE_SAVE_MESSAGES[archive],
            OFFLINE_DISCONNECT_LINE: OFFLINE_DISCONNECT_MESSAGES[archive],
            TITLE_MODE_OFFLINE_LINE: title_mode_offline,
            TITLE_MODE_DOWNLOAD_LINE: title_mode_download,
            DISABLED_LINE: DISABLED_MESSAGES[archive],
            LANGUAGE_MENU_LINE: HELPER.LANGUAGE_MENU_MESSAGES[archive],
            DOWNLOAD_GAME_SELECTION_LINE: DOWNLOAD_GAME_SELECTION_MESSAGES[archive],
        }
        for index, value in expected.items():
            if rebuilt_lines[index] != value:
                raise ValueError(f"message verification failed for {archive}, line {index}")
        if rebuilt_greetings[OFFLINE_MENU_GREETING_LINE] != offline_menu_greeting:
            raise ValueError(f"offline-menu greeting verification failed for {archive}")
        if rebuilt_greetings[DOWNLOAD_MENU_GREETING_LINE] != download_menu_greeting:
            raise ValueError(f"download-menu greeting verification failed for {archive}")
        if rebuilt_greetings[MENU_GREETING_LINE] != greeting_original_lines[MENU_GREETING_LINE]:
            raise ValueError(f"stock-menu greeting verification failed for {archive}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(rebuilt)
        print(f"patched {archive} -> {destination}")


if __name__ == "__main__":
    main()
