"""Independent UI wording for the read-only bankdata viewer.

The strings in this file describe observed data roles.  They deliberately do
not reuse internal program identifiers.  Localized species names are read
from fixed local resources by :mod:`text_resources`.
"""

from __future__ import annotations


LANGUAGE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("ja-kana", "にほんご（かな）"),
    ("ja-kanji", "日本語（漢字）"),
    ("en", "English"),
    ("de", "Deutsch"),
    ("it", "Italiano"),
    ("fr", "Français"),
    ("es", "Español"),
    ("ko", "한국어"),
    ("zh-Hans", "简体中文"),
    ("zh-Hant", "繁體中文"),
)
LANGUAGE_CODES = tuple(code for code, _label in LANGUAGE_OPTIONS)


UI: dict[str, dict[str, str]] = {
    "ja-kana": {
        "title": "ポケモンバンク bankdata びゅーあ", "open": "bankdata を ひらく", "language": "ひょうじ げんご",
        "groups": "ぐるーぷ と ぼっくす", "box": "ぼっくす", "transfer": "てんそうぼっくす", "empty": "から",
        "overview": "ふぁいる がいよう", "sources": "げーむ きろく", "boxmeta": "ぼっくすべつ めたでーた", "slotmeta": "えらんだ ぼっくすの すろっと めたでーた", "structure": "くわしい めたでーた", "creature": "ポケモン しょうさい",
        "field": "こうもく", "value": "ないよう", "description": "せつめい", "game": "げーむ", "player": "ぷれいやーめい", "sex": "せいべつ", "trainer": "とれーなー ID",
        "format": "けいしき", "format6": "だい6せだい けいしき", "format7": "だい7せだい けいしき", "origin": "もと", "latest": "さいしんの こうしん", "slots": "すろっと", "count": "かず",
        "privacy": "この ふぁいるには ぷれいやーめい、ID、こゆう ばんごうが ふくまれる ばあいが あります。 そのまま こうかいしないで ください。",
        "loaded": "よみこみ かんりょう", "no_file": "bankdata.bin または かんぜんな おぶじぇくと だんぷを ひらいてください。", "invalid": "ふぁいるの おおきさが ただしくありません",
        "male": "おす", "female": "めす", "unknown": "ふめい", "all": "すべて", "number": "ばんごう", "code": "こーど", "raw_time": "もとの じかんち", "nickname": "にっくねーむ",
        "select_slot": "ぼっくすの ますを えらぶと、ここに しょうさいを ひょうじします。",
    },
    "ja-kanji": {
        "title": "ポケモンバンク bankdata ビューア", "open": "bankdataを開く", "language": "表示言語",
        "groups": "グループとボックス", "box": "ボックス", "transfer": "転送ボックス", "empty": "空き",
        "overview": "ファイル概要", "sources": "ゲーム記録", "boxmeta": "ボックス別メタデータ", "slotmeta": "選択中ボックスのスロットメタデータ", "structure": "詳細メタデータ", "creature": "ポケモン詳細",
        "field": "項目", "value": "値", "description": "説明", "game": "ゲーム", "player": "プレイヤー名", "sex": "性別", "trainer": "トレーナーID",
        "format": "形式", "format6": "第6世代形式", "format7": "第7世代形式", "origin": "由来", "latest": "最終更新", "slots": "スロット", "count": "数",
        "privacy": "このファイルにはプレイヤー名、トレーナーID、固有番号が含まれる場合があります。直接公開しないでください。",
        "loaded": "読み込み済み", "no_file": "bankdata.bin または完全なオブジェクトダンプを開いてください。", "invalid": "ファイルサイズが正しくありません",
        "male": "男", "female": "女", "unknown": "不明", "all": "すべて", "number": "番号", "code": "コード", "raw_time": "生の時刻値", "nickname": "ニックネーム",
        "select_slot": "ボックス内の枠を選ぶと、ここに詳細を表示します。",
    },
    "en": {
        "title": "Pokémon Bank bankdata Viewer", "open": "Open bankdata", "language": "Language",
        "groups": "Groups and Boxes", "box": "Box", "transfer": "Transfer Box", "empty": "Empty",
        "overview": "File Overview", "sources": "Game Records", "boxmeta": "Per-box Metadata", "slotmeta": "Selected Box Slot Metadata", "structure": "Detailed Metadata", "creature": "Pokémon Details",
        "field": "Field", "value": "Value", "description": "Description", "game": "Game", "player": "Player", "sex": "Sex", "trainer": "Trainer ID",
        "format": "Format", "format6": "Generation 6 format", "format7": "Generation 7 format", "origin": "Origin", "latest": "Latest update", "slots": "Slots", "count": "Count",
        "privacy": "This file may contain player names, Trainer IDs, and a unique object ID. Do not publish it directly.",
        "loaded": "Loaded", "no_file": "Open bankdata.bin or a complete object dump.", "invalid": "Invalid file size",
        "male": "Male", "female": "Female", "unknown": "Unknown", "all": "All", "number": "Number", "code": "Code", "raw_time": "Raw time value", "nickname": "Nickname",
        "select_slot": "Select a box cell to display its details here.",
    },
    "de": {
        "title": "Pokémon Bank bankdata-Betrachter", "open": "bankdata öffnen", "language": "Sprache",
        "groups": "Gruppen und Boxen", "box": "Box", "transfer": "Transfer-Box", "empty": "Leer",
        "overview": "Dateiübersicht", "sources": "Spielaufzeichnungen", "boxmeta": "Metadaten je Box", "slotmeta": "Slot-Metadaten der gewählten Box", "structure": "Detaillierte Metadaten", "creature": "Pokémon-Details",
        "field": "Feld", "value": "Wert", "description": "Beschreibung", "game": "Spiel", "player": "Spieler", "sex": "Geschlecht", "trainer": "Trainer-ID",
        "format": "Format", "format6": "Format der 6. Generation", "format7": "Format der 7. Generation", "origin": "Herkunft", "latest": "Letzte Aktualisierung", "slots": "Plätze", "count": "Anzahl",
        "privacy": "Diese Datei kann Spielernamen, Trainer-IDs und eine eindeutige Objekt-ID enthalten. Nicht unverändert veröffentlichen.",
        "loaded": "Geladen", "no_file": "Öffne bankdata.bin oder einen vollständigen Objektdump.", "invalid": "Ungültige Dateigröße",
        "male": "Männlich", "female": "Weiblich", "unknown": "Unbekannt", "all": "Alle", "number": "Nummer", "code": "Code", "raw_time": "Rohzeitwert", "nickname": "Spitzname",
        "select_slot": "Wähle ein Feld in der Box, um die Details hier anzuzeigen.",
    },
    "it": {
        "title": "Visualizzatore bankdata di Pokémon Bank", "open": "Apri bankdata", "language": "Lingua",
        "groups": "Gruppi e Box", "box": "Box", "transfer": "Box trasferimento", "empty": "Vuoto",
        "overview": "Panoramica file", "sources": "Registri dei giochi", "boxmeta": "Metadati per Box", "slotmeta": "Metadati slot della Box selezionata", "structure": "Metadati dettagliati", "creature": "Dettagli Pokémon",
        "field": "Campo", "value": "Valore", "description": "Descrizione", "game": "Gioco", "player": "Giocatore", "sex": "Sesso", "trainer": "ID Allenatore",
        "format": "Formato", "format6": "Formato di sesta generazione", "format7": "Formato di settima generazione", "origin": "Origine", "latest": "Ultimo aggiornamento", "slots": "Slot", "count": "Numero",
        "privacy": "Questo file può contenere nomi dei giocatori, ID Allenatore e un ID oggetto univoco. Non pubblicarlo direttamente.",
        "loaded": "Caricato", "no_file": "Apri bankdata.bin o un dump completo dell'oggetto.", "invalid": "Dimensione file non valida",
        "male": "Maschio", "female": "Femmina", "unknown": "Sconosciuto", "all": "Tutti", "number": "Numero", "code": "Codice", "raw_time": "Valore temporale grezzo", "nickname": "Soprannome",
        "select_slot": "Seleziona una cella della Box per visualizzarne qui i dettagli.",
    },
    "fr": {
        "title": "Visionneuse bankdata de Banque Pokémon", "open": "Ouvrir bankdata", "language": "Langue",
        "groups": "Groupes et Boîtes", "box": "Boîte", "transfer": "Boîte Transfert", "empty": "Vide",
        "overview": "Aperçu du fichier", "sources": "Enregistrements des jeux", "boxmeta": "Métadonnées par Boîte", "slotmeta": "Métadonnées des emplacements de la Boîte sélectionnée", "structure": "Métadonnées détaillées", "creature": "Détails du Pokémon",
        "field": "Champ", "value": "Valeur", "description": "Description", "game": "Jeu", "player": "Joueur", "sex": "Sexe", "trainer": "ID Dresseur",
        "format": "Format", "format6": "Format de sixième génération", "format7": "Format de septième génération", "origin": "Origine", "latest": "Dernière mise à jour", "slots": "Emplacements", "count": "Nombre",
        "privacy": "Ce fichier peut contenir des noms de joueurs, des ID Dresseur et un identifiant d'objet unique. Ne le publiez pas directement.",
        "loaded": "Chargé", "no_file": "Ouvrez bankdata.bin ou un vidage complet de l'objet.", "invalid": "Taille de fichier invalide",
        "male": "Mâle", "female": "Femelle", "unknown": "Inconnu", "all": "Tous", "number": "Numéro", "code": "Code", "raw_time": "Valeur horaire brute", "nickname": "Surnom",
        "select_slot": "Sélectionnez une case de la Boîte pour afficher ses détails ici.",
    },
    "es": {
        "title": "Visor de bankdata de Banco de Pokémon", "open": "Abrir bankdata", "language": "Idioma",
        "groups": "Grupos y Cajas", "box": "Caja", "transfer": "Caja de transferencia", "empty": "Vacío",
        "overview": "Resumen del archivo", "sources": "Registros de juegos", "boxmeta": "Metadatos por Caja", "slotmeta": "Metadatos de ranuras de la Caja seleccionada", "structure": "Metadatos detallados", "creature": "Detalles del Pokémon",
        "field": "Campo", "value": "Valor", "description": "Descripción", "game": "Juego", "player": "Jugador", "sex": "Sexo", "trainer": "ID de Entrenador",
        "format": "Formato", "format6": "Formato de sexta generación", "format7": "Formato de séptima generación", "origin": "Origen", "latest": "Última actualización", "slots": "Ranuras", "count": "Cantidad",
        "privacy": "Este archivo puede contener nombres de jugadores, ID de Entrenador y un identificador de objeto único. No lo publiques directamente.",
        "loaded": "Cargado", "no_file": "Abre bankdata.bin o un volcado completo del objeto.", "invalid": "Tamaño de archivo no válido",
        "male": "Macho", "female": "Hembra", "unknown": "Desconocido", "all": "Todos", "number": "Número", "code": "Código", "raw_time": "Valor de hora sin procesar", "nickname": "Apodo",
        "select_slot": "Selecciona una celda de la Caja para mostrar aquí sus detalles.",
    },
    "ko": {
        "title": "포켓몬 뱅크 bankdata 뷰어", "open": "bankdata 열기", "language": "표시 언어",
        "groups": "그룹과 박스", "box": "박스", "transfer": "전송 박스", "empty": "비어 있음",
        "overview": "파일 개요", "sources": "게임 기록", "boxmeta": "박스별 메타데이터", "slotmeta": "선택한 박스의 슬롯 메타데이터", "structure": "상세 메타데이터", "creature": "포켓몬 상세",
        "field": "항목", "value": "값", "description": "설명", "game": "게임", "player": "플레이어 이름", "sex": "성별", "trainer": "트레이너 ID",
        "format": "형식", "format6": "6세대 형식", "format7": "7세대 형식", "origin": "출처", "latest": "최근 갱신", "slots": "슬롯", "count": "개수",
        "privacy": "이 파일에는 플레이어 이름, 트레이너 ID 및 고유 객체 ID가 들어 있을 수 있습니다. 그대로 공개하지 마십시오.",
        "loaded": "불러옴", "no_file": "bankdata.bin 또는 완전한 객체 덤프를 여십시오.", "invalid": "파일 크기가 올바르지 않습니다",
        "male": "수컷", "female": "암컷", "unknown": "알 수 없음", "all": "전체", "number": "번호", "code": "코드", "raw_time": "원시 시간 값", "nickname": "별명",
        "select_slot": "박스 칸을 선택하면 여기에 자세한 정보를 표시합니다.",
    },
    "zh-Hans": {
        "title": "宝可梦虚拟银行 bankdata 查看器", "open": "打开 bankdata", "language": "界面语言",
        "groups": "分组与盒子", "box": "Bank Box", "transfer": "Transfer Box", "empty": "空",
        "overview": "文件概要", "sources": "来源游戏记录", "boxmeta": "每盒元数据", "slotmeta": "当前盒子槽位元数据", "structure": "完整技术元数据", "creature": "宝可梦详细信息",
        "field": "字段", "value": "值", "description": "说明", "game": "游戏", "player": "玩家名", "sex": "性别", "trainer": "训练家ID",
        "format": "格式", "format6": "第6世代格式", "format7": "第7世代格式", "origin": "来源", "latest": "最近更新时间", "slots": "槽位", "count": "数量",
        "privacy": "此文件可能包含玩家名、训练家ID和唯一对象编号，请勿直接公开。",
        "loaded": "已加载", "no_file": "请打开 bankdata.bin 或完整内存对象转储。", "invalid": "文件尺寸不正确",
        "male": "雄", "female": "雌", "unknown": "未知", "all": "全部", "number": "编号", "code": "代码", "raw_time": "原始时间值", "nickname": "昵称",
        "select_slot": "选择一个盒子格位，即可在这里查看详细信息。",
    },
    "zh-Hant": {
        "title": "寶可夢虛擬銀行 bankdata 檢視器", "open": "開啟 bankdata", "language": "介面語言",
        "groups": "分組與盒子", "box": "Bank Box", "transfer": "Transfer Box", "empty": "空",
        "overview": "檔案概要", "sources": "來源遊戲記錄", "boxmeta": "每盒中繼資料", "slotmeta": "目前盒子槽位中繼資料", "structure": "完整技術中繼資料", "creature": "寶可夢詳細資訊",
        "field": "欄位", "value": "值", "description": "說明", "game": "遊戲", "player": "玩家名", "sex": "性別", "trainer": "訓練家ID",
        "format": "格式", "format6": "第6世代格式", "format7": "第7世代格式", "origin": "來源", "latest": "最近更新時間", "slots": "槽位", "count": "數量",
        "privacy": "此檔案可能包含玩家名、訓練家ID和唯一物件編號，請勿直接公開。",
        "loaded": "已載入", "no_file": "請開啟 bankdata.bin 或完整記憶體物件轉儲。", "invalid": "檔案大小不正確",
        "male": "雄", "female": "雌", "unknown": "未知", "all": "全部", "number": "編號", "code": "代碼", "raw_time": "原始時間值", "nickname": "暱稱",
        "select_slot": "選取一個盒子格位，即可在這裡查看詳細資訊。",
    },
}


