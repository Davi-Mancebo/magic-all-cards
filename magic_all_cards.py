"""Aplicativo gráfico para baixar cartas de Magic: The Gathering."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

import requests
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

BASE_DIR = Path(__file__).resolve().parent
ALL_PRINTINGS_URL = "https://mtgjson.com/api/v5/AllPrintings.json"
META_URL = "https://mtgjson.com/api/v5/Meta.json"
ALL_PRINTINGS_FILE = BASE_DIR / "AllPrintings.json"
ALL_PRINTINGS_META_FILE = BASE_DIR / "AllPrintings.meta.json"
LOCALE_CONFIG_FILE = BASE_DIR / "config.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "MTG_IMAGES"
REQUEST_TIMEOUT = 25
REQUEST_DELAY = 0.05
CARD_WARNING_THRESHOLD = 40000  # Aproximadamente >10 GB de imagens
CARD_WARNING_MB_PER_IMAGE = 0.24  # média estimada em MB por PNG
IMAGE_DOWNLOAD_RETRIES = 3
IMAGE_RETRY_DELAY = 1.0
@dataclass(frozen=True)
class SetMetadata:
    code: str
    name: str
    release: str
    search: str

CARD_TYPE_RULES: Dict[str, Callable[[Dict], bool]] = {
    "all": lambda card: True,
    "creature": lambda card: "Creature" in card.get("types", []),
    "land": lambda card: "Land" in card.get("types", []),
    "enchantment": lambda card: "Enchantment" in card.get("types", []),
    "artifact": lambda card: "Artifact" in card.get("types", []),
    "instant": lambda card: "Instant" in card.get("types", []),
    "sorcery": lambda card: "Sorcery" in card.get("types", []),
    "spell": lambda card: any(t in card.get("types", []) for t in ("Instant", "Sorcery")),
}

CARD_TYPE_LABELS: Dict[str, Dict[str, str]] = {
    "all": {"pt": "Todas as cartas", "en": "All cards"},
    "creature": {"pt": "Criaturas", "en": "Creatures"},
    "land": {"pt": "Terrenos", "en": "Lands"},
    "enchantment": {"pt": "Encantamentos", "en": "Enchantments"},
    "artifact": {"pt": "Artefatos", "en": "Artifacts"},
    "planeswalker": {"pt": "Planeswalkers", "en": "Planeswalkers"},
    "instant": {"pt": "Mágicas instantâneas", "en": "Instants"},
    "sorcery": {"pt": "Mágicas feitiço", "en": "Sorceries"},
    "spell": {"pt": "Mágicas (Instant/Sorcery)", "en": "Instants or sorceries"},
}

CARD_TYPE_ORDER: List[str] = [
    "all",
    "creature",
    "land",
    "enchantment",
    "artifact",
    "planeswalker",
    "instant",
    "sorcery",
    "spell",
]

RARITY_VALUES: Dict[str, Optional[str]] = {
    "all": None,
    "common": "common",
    "uncommon": "uncommon",
    "rare": "rare",
    "mythic": "mythic",
    "special": "special",
    "promo": "promo",
    "bonus": "bonus",
}

RARITY_LABELS: Dict[str, Dict[str, str]] = {
    "all": {"pt": "Todas as raridades", "en": "All rarities"},
    "common": {"pt": "Comum", "en": "Common"},
    "uncommon": {"pt": "Incomum", "en": "Uncommon"},
    "rare": {"pt": "Rara", "en": "Rare"},
    "mythic": {"pt": "Mítica", "en": "Mythic"},
    "special": {"pt": "Especial", "en": "Special"},
    "promo": {"pt": "Promo", "en": "Promo"},
    "bonus": {"pt": "Bônus", "en": "Bonus"},
}

RARITY_ORDER: List[str] = [
    "all",
    "common",
    "uncommon",
    "rare",
    "mythic",
    "special",
    "promo",
    "bonus",
]

RARITY_FOLDER_LABELS: Dict[str, str] = {
    "common": "1-Comum",
    "uncommon": "2-Incomum",
    "rare": "3-Rara",
    "mythic": "4-Mítica",
    "special": "5-Especial",
    "bonus": "6-Bônus",
}

COLOR_FOLDER_LABELS: Dict[str, str] = {
    "W": "1-Branca",
    "U": "2-Azul",
    "B": "3-Preta",
    "R": "4-Vermelha",
    "G": "5-Verde",
    "C": "0-Incolor",
}

TYPE_PRIORITY: List[tuple[str, str]] = [
    ("Land", "0-Terreno"),
    ("Creature", "1-Criatura"),
    ("Planeswalker", "2-Planeswalker"),
    ("Instant", "3-Instant"),
    ("Sorcery", "4-Feitiço"),
    ("Enchantment", "5-Encantamento"),
    ("Artifact", "6-Artefato"),
    ("Battle", "7-Batalha"),
]

SCRYFALL_LANGUAGE_CHOICES: List[tuple[str, str]] = [
    ("English", "en"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Russian", "ru"),
    ("Simplified Chinese", "zhs"),
    ("Traditional Chinese", "zht"),
    ("Hebrew", "he"),
    ("Latin", "la"),
    ("Ancient Greek", "grc"),
    ("Arabic", "ar"),
    ("Sanskrit", "sa"),
    ("Phyrexian", "ph"),
    ("Quenya", "qya"),
]


LANGUAGE_DISPLAY_TO_CODE: Dict[str, str] = {
    f"{name} ({code.upper()})": code for name, code in SCRYFALL_LANGUAGE_CHOICES
}

LANGUAGE_FOLDER_LABELS: Dict[str, str] = {
    code: f"{index + 1:02d}-{name.replace(' ', '')}"
    for index, (name, code) in enumerate(SCRYFALL_LANGUAGE_CHOICES)
}

APP_LANGUAGES = {
    "pt": "Português",
    "en": "English",
}

DEFAULT_APP_LANGUAGE = "en"

TEXTS: Dict[str, Dict[str, str]] = {
    "pt": {
        "title": "Magic All Cards - GUI",
        "download_db": "Baixar/Atualizar banco MTGJSON",
        "load_sets": "Carregar sets",
        "choose_dest": "Selecionar pasta de destino",
        "filters": "Filtros",
        "card_type": "Tipo de carta:",
        "rarity": "Raridade:",
        "name_contains": "Nome contém:",
        "set_filter": "Filtrar set:",
        "image_language": "Idioma das imagens:",
        "app_language": "Idioma do app:",
        "sets": "Sets disponíveis",
        "download_cards": "Baixar cartas selecionadas",
        "stop_download": "Parar download",
        "log": "Log",
        "status_ready": "Pronto",
        "status_downloading_db": "Baixando base MTGJSON...",
        "status_filtering": "Filtrando cartas...",
        "status_downloading_cards": "Baixando {total} cartas...",
        "missing_allprintings": "Baixe o AllPrintings.json antes.",
        "missing_sets": "Carregue os sets antes de baixar.",
        "missing_selection": "Escolha pelo menos um set.",
        "no_cards_filters": "Nenhuma carta corresponde aos filtros selecionados.",
        "error_no_cards": "Nenhuma carta encontrada com os filtros informados.",
        "download_large_title": "Download muito grande",
        "download_large_text": "Você selecionou aproximadamente {cards:,} cartas (~{gb:,.1f} GB).\n\nDeseja continuar mesmo assim?",
        "download_log_start": "Iniciando download de {cards} cartas.",
        "download_log_done": "Download finalizado.",
        "log_download_cancelled": "Download cancelado após alerta de tamanho.",
        "log_download_success": "Baixado [{lang}]: {set_name} - {card_name}",
        "log_download_fallback": "Baixado (fallback EN): {set_name} - {card_name}",
        "log_download_failure": "Falhou [{lang}]: {set_name} - {card_name}",
        "progress_cards_label": "{percent}% ({downloaded}/{total} cartas)",
        "card_fallback_name": "Carta",
        "error_title": "Erro",
        "warning_title": "Aviso",
        "info_title": "Informação",
        "meta_fail": "Não foi possível consultar o Meta do MTGJSON. Usando cache local.",
        "download_in_progress": "Download do AllPrintings já está em andamento.",
        "log_db_start": "Iniciando download do AllPrintings.json",
        "log_db_done_hint": "Download concluído. Clique em 'Carregar sets'.",
        "error_db_download": "Falha ao baixar banco: {error}",
        "sets_loading": "Carregando sets...",
        "sets_loaded": "{count} sets carregados.",
        "log_sets_in_progress": "Carregamento de sets já está em andamento.",
        "error_load_sets": "Erro ao carregar sets: {error}",
        "log_db_corrupted": "AllPrintings.json parece corrompido. Baixando novamente...",
        "select_language": "Selecione o idioma do aplicativo.",
        "clear_selection": "Limpar seleção",
        "log_download_stopped": "Download interrompido pelo usuário.",
    },
    "en": {
        "title": "Magic All Cards - GUI",
        "download_db": "Download/Update MTGJSON",
        "load_sets": "Load sets",
        "choose_dest": "Choose destination folder",
        "filters": "Filters",
        "card_type": "Card type:",
        "rarity": "Rarity:",
        "name_contains": "Name contains:",
        "set_filter": "Filter set:",
        "image_language": "Image language:",
        "app_language": "App language:",
        "sets": "Available sets",
        "download_cards": "Download selected cards",
        "stop_download": "Stop download",
        "log": "Log",
        "status_ready": "Ready",
        "status_downloading_db": "Downloading MTGJSON database...",
        "status_filtering": "Filtering cards...",
        "status_downloading_cards": "Downloading {total} cards...",
        "missing_allprintings": "Download AllPrintings.json first.",
        "missing_sets": "Load the sets before downloading.",
        "missing_selection": "Select at least one set.",
        "no_cards_filters": "No cards match the selected filters.",
        "error_no_cards": "No cards found with the selected filters.",
        "download_large_title": "Huge download",
        "download_large_text": "You selected about {cards:,} cards (~{gb:,.1f} GB).\n\nDo you want to continue?",
        "download_log_start": "Starting download of {cards} cards.",
        "download_log_done": "Download finished.",
        "log_download_cancelled": "Download canceled after size warning.",
        "log_download_success": "Downloaded [{lang}]: {set_name} - {card_name}",
        "log_download_fallback": "Downloaded (fallback EN): {set_name} - {card_name}",
        "log_download_failure": "Failed [{lang}]: {set_name} - {card_name}",
        "progress_cards_label": "{percent}% ({downloaded}/{total} cards)",
        "card_fallback_name": "Card",
        "error_title": "Error",
        "warning_title": "Warning",
        "info_title": "Information",
        "meta_fail": "Unable to reach MTGJSON Meta. Using local cache.",
        "download_in_progress": "AllPrintings download already running.",
        "log_db_start": "Starting download of AllPrintings.json",
        "log_db_done_hint": "Download finished. Click 'Load sets'.",
        "error_db_download": "Failed to download database: {error}",
        "sets_loading": "Loading sets...",
        "sets_loaded": "{count} sets loaded.",
        "log_sets_in_progress": "Set loading is already running.",
        "error_load_sets": "Failed to load sets: {error}",
        "log_db_corrupted": "AllPrintings.json looks corrupted. Downloading it again...",
        "select_language": "Select the application language.",
        "clear_selection": "Clear selection",
        "log_download_stopped": "Download stopped by the user.",
    },
}


def fetch_allprintings_remote_meta() -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(META_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        return None

    data = payload.get("data") or []

    if isinstance(data, dict):
        candidates = data.values()
    else:
        candidates = data

    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("fileName")
        file_name = entry.get("fileName") or entry.get("name")
        if name == "AllPrintings" or file_name == "AllPrintings.json":
            return entry
    return None


def load_local_meta() -> Optional[Dict[str, Any]]:
    if not ALL_PRINTINGS_META_FILE.exists():
        return None
    try:
        with ALL_PRINTINGS_META_FILE.open(encoding="utf-8") as handler:
            return json.load(handler)
    except (OSError, json.JSONDecodeError):
        return None


def save_local_meta(meta_entry: Dict[str, Any]) -> None:
    try:
        ALL_PRINTINGS_META_FILE.write_text(json.dumps(meta_entry, indent=2), encoding="utf-8")
    except OSError:
        pass


def needs_database_update(remote_meta: Optional[Dict[str, Any]]) -> bool:
    if not ALL_PRINTINGS_FILE.exists():
        return True

    if not remote_meta:
        return False

    local_meta = load_local_meta()
    if not local_meta:
        return True

    remote_hash = (remote_meta.get("contentHash") or {}).get("sha512")
    local_hash = (local_meta.get("contentHash") or {}).get("sha512")

    if remote_hash and local_hash:
        return remote_hash != local_hash

    remote_updated = remote_meta.get("updatedAt") or remote_meta.get("lastUpdated")
    local_updated = local_meta.get("updatedAt") or local_meta.get("lastUpdated")

    if remote_updated and local_updated:
        return remote_updated != local_updated

    return False


def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos mantendo nomes legíveis."""

    safe = "".join(char for char in name if char.isalnum() or char in " -_#")
    return safe.strip() or "carta"


