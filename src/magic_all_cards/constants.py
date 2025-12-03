"""Shared constants and configuration for Magic All Cards."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Callable, Dict, List, Optional


def resolve_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    resolved = Path(__file__).resolve()
    try:
        return resolved.parents[2]
    except IndexError:
        return resolved.parent


BASE_DIR = resolve_base_dir()
ALL_PRINTINGS_URL = "https://mtgjson.com/api/v5/AllPrintings.json"
META_URL = "https://mtgjson.com/api/v5/Meta.json"
ALL_PRINTINGS_FILE = BASE_DIR / "AllPrintings.json"
ALL_PRINTINGS_META_FILE = BASE_DIR / "AllPrintings.meta.json"
LOCALE_CONFIG_FILE = BASE_DIR / "config.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "MTG_IMAGES"
REQUEST_TIMEOUT = 25
REQUEST_DELAY = 0.05
CARD_WARNING_THRESHOLD = 40000
CARD_WARNING_MB_PER_IMAGE = 0.24
IMAGE_DOWNLOAD_RETRIES = 3
IMAGE_RETRY_DELAY = 1.0
LANGUAGE_AUTO_FALLBACK_THRESHOLD = 3

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

LANGUAGE_FOLDER_INDEX: Dict[str, int] = {
    code: index + 1 for index, (_name, code) in enumerate(SCRYFALL_LANGUAGE_CHOICES)
}

LANGUAGE_NAMES_BY_APP_LANG: Dict[str, Dict[str, str]] = {
    "en": {code: name for name, code in SCRYFALL_LANGUAGE_CHOICES},
    "pt": {
        "en": "Inglês",
        "es": "Espanhol",
        "fr": "Francês",
        "de": "Alemão",
        "it": "Italiano",
        "pt": "Português",
        "ja": "Japonês",
        "ko": "Coreano",
        "ru": "Russo",
        "zhs": "Chinês Simplificado",
        "zht": "Chinês Tradicional",
        "he": "Hebraico",
        "la": "Latim",
        "grc": "Grego Antigo",
        "ar": "Árabe",
        "sa": "Sânscrito",
        "ph": "Phyrexiano",
        "qya": "Quenya",
    },
}

def get_language_display_map(app_language: str) -> Dict[str, str]:
    """Return localized language choices keyed by label."""

    fallback = LANGUAGE_NAMES_BY_APP_LANG.get(DEFAULT_APP_LANGUAGE, {})
    localized = LANGUAGE_NAMES_BY_APP_LANG.get(app_language, fallback)
    mapping: Dict[str, str] = {}
    for code in LANGUAGE_FOLDER_INDEX:
        label = localized.get(code) or fallback.get(code) or code.upper()
        mapping[f"{label} ({code.upper()})"] = code
    return mapping

LANGUAGE_NAME_TO_CODE: Dict[str, str] = {
    name.lower(): code for name, code in SCRYFALL_LANGUAGE_CHOICES
}

LANGUAGE_NAME_TO_CODE.update(
    {
        "portuguese (brazil)": "pt",
        "chinese simplified": "zhs",
        "chinese traditional": "zht",
        "spanish (latin america)": "es",
    }
)

CARD_TYPE_RULES: Dict[str, Callable[[Dict[str, Any]], bool]] = {
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

RARITY_FOLDER_LABELS: Dict[str, Dict[str, str]] = {
    "pt": {
        "common": "1-Comum",
        "uncommon": "2-Incomum",
        "rare": "3-Rara",
        "mythic": "4-Mítica",
        "special": "5-Especial",
        "bonus": "6-Bônus",
        "__default__": "0-SemRaridade",
    },
    "en": {
        "common": "1-Common",
        "uncommon": "2-Uncommon",
        "rare": "3-Rare",
        "mythic": "4-Mythic",
        "special": "5-Special",
        "bonus": "6-Bonus",
        "__default__": "0-NoRarity",
    },
}

COLOR_FOLDER_LABELS: Dict[str, Dict[str, str]] = {
    "pt": {
        "W": "1-Branca",
        "U": "2-Azul",
        "B": "3-Preta",
        "R": "4-Vermelha",
        "G": "5-Verde",
        "C": "0-Incolor",
        "__colorless__": "0-Incolor",
        "__multicolor__": "7-Multicolor",
    },
    "en": {
        "W": "1-White",
        "U": "2-Blue",
        "B": "3-Black",
        "R": "4-Red",
        "G": "5-Green",
        "C": "0-Colorless",
        "__colorless__": "0-Colorless",
        "__multicolor__": "7-Multicolor",
    },
}

TYPE_PRIORITY: List[tuple[str, Dict[str, str]]] = [
    ("Land", {"pt": "0-Terreno", "en": "0-Land"}),
    ("Creature", {"pt": "1-Criatura", "en": "1-Creature"}),
    ("Planeswalker", {"pt": "2-Planeswalker", "en": "2-Planeswalker"}),
    ("Instant", {"pt": "3-Instante", "en": "3-Instant"}),
    ("Sorcery", {"pt": "4-Feitiço", "en": "4-Sorcery"}),
    ("Enchantment", {"pt": "5-Encantamento", "en": "5-Enchantment"}),
    ("Artifact", {"pt": "6-Artefato", "en": "6-Artifact"}),
    ("Battle", {"pt": "7-Batalha", "en": "7-Battle"}),
]

TYPE_DEFAULT_FOLDER: Dict[str, str] = {
    "pt": "8-Outros",
    "en": "8-Others",
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
        "log_download_retry": "Tentativa {attempt}/{total} falhou [{lang}]: {set_name} - {card_name}. Motivo: {error}",
        "log_download_failure": "Falhou [{lang}] após {attempts} tentativas: {set_name} - {card_name}. Motivo: {error}",
        "log_language_unavailable": "Idioma {lang} indisponível para {set_name}. Usando fallback EN para o restante do set.",
        "progress_cards_label": "{percent}% ({downloaded}/{total} cartas)",
        "card_fallback_name": "Carta",
        "error_title": "Erro",
        "error_unknown": "Motivo desconhecido",
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
        "log_db_redownload": "Clique em 'Download/Update MTGJSON' caso o download não reinicie sozinho.",
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
        "log_download_retry": "Attempt {attempt}/{total} failed [{lang}]: {set_name} - {card_name}. Reason: {error}",
        "log_download_failure": "Failed [{lang}] after {attempts} attempts: {set_name} - {card_name}. Reason: {error}",
        "log_language_unavailable": "Language {lang} unavailable for {set_name}. Using EN fallback for the rest of this set.",
        "progress_cards_label": "{percent}% ({downloaded}/{total} cards)",
        "card_fallback_name": "Card",
        "error_title": "Error",
        "error_unknown": "Unknown reason",
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
        "log_db_redownload": "Click 'Download/Update MTGJSON' if the download does not restart automatically.",
        "select_language": "Select the application language.",
        "clear_selection": "Clear selection",
        "log_download_stopped": "Download stopped by the user.",
    },
}