GAME_NAMES: dict[str, tuple[str, ...]] = {
    "ja-kana": ("ポケットモンスター X", "ポケットモンスター Y", "ポケットモンスター オメガルビー", "ポケットモンスター アルファサファイア", "ポケットモンスター サン", "ポケットモンスター ムーン", "ポケットモンスター ウルトラサン", "ポケットモンスター ウルトラムーン"),
    "ja-kanji": ("ポケットモンスター X", "ポケットモンスター Y", "ポケットモンスター オメガルビー", "ポケットモンスター アルファサファイア", "ポケットモンスター サン", "ポケットモンスター ムーン", "ポケットモンスター ウルトラサン", "ポケットモンスター ウルトラムーン"),
    "en": ("Pokémon X", "Pokémon Y", "Pokémon Omega Ruby", "Pokémon Alpha Sapphire", "Pokémon Sun", "Pokémon Moon", "Pokémon Ultra Sun", "Pokémon Ultra Moon"),
    "de": ("Pokémon X", "Pokémon Y", "Pokémon Omega Rubin", "Pokémon Alpha Saphir", "Pokémon Sonne", "Pokémon Mond", "Pokémon Ultrasonne", "Pokémon Ultramond"),
    "it": ("Pokémon X", "Pokémon Y", "Pokémon Rubino Omega", "Pokémon Zaffiro Alpha", "Pokémon Sole", "Pokémon Luna", "Pokémon Ultrasole", "Pokémon Ultraluna"),
    "fr": ("Pokémon X", "Pokémon Y", "Pokémon Rubis Oméga", "Pokémon Saphir Alpha", "Pokémon Soleil", "Pokémon Lune", "Pokémon Ultra-Soleil", "Pokémon Ultra-Lune"),
    "es": ("Pokémon X", "Pokémon Y", "Pokémon Rubí Omega", "Pokémon Zafiro Alfa", "Pokémon Sol", "Pokémon Luna", "Pokémon Ultrasol", "Pokémon Ultraluna"),
    "ko": ("포켓몬스터 X", "포켓몬스터 Y", "포켓몬스터 오메가루비", "포켓몬스터 알파사파이어", "포켓몬스터썬", "포켓몬스터문", "포켓몬스터 울트라썬", "포켓몬스터 울트라문"),
    "zh-Hans": ("宝可梦 X", "宝可梦 Y", "宝可梦 欧米伽红宝石", "宝可梦 阿尔法蓝宝石", "宝可梦 太阳", "宝可梦 月亮", "宝可梦 究极之日", "宝可梦 究极之月"),
    "zh-Hant": ("寶可夢 X", "寶可夢 Y", "寶可夢 歐米伽紅寶石", "寶可夢 阿爾法藍寶石", "寶可夢 太陽", "寶可夢 月亮", "寶可夢 究極之日", "寶可夢 究極之月"),
}