def get_rarity_folder_name(rarity_value: Optional[str]) -> str:
    """Retorna o nome de pasta baseado na raridade, padronizando rótulos."""

    if not rarity_value:
        return "0-SemRaridade"

    cleaned = rarity_value.lower().strip()
    if not cleaned:
        return "0-SemRaridade"

    if cleaned in RARITY_FOLDER_LABELS:
        return RARITY_FOLDER_LABELS[cleaned]

    fallback = sanitize_filename(cleaned.title())
    return fallback or "0-SemRaridade"


def get_color_folder_name(card: Dict[str, Any]) -> str:
    """Determina pasta por cor, usando cores ou color identity."""

    colors = card.get("colors") or card.get("colorIdentity") or []
    if isinstance(colors, str):  # salvaguarda para dados malformados
        colors = list(colors)

    unique_colors = sorted({c for c in colors if isinstance(c, str)})

    if not unique_colors:
        return "0-Incolor"

    if len(unique_colors) == 1:
        label = COLOR_FOLDER_LABELS.get(unique_colors[0], unique_colors[0])
        return sanitize_filename(label) or "0-Incolor"

    return "7-Multicolor"


def get_type_folder_name(card: Dict[str, Any]) -> str:
    """Determina pasta de tipo, priorizando Terrenos conforme solicitado."""

    types = card.get("types") or []
    normalized = [str(t) for t in types]

    for keyword, label in TYPE_PRIORITY:
        if keyword in normalized:
            return label

    if normalized:
        return sanitize_filename(f"8-{normalized[0]}") or "8-Outros"

    return "8-Outros"