SOURCE_GAME_INDEX = {24: 0, 25: 1, 26: 3, 27: 2, 30: 4, 31: 5, 32: 6, 33: 7}
LEGACY_TITLES: dict[str, dict[int, str]] = {
    "ja-kana": {35: "VC ポケットモンスター あか", 36: "VC ポケットモンスター みどり", 37: "VC ポケットモンスター あお", 38: "VC ポケットモンスター ピカチュウ", 39: "VC ポケットモンスター きん", 40: "VC ポケットモンスター ぎん", 41: "VC ポケットモンスター クリスタル"},
    "ja-kanji": {35: "VC ポケットモンスター 赤", 36: "VC ポケットモンスター 緑", 37: "VC ポケットモンスター 青", 38: "VC ポケットモンスター ピカチュウ", 39: "VC ポケットモンスター 金", 40: "VC ポケットモンスター 銀", 41: "VC ポケットモンスター クリスタル"},
    "en": {35: "VC Pokémon Red", 36: "VC Pokémon Green", 37: "VC Pokémon Blue", 38: "VC Pokémon Yellow", 39: "VC Pokémon Gold", 40: "VC Pokémon Silver", 41: "VC Pokémon Crystal"},
    "de": {35: "VC Pokémon Rote Edition", 36: "VC Pokémon Grüne Edition", 37: "VC Pokémon Blaue Edition", 38: "VC Pokémon Gelbe Edition", 39: "VC Pokémon Goldene Edition", 40: "VC Pokémon Silberne Edition", 41: "VC Pokémon Kristall-Edition"},
    "it": {35: "VC Pokémon Rosso", 36: "VC Pokémon Verde", 37: "VC Pokémon Blu", 38: "VC Pokémon Giallo", 39: "VC Pokémon Oro", 40: "VC Pokémon Argento", 41: "VC Pokémon Cristallo"},
    "fr": {35: "VC Pokémon Rouge", 36: "VC Pokémon Vert", 37: "VC Pokémon Bleu", 38: "VC Pokémon Jaune", 39: "VC Pokémon Or", 40: "VC Pokémon Argent", 41: "VC Pokémon Cristal"},
    "es": {35: "VC Pokémon Rojo", 36: "VC Pokémon Verde", 37: "VC Pokémon Azul", 38: "VC Pokémon Amarillo", 39: "VC Pokémon Oro", 40: "VC Pokémon Plata", 41: "VC Pokémon Cristal"},
    "ko": {35: "VC 포켓몬스터 레드", 36: "VC 포켓몬스터 그린", 37: "VC 포켓몬스터 블루", 38: "VC 포켓몬스터 피카츄", 39: "VC 포켓몬스터 금", 40: "VC 포켓몬스터 은", 41: "VC 포켓몬스터 크리스탈"},
    "zh-Hans": {35: "VC 宝可梦 红", 36: "VC 宝可梦 绿", 37: "VC 宝可梦 蓝", 38: "VC 宝可梦 皮卡丘", 39: "VC 宝可梦 金", 40: "VC 宝可梦 银", 41: "VC 宝可梦 水晶"},
    "zh-Hant": {35: "VC 寶可夢 紅", 36: "VC 寶可夢 綠", 37: "VC 寶可夢 藍", 38: "VC 寶可夢 皮卡丘", 39: "VC 寶可夢 金", 40: "VC 寶可夢 銀", 41: "VC 寶可夢 水晶"},
}