def get_language_folder_name(language_code: Optional[str]) -> str:
    code = (language_code or "en").lower()
    return LANGUAGE_FOLDER_LABELS.get(code, f"99-{code.upper()}")


def load_config() -> Dict[str, Any]:
    if not LOCALE_CONFIG_FILE.exists():
        return {}
    try:
        with LOCALE_CONFIG_FILE.open(encoding="utf-8") as handler:
            return json.load(handler)
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data: Dict[str, Any]) -> None:
    try:
        LOCALE_CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def build_image_url_candidates(card: Dict[str, Any], set_code: str, language_code: str) -> List[str]:
    params = "format=image&version=png"
    candidates: List[str] = []
    cleaned_set = (set_code or "").lower()
    card_number = str(card.get("number", "")).strip()
    encoded_number = quote(card_number, safe="") if card_number else ""
    target_lang = (language_code or "en").lower()
    scryfall_id = get_scryfall_id(card)

    def add_url(url: Optional[str]) -> None:
        if url and url not in candidates:
            candidates.append(url)

    if target_lang != "en" and cleaned_set and encoded_number:
        add_url(
            f"https://api.scryfall.com/cards/{cleaned_set}/{encoded_number}/{target_lang}?{params}"
        )

    if cleaned_set and encoded_number:
        add_url(f"https://api.scryfall.com/cards/{cleaned_set}/{encoded_number}/en?{params}")

    if scryfall_id:
        add_url(f"https://api.scryfall.com/cards/{scryfall_id}?{params}")

    return candidates


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_scryfall_id(card: Dict) -> str | None:
    identifiers = card.get("identifiers") or {}
    return card.get("scryfallId") or identifiers.get("scryfallId")


def download_binary(url: str, destination: Path) -> bool:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            destination.write_bytes(response.content)
            return True
    except requests.RequestException:
        return False
    return False