STAT_HEADERS: dict[str, tuple[str, ...]] = {
    "ja-kana": ("つかまえた", "つり", "たまごから うまれた", "しんか", "かせきから ふっかつ", "やせいに であった", "こうかん", "1にちの さいだい つかまえた かず", "1にちの さいだい しんか かず"),
    "ja-kanji": ("捕まえた数", "釣り", "孵化", "進化", "化石復元", "野生遭遇", "交換", "一日の捕獲最大", "一日の進化最大"),
    "en": ("Caught", "Fished", "Hatched", "Evolved", "Fossils restored", "Wild encounters", "Traded", "Daily caught peak", "Daily evolved peak"),
    "de": ("Gefangen", "Geangelt", "Ausgebrütet", "Entwickelt", "Fossilien", "Wilde Begegnungen", "Getauscht", "Tagesmaximum gefangen", "Tagesmaximum entwickelt"),
    "it": ("Catturati", "Pescati", "Schiusi", "Evoluti", "Fossili restaurati", "Incontri selvatici", "Scambiati", "Massimo catture giornaliere", "Massimo evoluzioni giornaliere"),
    "fr": ("Capturés", "Pêchés", "Éclos", "Évolués", "Fossiles restaurés", "Rencontres sauvages", "Échangés", "Maximum quotidien de captures", "Maximum quotidien d'évolutions"),
    "es": ("Capturados", "Pescados", "Eclosionados", "Evolucionados", "Fósiles restaurados", "Encuentros salvajes", "Intercambiados", "Máximo diario de capturas", "Máximo diario de evoluciones"),
    "ko": ("잡은 수", "낚은 수", "부화 수", "진화 수", "화석 복원 수", "야생 조우 수", "교환 수", "하루 최대 포획 수", "하루 최대 진화 수"),
    "zh-Hans": ("捕获", "钓鱼", "孵化", "进化", "化石复原", "野生遭遇", "交换", "单日捕获峰值", "单日进化峰值"),
    "zh-Hant": ("捕獲", "釣魚", "孵化", "進化", "化石復原", "野生遭遇", "交換", "單日捕獲峰值", "單日進化峰值"),
}


FIELD_LABELS: dict[str, dict[str, str]] = {
    "ja-kana": {"object_id": "りもーと おぶじぇくと ばんごう", "version": "ふぁいる けいしき ばんごう", "box_count": "つかえる ぼっくすの かず", "edit_time": "さいごの へんしゅう じこく", "rewards": "ぷれぜんとの きろく", "points": "ぽいんと と けん", "flags": "じょうたい ふらぐ", "format": "すろっと けいしき", "index": "ずかん しゅうごう きろく", "operations": "さいしんの そうさ", "tail": "さいごの じょうたい"},
    "ja-kanji": {"object_id": "リモートオブジェクト番号", "version": "ファイル形式番号", "box_count": "利用可能ボックス数", "edit_time": "最終編集日時", "rewards": "プレゼント記録", "points": "ポイントと利用券", "flags": "状態フラグ", "format": "スロット形式", "index": "図鑑集約記録", "operations": "直近の操作", "tail": "末尾状態"},
    "en": {"object_id": "Remote object ID", "version": "File format version", "box_count": "Available boxes", "edit_time": "Last box edit", "rewards": "Gift record", "points": "Points and passes", "flags": "State flags", "format": "Slot format", "index": "Pokédex aggregate", "operations": "Latest operation", "tail": "Tail state"},
    "de": {"object_id": "Remote Objekt-ID", "version": "Dateiformatversion", "box_count": "Verfügbare Boxen", "edit_time": "Letzte Boxbearbeitung", "rewards": "Geschenkprotokoll", "points": "Punkte und Pässe", "flags": "Statusmarkierungen", "format": "Slotformat", "index": "Pokédex-Sammelstand", "operations": "Letzte Aktion", "tail": "Endstatus"},
    "it": {"object_id": "ID oggetto remoto", "version": "Versione del formato", "box_count": "Box disponibili", "edit_time": "Ultima modifica Box", "rewards": "Registro regali", "points": "Punti e pass", "flags": "Indicatori di stato", "format": "Formato slot", "index": "Riepilogo Pokédex", "operations": "Ultima operazione", "tail": "Stato finale"},
    "fr": {"object_id": "ID d'objet distant", "version": "Version du format", "box_count": "Boîtes disponibles", "edit_time": "Dernière modification de Boîte", "rewards": "Historique des cadeaux", "points": "Points et laissez-passer", "flags": "Indicateurs d'état", "format": "Format d'emplacement", "index": "Ensemble Pokédex", "operations": "Dernière opération", "tail": "État final"},
    "es": {"object_id": "ID de objeto remoto", "version": "Versión del formato", "box_count": "Cajas disponibles", "edit_time": "Última edición de Caja", "rewards": "Registro de regalos", "points": "Puntos y pases", "flags": "Indicadores de estado", "format": "Formato de ranura", "index": "Conjunto de Pokédex", "operations": "Última operación", "tail": "Estado final"},
    "ko": {"object_id": "원격 객체 ID", "version": "파일 형식 버전", "box_count": "사용 가능한 박스 수", "edit_time": "마지막 박스 편집 시각", "rewards": "선물 기록", "points": "포인트와 이용권", "flags": "상태 플래그", "format": "슬롯 형식", "index": "도감 통합 기록", "operations": "최근 작업", "tail": "끝부분 상태"},
    "zh-Hans": {"object_id": "远端对象编号", "version": "文件格式版本", "box_count": "已启用盒子数", "edit_time": "最后编辑时间", "rewards": "礼物记录", "points": "点数与票券", "flags": "状态标志", "format": "槽位格式", "index": "图鉴聚合记录", "operations": "最近操作", "tail": "尾部状态"},
    "zh-Hant": {"object_id": "遠端物件編號", "version": "檔案格式版本", "box_count": "已啟用盒子數", "edit_time": "最後編輯時間", "rewards": "禮物記錄", "points": "點數與票券", "flags": "狀態旗標", "format": "槽位格式", "index": "圖鑑彙整記錄", "operations": "最近操作", "tail": "尾端狀態"},
}