class MagicDownloaderApp:
    """Interface gráfica para baixar cartas filtradas."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.app_language = DEFAULT_APP_LANGUAGE
        self.config_data: Dict[str, Any] = load_config()
        self._apply_config_preferences()
        self.root.title(self._t("title"))
        self.root.geometry("960x640")
        self.root.minsize(860, 540)

        self.queue: Queue = Queue()
        self.sets_data: Dict[str, Dict] = {}
        self.sets_metadata: List[SetMetadata] = []
        self.filtered_metadata: List[SetMetadata] = []
        self.database_lock = threading.Lock()
        self.sets_lock = threading.Lock()

        self.destination_var = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.selected_type_key = CARD_TYPE_ORDER[0]
        self.selected_rarity_key = RARITY_ORDER[0]
        self.type_var = tk.StringVar()
        self.rarity_var = tk.StringVar()
        self.type_display_to_key: Dict[str, str] = {}
        self.rarity_display_to_key: Dict[str, str] = {}
        self.type_box: Optional[ttk.Combobox] = None
        self.rarity_box: Optional[ttk.Combobox] = None
        self.app_language_button: Optional[ttk.Button] = None
        self.app_language_label: Optional[ttk.Label] = None
        self.filters_frame: Optional[ttk.LabelFrame] = None
        self.sets_frame: Optional[ttk.LabelFrame] = None
        self.btn_clear_sets: Optional[ttk.Button] = None
        self.log_frame: Optional[ttk.LabelFrame] = None
        self.card_type_label: Optional[ttk.Label] = None
        self.rarity_label: Optional[ttk.Label] = None
        self.name_contains_label: Optional[ttk.Label] = None
        self.set_filter_label: Optional[ttk.Label] = None
        self.image_language_label: Optional[ttk.Label] = None
        self.btn_choose_dest: Optional[ttk.Button] = None
        self.language_box: Optional[ttk.Combobox] = None
        self.name_filter_var = tk.StringVar()
        self.set_filter_var = tk.StringVar()
        self.language_options = list(LANGUAGE_DISPLAY_TO_CODE.keys())
        default_language_display = self.language_options[0]
        self.language_var = tk.StringVar(value=default_language_display)
        self.status_var = tk.StringVar(value=self._t("status_ready"))
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_label_var = tk.StringVar(value="0%")
        self.btn_stop_download: Optional[ttk.Button] = None
        self.download_cancel_event = threading.Event()
        self.is_downloading = False

        self._build_ui()
        self.root.after(150, self._process_queue)
        threading.Thread(target=self._auto_bootstrap_task, daemon=True).start()

    def _build_ui(self) -> None:
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill=tk.X)

        self.btn_download_db = ttk.Button(
            control_frame,
            text=self._t("download_db"),
            command=self.download_database,
        )
        self.btn_download_db.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_load_sets = ttk.Button(
            control_frame,
            text=self._t("load_sets"),
            command=self.load_sets,
        )
        self.btn_load_sets.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_choose_dest = ttk.Button(
            control_frame,
            text=self._t("choose_dest"),
            command=self.choose_directory,
        )
        self.btn_choose_dest.pack(side=tk.LEFT)

        ttk.Label(control_frame, textvariable=self.destination_var).pack(
            side=tk.LEFT, padx=10
        )

        self.filters_frame = ttk.LabelFrame(self.root, text=self._t("filters"), padding=10)
        self.filters_frame.pack(fill=tk.X, padx=10, pady=5)

        self.card_type_label = ttk.Label(self.filters_frame, text=self._t("card_type"))
        self.card_type_label.grid(row=0, column=0, sticky=tk.W)
        self.type_box = ttk.Combobox(
            self.filters_frame,
            textvariable=self.type_var,
            state="readonly",
            width=28,
            values=[],
        )
        self.type_box.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        self.type_box.bind("<<ComboboxSelected>>", self._on_type_selected)

        self.rarity_label = ttk.Label(self.filters_frame, text=self._t("rarity"))
        self.rarity_label.grid(row=0, column=2, sticky=tk.W)
        self.rarity_box = ttk.Combobox(
            self.filters_frame,
            textvariable=self.rarity_var,
            state="readonly",
            width=24,
            values=[],
        )
        self.rarity_box.grid(row=0, column=3, padx=5, pady=2, sticky=tk.W)
        self.rarity_box.bind("<<ComboboxSelected>>", self._on_rarity_selected)

        self.name_contains_label = ttk.Label(self.filters_frame, text=self._t("name_contains"))
        self.name_contains_label.grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(self.filters_frame, textvariable=self.name_filter_var, width=30).grid(
            row=1, column=1, padx=5, pady=2, sticky=tk.W
        )

        self.set_filter_label = ttk.Label(self.filters_frame, text=self._t("set_filter"))
        self.set_filter_label.grid(row=1, column=2, sticky=tk.W)
        set_filter_entry = ttk.Entry(self.filters_frame, textvariable=self.set_filter_var, width=24)
        set_filter_entry.grid(row=1, column=3, padx=5, pady=2, sticky=tk.W)
        set_filter_entry.bind("<KeyRelease>", lambda _event: self._refresh_set_list())

        self.image_language_label = ttk.Label(self.filters_frame, text=self._t("image_language"))
        self.image_language_label.grid(row=2, column=0, sticky=tk.W, pady=(6, 0))
        self.language_box = ttk.Combobox(
            self.filters_frame,
            textvariable=self.language_var,
            values=self.language_options,
            state="readonly",
            width=30,
        )
        self.language_box.grid(row=2, column=1, padx=5, pady=(6, 0), sticky=tk.W)

        self.app_language_label = ttk.Label(self.filters_frame, text=self._t("app_language"))
        self.app_language_label.grid(row=2, column=2, sticky=tk.W, pady=(6, 0))
        self.app_language_button = ttk.Button(
            self.filters_frame,
            text=self._get_next_app_language_label(),
            command=self._toggle_app_language,
            width=20,
        )
        self.app_language_button.grid(row=2, column=3, padx=5, pady=(6, 0), sticky=tk.W)

        self.sets_frame = ttk.LabelFrame(self.root, text=self._t("sets"), padding=10)
        self.sets_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        sets_header = ttk.Frame(self.sets_frame)
        sets_header.pack(fill=tk.X, side=tk.TOP, anchor=tk.W, pady=(0, 6))
        self.btn_clear_sets = ttk.Button(
            sets_header,
            text=self._t("clear_selection"),
            command=self.clear_set_selection,
        )
        self.btn_clear_sets.pack(side=tk.RIGHT)

        self.set_list = tk.Listbox(self.sets_frame, selectmode=tk.MULTIPLE, exportselection=False)
        self.set_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self.sets_frame, orient=tk.VERTICAL, command=self.set_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.set_list.config(yscrollcommand=scrollbar.set)

        action_frame = ttk.Frame(self.root, padding=10)
        action_frame.pack(fill=tk.X)

        self.btn_start_download = ttk.Button(
            action_frame,
            text=self._t("download_cards"),
            command=self.start_download,
            state=tk.DISABLED,
        )
        self.btn_start_download.pack(side=tk.LEFT)

        self.btn_stop_download = ttk.Button(
            action_frame,
            text=self._t("stop_download"),
            command=self.stop_download,
            state=tk.DISABLED,
        )
        self.btn_stop_download.pack(side=tk.LEFT, padx=(6, 0))

        ttk.Progressbar(
            action_frame,
            variable=self.progress_var,
            maximum=100.0,
            length=320,
        ).pack(side=tk.LEFT, padx=10)

        ttk.Label(action_frame, textvariable=self.progress_label_var, width=18, anchor=tk.W).pack(side=tk.LEFT)
        ttk.Label(action_frame, textvariable=self.status_var).pack(side=tk.LEFT)

        self.log_frame = ttk.LabelFrame(self.root, text=self._t("log"), padding=10)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.log_widget = scrolledtext.ScrolledText(self.log_frame, height=10, state=tk.DISABLED)
        self.log_widget.pack(fill=tk.BOTH, expand=True)

        self._apply_language_to_ui()

    def _get_card_type_label(self, key: str) -> str:
        return CARD_TYPE_LABELS.get(key, {}).get(self.app_language, key)

    def _get_rarity_label(self, key: str) -> str:
        return RARITY_LABELS.get(key, {}).get(self.app_language, key)

    def _get_next_app_language_code(self) -> str:
        codes = list(APP_LANGUAGES.keys())
        if self.app_language in codes:
            index = codes.index(self.app_language)
            return codes[(index + 1) % len(codes)]
        return DEFAULT_APP_LANGUAGE

    def _get_next_app_language_label(self) -> str:
        next_code = self._get_next_app_language_code()
        return APP_LANGUAGES.get(next_code, next_code.upper())

    def _t(self, key: str, **kwargs: Any) -> str:
        language_pack = TEXTS.get(self.app_language) or TEXTS.get(DEFAULT_APP_LANGUAGE) or {}
        fallback_pack = TEXTS.get(DEFAULT_APP_LANGUAGE, {})
        template = language_pack.get(key) or fallback_pack.get(key) or key
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError:
                return template
        return template

    def _apply_language_to_ui(self) -> None:
        self._refresh_filter_comboboxes()
        if self.btn_download_db:
            self.btn_download_db.config(text=self._t("download_db"))
        if self.btn_load_sets:
            self.btn_load_sets.config(text=self._t("load_sets"))
        if self.btn_choose_dest:
            self.btn_choose_dest.config(text=self._t("choose_dest"))
        if self.filters_frame:
            self.filters_frame.config(text=self._t("filters"))
        if self.card_type_label:
            self.card_type_label.config(text=self._t("card_type"))
        if self.rarity_label:
            self.rarity_label.config(text=self._t("rarity"))
        if self.name_contains_label:
            self.name_contains_label.config(text=self._t("name_contains"))
        if self.set_filter_label:
            self.set_filter_label.config(text=self._t("set_filter"))
        if self.image_language_label:
            self.image_language_label.config(text=self._t("image_language"))
        if self.app_language_label:
            self.app_language_label.config(text=self._t("app_language"))
        if self.sets_frame:
            self.sets_frame.config(text=self._t("sets"))
        if self.btn_clear_sets:
            self.btn_clear_sets.config(text=self._t("clear_selection"))
        if self.log_frame:
            self.log_frame.config(text=self._t("log"))
        if self.btn_start_download:
            self.btn_start_download.config(text=self._t("download_cards"))
        if self.btn_stop_download:
            self.btn_stop_download.config(text=self._t("stop_download"))
        if self.app_language_button:
            self.app_language_button.config(text=self._get_next_app_language_label())
        self.root.title(self._t("title"))

    def _toggle_app_language(self) -> None:
        new_code = self._get_next_app_language_code()
        if new_code == self.app_language:
            return
        self.app_language = new_code
        self._persist_config()
        self._apply_language_to_ui()

    def _apply_config_preferences(self) -> None:
        stored_language = str(self.config_data.get("app_language", "")).lower()
        if stored_language in APP_LANGUAGES:
            self.app_language = stored_language

    def _persist_config(self) -> None:
        payload = dict(self.config_data)
        payload["app_language"] = self.app_language
        self.config_data = payload
        save_config(payload)

    def _refresh_filter_comboboxes(self) -> None:
        type_values: List[str] = []
        self.type_display_to_key.clear()
        for key in CARD_TYPE_ORDER:
            label = self._get_card_type_label(key)
            type_values.append(label)
            self.type_display_to_key[label] = key
        if self.type_box is not None:
            self.type_box["values"] = type_values
        self.type_var.set(self._get_card_type_label(self.selected_type_key))

        rarity_values: List[str] = []
        self.rarity_display_to_key.clear()
        for key in RARITY_ORDER:
            label = self._get_rarity_label(key)
            rarity_values.append(label)
            self.rarity_display_to_key[label] = key
        if self.rarity_box is not None:
            self.rarity_box["values"] = rarity_values
        self.rarity_var.set(self._get_rarity_label(self.selected_rarity_key))

    def _on_type_selected(self, _event: Optional[tk.Event] = None) -> None:
        label = self.type_var.get()
        if self.type_display_to_key:
            self.selected_type_key = self.type_display_to_key.get(label, CARD_TYPE_ORDER[0])
        else:
            self.selected_type_key = CARD_TYPE_ORDER[0]
        if label not in self.type_display_to_key:
            self.type_var.set(self._get_card_type_label(self.selected_type_key))

    def _on_rarity_selected(self, _event: Optional[tk.Event] = None) -> None:
        label = self.rarity_var.get()
        if self.rarity_display_to_key:
            self.selected_rarity_key = self.rarity_display_to_key.get(label, RARITY_ORDER[0])
        else:
            self.selected_rarity_key = RARITY_ORDER[0]
        if label not in self.rarity_display_to_key:
            self.rarity_var.set(self._get_rarity_label(self.selected_rarity_key))

    def choose_directory(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.destination_var.get())
        if selected:
            self.destination_var.set(selected)

    def download_database(self) -> None:
        thread = threading.Thread(target=self._download_database_task, daemon=True)
        thread.start()

    def _download_database_task(
        self,
        remote_meta: Optional[Dict[str, Any]] = None,
        auto_load_after: bool = False,
    ) -> None:
        if not self.database_lock.acquire(blocking=False):
            self.queue.put(("log", self._t("download_in_progress")))
            return

        download_success = False
        try:
            remote_meta = remote_meta or fetch_allprintings_remote_meta()

            if not ALL_PRINTINGS_FILE.parent.exists():
                ALL_PRINTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

            self.queue.put(("status", self._t("status_downloading_db")))
            self.queue.put(("log", self._t("log_db_start")))

            try:
                response = requests.get(ALL_PRINTINGS_URL, stream=True, timeout=60)
                response.raise_for_status()

                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                start_time = time.perf_counter()
                with ALL_PRINTINGS_FILE.open("wb") as file_handle:
                    for chunk in response.iter_content(chunk_size=1024 * 512):
                        if not chunk:
                            continue
                        file_handle.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            percent = (downloaded / total) * 100
                            elapsed = max(time.perf_counter() - start_time, 1e-6)
                            speed = downloaded / elapsed / (1024 * 1024)
                            label = f"{percent:5.1f}% ({speed:.2f} MB/s)"
                            self.queue.put(("progress", {"value": percent, "label": label}))

                if remote_meta:
                    save_local_meta(remote_meta)
                elif ALL_PRINTINGS_META_FILE.exists():
                    try:
                        ALL_PRINTINGS_META_FILE.unlink()
                    except OSError:
                        pass

                self.queue.put(("log", self._t("log_db_done_hint")))
                download_success = True
            except requests.RequestException as exc:
                self.queue.put(("error", self._t("error_db_download", error=exc)))
            finally:
                self.queue.put(("status", self._t("status_ready")))
                self.queue.put(("progress", 0.0))
        finally:
            self.database_lock.release()

        if auto_load_after and download_success:
            threading.Thread(target=self._load_sets_task, daemon=True).start()

    def load_sets(self) -> None:
        if not ALL_PRINTINGS_FILE.exists():
            messagebox.showwarning(self._t("warning_title"), self._t("missing_allprintings"))
            return

        self.btn_load_sets.config(state=tk.DISABLED)
        thread = threading.Thread(target=self._load_sets_task, daemon=True)
        thread.start()

    def _load_sets_task(self) -> None:
        if not self.sets_lock.acquire(blocking=False):
            self.queue.put(("log", self._t("log_sets_in_progress")))
            return

        self.queue.put(("status", self._t("sets_loading")))
        try:
            with ALL_PRINTINGS_FILE.open(encoding="utf-8") as handler:
                data = json.load(handler)["data"]

            metadata: List[SetMetadata] = []
            for code, info in data.items():
                metadata.append(
                    SetMetadata(
                        code=code,
                        name=info.get("name", code),
                        release=info.get("releaseDate", ""),
                        search=f"{code} {info.get('name', '')}".lower(),
                    )
                )

            metadata.sort(key=lambda item: item.release or "", reverse=True)

            self.queue.put(("sets_loaded", (data, metadata)))
            self.queue.put(("log", self._t("sets_loaded", count=len(metadata))))
        except (json.JSONDecodeError, OSError) as exc:
            self.queue.put(("error", self._t("error_load_sets", error=exc)))
            self._handle_corrupted_database()
        finally:
            self.queue.put(("status", self._t("status_ready")))
            self.queue.put(("progress", 0.0))
            self.sets_lock.release()

    def _handle_corrupted_database(self) -> None:
        for file_path in (ALL_PRINTINGS_FILE, ALL_PRINTINGS_META_FILE):
            try:
                if file_path.exists():
                    file_path.unlink()
            except OSError:
                pass

        self.queue.put(("log", self._t("log_db_corrupted")))

        threading.Thread(
            target=self._download_database_task,
            kwargs={"auto_load_after": True},
            daemon=True,
        ).start()

    def _on_sets_loaded(self, data: Dict, metadata: List[SetMetadata]) -> None:
        self.sets_data = data
        self.sets_metadata = metadata
        self.filtered_metadata = metadata
        self._refresh_set_list()
        self.btn_start_download.config(state=tk.NORMAL)
        self.btn_load_sets.config(state=tk.NORMAL)

    def _refresh_set_list(self) -> None:
        filter_text = self.set_filter_var.get().lower().strip()
        if filter_text:
            self.filtered_metadata = [item for item in self.sets_metadata if filter_text in item.search]
        else:
            self.filtered_metadata = list(self.sets_metadata)

        self.set_list.delete(0, tk.END)
        for item in self.filtered_metadata:
            display = f"[{item.code}] {item.name} ({item.release})"
            self.set_list.insert(tk.END, display)

    def clear_set_selection(self) -> None:
        if self.set_list is not None:
            self.set_list.selection_clear(0, tk.END)

    def stop_download(self) -> None:
        if not self.is_downloading:
            return
        self.download_cancel_event.set()
        if self.btn_stop_download:
            self.btn_stop_download.config(state=tk.DISABLED)

    def _on_download_complete(self, canceled: bool) -> None:
        self.is_downloading = False
        if self.btn_stop_download:
            self.btn_stop_download.config(state=tk.DISABLED)
        if self.btn_start_download:
            state = tk.NORMAL if self.sets_data else tk.DISABLED
            self.btn_start_download.config(state=state)

    def start_download(self) -> None:
        if not self.sets_data:
            messagebox.showinfo(self._t("info_title"), self._t("missing_sets"))
            return

        selection = self.set_list.curselection()
        if not selection:
            messagebox.showwarning(self._t("warning_title"), self._t("missing_selection"))
            return

        selected_codes = [self.filtered_metadata[idx].code for idx in selection]
        destination = Path(self.destination_var.get()).expanduser()

        type_key = self.selected_type_key
        rarity_key = self.selected_rarity_key
        name_filter = self.name_filter_var.get().strip().lower()
        language_display = self.language_var.get()
        language_code = LANGUAGE_DISPLAY_TO_CODE.get(language_display, "en")

        self.is_downloading = True
        self.download_cancel_event.clear()
        if self.btn_start_download:
            self.btn_start_download.config(state=tk.DISABLED)
        if self.btn_stop_download:
            self.btn_stop_download.config(state=tk.NORMAL)

        thread = threading.Thread(
            target=self._download_sets_task,
            args=(selected_codes, destination, type_key, rarity_key, name_filter, language_code),
            daemon=True,
        )
        thread.start()

    def _filter_cards(
        self,
        set_codes: List[str],
        type_key: str,
        rarity_key: str,
        name_filter: str,
    ) -> tuple[Dict[str, List[Dict]], int]:
        type_rule = CARD_TYPE_RULES.get(type_key, CARD_TYPE_RULES["all"])
        rarity_value = RARITY_VALUES.get(rarity_key)
        normalized_name = name_filter.strip().lower()

        filtered_cards: Dict[str, List[Dict]] = {}
        total_cards = 0

        for code in set_codes:
            set_info = self.sets_data.get(code, {})
            cards = set_info.get("cards", [])
            selected = [
                card
                for card in cards
                if type_rule(card)
                and (not rarity_value or card.get("rarity") == rarity_value)
                and (not normalized_name or normalized_name in card.get("name", "").lower())
                and get_scryfall_id(card)
            ]
            if selected:
                filtered_cards[code] = selected
                total_cards += len(selected)

        return filtered_cards, total_cards

    def _download_sets_task(
        self,
        set_codes: List[str],
        destination: Path,
        type_key: str,
        rarity_key: str,
        name_filter: str,
        language_code: str,
        prepared_cards: Optional[Dict[str, List[Dict]]] = None,
        prepared_total: Optional[int] = None,
    ) -> None:
        self.queue.put(("status", self._t("status_filtering")))
        ensure_output_dir(destination)

        filtered_cards = prepared_cards
        total_cards = prepared_total
        cancel_event = self.download_cancel_event

        if filtered_cards is None or total_cards is None:
            filtered_cards, total_cards = self._filter_cards(set_codes, type_key, rarity_key, name_filter)

        if total_cards == 0:
            self.queue.put(("error", self._t("error_no_cards")))
            self.queue.put(("status", self._t("status_ready")))
            self.queue.put(("progress", 0.0))
            self.queue.put(("download_complete", {"canceled": True}))
            return

        if total_cards >= CARD_WARNING_THRESHOLD:
            confirmation_event = threading.Event()
            decision_holder: Dict[str, bool] = {"proceed": False}
            estimated_gb = (total_cards * CARD_WARNING_MB_PER_IMAGE) / 1024
            self.queue.put(
                (
                    "confirm_download",
                    (total_cards, estimated_gb, confirmation_event, decision_holder),
                )
            )
            confirmation_event.wait()

            if not decision_holder.get("proceed"):
                self.queue.put(("log", self._t("log_download_cancelled")))
                self.queue.put(("status", self._t("status_ready")))
                self.queue.put(("progress", 0.0))
                self.queue.put(("download_complete", {"canceled": True}))
                return

        self.queue.put(("status", self._t("status_downloading_cards", total=total_cards)))
        self.queue.put(("log", self._t("download_log_start", cards=total_cards)))

        downloaded = 0
        canceled = False
        for code, cards in filtered_cards.items():
            if cancel_event.is_set():
                canceled = True
                break
            set_name = self.sets_data.get(code, {}).get("name", code)
            folder_name = sanitize_filename(f"{code}_{set_name}") or code
            set_folder = ensure_output_dir(destination / folder_name)
            language_folder = ensure_output_dir(set_folder / get_language_folder_name(language_code))

            for card in cards:
                if cancel_event.is_set():
                    canceled = True
                    break
                card_name = sanitize_filename(card.get("name", "carta"))
                card_number = card.get("number")
                filename = f"{card_number}_{card_name}" if card_number else card_name
                color_folder = ensure_output_dir(language_folder / get_color_folder_name(card))
                type_folder = ensure_output_dir(color_folder / get_type_folder_name(card))
                rarity_folder = ensure_output_dir(type_folder / get_rarity_folder_name(card.get("rarity")))
                primary_path = rarity_folder / f"{filename}.png"
                fallback_path = rarity_folder / f"{filename}_EN.png"

                if primary_path.exists() or fallback_path.exists():
                    downloaded += 1
                    percent = (downloaded / total_cards) * 100
                    label = self._t(
                        "progress_cards_label",
                        percent=f"{percent:5.1f}",
                        downloaded=downloaded,
                        total=total_cards,
                    )
                    self.queue.put(("progress", {"value": percent, "label": label}))
                    continue

                url_candidates = build_image_url_candidates(card, code, language_code)
                success = False
                fallback_used = False
                for idx, url in enumerate(url_candidates):
                    is_fallback_attempt = idx > 0 and language_code.lower() != "en"
                    target_path = fallback_path if is_fallback_attempt else primary_path
                    for attempt in range(IMAGE_DOWNLOAD_RETRIES):
                        success = download_binary(url, target_path)
                        if success:
                            fallback_used = is_fallback_attempt
                            break
                        if attempt < IMAGE_DOWNLOAD_RETRIES - 1:
                            time.sleep(IMAGE_RETRY_DELAY)
                    if success:
                        break

                lang_label = language_code.upper()
                card_display_name = card.get("name") or self._t("card_fallback_name")
                if success:
                    if fallback_used:
                        self.queue.put(
                            (
                                "log",
                                self._t(
                                    "log_download_fallback",
                                    set_name=set_name,
                                    card_name=card_display_name,
                                ),
                            )
                        )
                    else:
                        self.queue.put(
                            (
                                "log",
                                self._t(
                                    "log_download_success",
                                    lang=lang_label,
                                    set_name=set_name,
                                    card_name=card_display_name,
                                ),
                            )
                        )
                else:
                    self.queue.put(
                        (
                            "log",
                            self._t(
                                "log_download_failure",
                                lang=lang_label,
                                set_name=set_name,
                                card_name=card_display_name,
                            ),
                        )
                    )

                downloaded += 1
                percent = (downloaded / total_cards) * 100
                label = self._t(
                    "progress_cards_label",
                    percent=f"{percent:5.1f}",
                    downloaded=downloaded,
                    total=total_cards,
                )
                self.queue.put(("progress", {"value": percent, "label": label}))
                time.sleep(REQUEST_DELAY)

            if canceled:
                break

        if canceled:
            self.queue.put(("log", self._t("log_download_stopped")))
        else:
            self.queue.put(("log", self._t("download_log_done")))
        self.queue.put(("status", self._t("status_ready")))
        self.queue.put(("progress", 0.0))
        self.queue.put(("download_complete", {"canceled": canceled}))

    def _process_queue(self) -> None:
        try:
            while True:
                message, payload = self.queue.get_nowait()
                if message == "log":
                    self._append_log(str(payload))
                elif message == "status":
                    self.status_var.set(str(payload))
                elif message == "progress":
                    value: float
                    label_text: Optional[str] = None
                    if isinstance(payload, dict):
                        value = float(payload.get("value", 0.0))
                        label_text = payload.get("label")
                    else:
                        value = float(payload)
                    self.progress_var.set(value)
                    if label_text is None:
                        label_text = f"{value:5.1f}%"
                    self.progress_label_var.set(label_text)
                elif message == "sets_loaded":
                    data, metadata = payload
                    self._on_sets_loaded(data, metadata)
                elif message == "error":
                    messagebox.showerror(self._t("error_title"), str(payload))
                elif message == "confirm_download":
                    total_cards, estimated_gb, event, decision_holder = payload
                    proceed = False
                    try:
                        proceed = messagebox.askyesno(
                            self._t("download_large_title"),
                            self._t("download_large_text", cards=total_cards, gb=estimated_gb),
                        )
                    finally:
                        decision_holder["proceed"] = bool(proceed)
                        event.set()
                elif message == "download_complete":
                    canceled = False
                    if isinstance(payload, dict):
                        canceled = bool(payload.get("canceled"))
                    else:
                        canceled = bool(payload)
                    self._on_download_complete(canceled)
        except Empty:
            pass
        finally:
            self.root.after(150, self._process_queue)

    def _auto_bootstrap_task(self) -> None:
        remote_meta = fetch_allprintings_remote_meta()
        if remote_meta is None:
            self.queue.put(("log", self._t("meta_fail")))

        if needs_database_update(remote_meta):
            self._download_database_task(remote_meta=remote_meta)

        if ALL_PRINTINGS_FILE.exists():
            self._load_sets_task()

    def _append_log(self, text: str) -> None:
        self.log_widget.configure(state=tk.NORMAL)
        self.log_widget.insert(tk.END, f"{text}\n")
        self.log_widget.see(tk.END)
        self.log_widget.configure(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    MagicDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