FIELD_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "ja-kana": {"object_id": "ほぞんたいしょうを くべつする こゆうの すうちです。 こじん しきべつしとして あつかいます。", "version": "あとにつづく でーたの よみかたを きめる ばんごうです。", "box_count": "つかえる Bank Box の かずです。", "edit_time": "ぼっくすの さいごの へんしゅう じこくです。", "rewards": "さいごに きろくされた こうしんぷれぜんとと きかんげんていぷれぜんとの ばんごうです。", "points": "ぽいんとと けんの きろくです。", "flags": "ぷれぜんと、さいしょの かくにん、ずかん きのうに かんする じょうたいです。", "format": "それぞれの すろっとを だい6または だい7せだいの けいしきで よむかを しめします。", "index": "8つの たいおう そふとごとの ずかん きろく、ひょうじせってい、きろくの ありなしを まとめた りょういきです。", "operations": "さいごに ほぞんされた いれた かずと だした かずです。", "tail": "かくちょうずかんの しるしと よやく りょういきです。"},
    "ja-kanji": {"object_id": "保存対象を区別する固有値です。個人識別子として扱います。", "version": "後続データの読み方を決める番号です。", "box_count": "利用できるBank Boxの数です。", "edit_time": "ボックスの最終編集日時です。", "rewards": "最後に記録された更新プレゼントと期間限定プレゼントの番号です。", "points": "ポイントと利用券の記録です。", "flags": "プレゼント、初回確認、図鑑機能に関する状態です。", "format": "各スロットを第6世代または第7世代形式として読むかを示します。", "index": "八つの対応ソフトごとの図鑑記録、表示設定、記録の有無をまとめた領域です。", "operations": "最後に保存された預け入れ数と引き出し数です。", "tail": "拡張図鑑の印と予約領域です。"},
    "en": {"object_id": "A unique value that distinguishes this stored object; treat it as private.", "version": "Selects how later data is interpreted.", "box_count": "Number of Bank Boxes currently available.", "edit_time": "Timestamp of the latest box edit.", "rewards": "Identifiers of the last recorded update and time-limited gifts.", "points": "Stored point and pass counters.", "flags": "States related to gifts, initial confirmation, and the Pokédex feature.", "format": "Shows whether each slot uses the Generation 6 or Generation 7 interpretation.", "index": "Combines per-title Pokédex records, display choices, and record-availability marks for eight supported games.", "operations": "Counts deposited and withdrawn in the most recently saved operation.", "tail": "An extended-record marker and reserved space."},
    "de": {"object_id": "Ein eindeutiger Wert zur Unterscheidung dieses Speicherobjekts; vertraulich behandeln.", "version": "Legt die Auslegung der folgenden Daten fest.", "box_count": "Anzahl der derzeit verfügbaren Bank-Boxen.", "edit_time": "Zeitpunkt der letzten Boxbearbeitung.", "rewards": "Kennungen des zuletzt gespeicherten Update- und zeitlich begrenzten Geschenks.", "points": "Gespeicherte Zähler für Punkte und Pässe.", "flags": "Zustände zu Geschenken, Erstbestätigung und der Pokédex-Funktion.", "format": "Zeigt, ob ein Platz nach der 6. oder 7. Generation ausgelegt wird.", "index": "Vereint Pokédex-Aufzeichnungen, Anzeigeauswahl und Verfügbarkeitsmarken für acht unterstützte Spiele.", "operations": "Bei der letzten Speicherung hinterlegte Ein- und Auslagerungszahlen.", "tail": "Markierung für erweiterte Aufzeichnungen und reservierter Bereich."},
    "it": {"object_id": "Valore univoco che distingue questo oggetto salvato; trattalo come privato.", "version": "Stabilisce come interpretare i dati successivi.", "box_count": "Numero di Bank Box attualmente disponibili.", "edit_time": "Data e ora dell'ultima modifica della Box.", "rewards": "Identificatori degli ultimi regali di aggiornamento e a tempo registrati.", "points": "Contatori memorizzati per punti e pass.", "flags": "Stati relativi a regali, conferma iniziale e funzione Pokédex.", "format": "Indica se ogni slot usa l'interpretazione della sesta o della settima generazione.", "index": "Riunisce registri Pokédex, scelte di visualizzazione e indicatori di disponibilità per otto giochi supportati.", "operations": "Quantità depositate e ritirate nell'operazione salvata più recente.", "tail": "Indicatore di registri estesi e area riservata."},
    "fr": {"object_id": "Valeur unique qui distingue cet objet enregistré ; à traiter comme privée.", "version": "Détermine l'interprétation des données suivantes.", "box_count": "Nombre de Bank Box actuellement disponibles.", "edit_time": "Horodatage de la dernière modification de Boîte.", "rewards": "Identifiants des derniers cadeaux de mise à jour et temporisés enregistrés.", "points": "Compteurs enregistrés pour les points et les laissez-passer.", "flags": "États liés aux cadeaux, à la confirmation initiale et à la fonction Pokédex.", "format": "Indique si chaque emplacement suit l'interprétation de la sixième ou de la septième génération.", "index": "Regroupe les relevés Pokédex, choix d'affichage et marques de disponibilité de huit jeux pris en charge.", "operations": "Nombres déposés et retirés dans la dernière opération enregistrée.", "tail": "Marqueur de relevés étendus et espace réservé."},
    "es": {"object_id": "Valor único que distingue este objeto guardado; trátalo como privado.", "version": "Determina cómo se interpretan los datos posteriores.", "box_count": "Número de Bank Box disponibles actualmente.", "edit_time": "Marca de tiempo de la última edición de Caja.", "rewards": "Identificadores de los últimos regalos de actualización y temporales registrados.", "points": "Contadores almacenados de puntos y pases.", "flags": "Estados relacionados con regalos, confirmación inicial y la función Pokédex.", "format": "Indica si cada ranura usa la interpretación de sexta o séptima generación.", "index": "Reúne registros de Pokédex, elecciones de visualización y marcas de disponibilidad de ocho juegos compatibles.", "operations": "Cantidades depositadas y retiradas en la operación guardada más reciente.", "tail": "Marcador de registros ampliados y espacio reservado."},
    "ko": {"object_id": "이 저장 객체를 구분하는 고유 값이며 개인 식별 정보로 취급합니다.", "version": "뒤따르는 데이터를 해석하는 방식을 정합니다.", "box_count": "현재 사용할 수 있는 Bank Box 수입니다.", "edit_time": "마지막 박스 편집 시각입니다.", "rewards": "마지막으로 기록된 업데이트 선물과 기간 한정 선물의 번호입니다.", "points": "포인트와 이용권의 저장된 카운터입니다.", "flags": "선물, 최초 확인, 도감 기능과 관련된 상태입니다.", "format": "각 슬롯을 6세대 또는 7세대 형식으로 해석할지 나타냅니다.", "index": "여덟 지원 게임의 도감 기록, 표시 선택, 기록 존재 여부를 모은 영역입니다.", "operations": "가장 최근에 저장된 작업의 맡긴 수와 꺼낸 수입니다.", "tail": "확장 기록 표식과 예약 영역입니다."},
    "zh-Hans": {"object_id": "用于区分该储存对象的唯一数值；属于私人标识。", "version": "决定后续区域采用何种解释方式。", "box_count": "当前可使用的 Bank Box 总数。", "edit_time": "文件中记录的最后一次盒子编辑时间。", "rewards": "最近记录的更新礼物和限时礼物编号。", "points": "点数与票券的保存计数。", "flags": "与礼物、初次确认和图鉴功能有关的状态。", "format": "说明每个槽位应按第6世代还是第7世代格式解释。", "index": "汇集八个支持游戏各自的图鉴记录、显示选择和记录可用状态。", "operations": "最近一次保存操作中的存入和取出数量。", "tail": "扩展记录标志及保留空间。"},
    "zh-Hant": {"object_id": "用於區分該儲存物件的唯一數值；屬於私人識別資訊。", "version": "決定後續區域採用何種解讀方式。", "box_count": "目前可使用的 Bank Box 總數。", "edit_time": "檔案中記錄的最後一次盒子編輯時間。", "rewards": "最近記錄的更新禮物和限時禮物編號。", "points": "點數與票券的儲存計數。", "flags": "與禮物、初次確認和圖鑑功能有關的狀態。", "format": "說明每個槽位應按第6世代還是第7世代格式解讀。", "index": "彙集八個支援遊戲各自的圖鑑記錄、顯示選擇和記錄可用狀態。", "operations": "最近一次儲存操作中的存入和取出數量。", "tail": "擴展記錄旗標及保留空間。"},
}


def ui(language: str, key: str) -> str:
    return UI[language][key]


def game_name(language: str, index: int) -> str:
    return GAME_NAMES[language][index]


def source_title(language: str, code: int) -> str | None:
    index = SOURCE_GAME_INDEX.get(code)
    if index is not None:
        return game_name(language, index)
    return LEGACY_TITLES[language].get(code)


def field_text(language: str, field: str) -> tuple[str, str]:
    return FIELD_LABELS[language][field], FIELD_DESCRIPTIONS[language][field]
