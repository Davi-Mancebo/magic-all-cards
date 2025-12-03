"""Pure helper utilities shared across the GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote
import unicodedata

import requests

from . import constants as const


def sanitize_filename(name: str) -> str:
    safe = "".join(char for char in name if char.isalnum() or char in " -_#")
    return safe.strip() or "carta"


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_language_map(mapping: Dict[str, Dict[str, str]], app_language: Optional[str]) -> Dict[str, str]:
    lang = (app_language or const.DEFAULT_APP_LANGUAGE).lower()
    return mapping.get(lang) or mapping.get(const.DEFAULT_APP_LANGUAGE, {})


def get_rarity_folder_name(rarity_value: Optional[str], app_language: Optional[str] = None) -> str:
    lang_map = _get_language_map(const.RARITY_FOLDER_LABELS, app_language)
    fallback_map = _get_language_map(const.RARITY_FOLDER_LABELS, const.DEFAULT_APP_LANGUAGE)
    default_label = lang_map.get("__default__") or fallback_map.get("__default__") or "0-Rarity"
    cleaned = (rarity_value or "").lower().strip()
    if cleaned and cleaned in lang_map:
        return lang_map[cleaned]
    if cleaned and cleaned in fallback_map:
        return fallback_map[cleaned]
    if cleaned:
        fallback = sanitize_filename(cleaned.title())
        return fallback or default_label
    return default_label


def get_color_folder_name(card: Dict[str, Any], app_language: Optional[str] = None) -> str:
    colors = card.get("colors") or card.get("colorIdentity") or []
    if isinstance(colors, str):
        colors = list(colors)
    unique_colors = sorted({c for c in colors if isinstance(c, str)})
    lang_map = _get_language_map(const.COLOR_FOLDER_LABELS, app_language)
    fallback_map = _get_language_map(const.COLOR_FOLDER_LABELS, const.DEFAULT_APP_LANGUAGE)
    colorless_label = lang_map.get("__colorless__") or fallback_map.get("__colorless__") or "0-Colorless"
    multicolor_label = lang_map.get("__multicolor__") or fallback_map.get("__multicolor__") or "7-Multicolor"
    if not unique_colors:
        return colorless_label
    if len(unique_colors) == 1:
        key = unique_colors[0]
        label = lang_map.get(key) or fallback_map.get(key)
        if label:
            return label
        return sanitize_filename(f"1-{key}") or colorless_label
    return multicolor_label


def get_type_folder_name(card: Dict[str, Any], app_language: Optional[str] = None) -> str:
    types = card.get("types") or []
    normalized = [str(t) for t in types]
    lang = (app_language or const.DEFAULT_APP_LANGUAGE).lower()
    fallback_lang = const.DEFAULT_APP_LANGUAGE
    default_label = (
        const.TYPE_DEFAULT_FOLDER.get(lang)
        or const.TYPE_DEFAULT_FOLDER.get(fallback_lang)
        or "8-Others"
    )
    for keyword, labels in const.TYPE_PRIORITY:
        if keyword in normalized:
            return labels.get(lang) or labels.get(fallback_lang) or default_label
    if normalized:
        fallback = sanitize_filename(f"8-{normalized[0]}")
        return fallback or default_label
    return default_label


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def get_language_folder_name(language_code: Optional[str], app_language: Optional[str] = None) -> str:
    code = (language_code or "en").lower()
    index = const.LANGUAGE_FOLDER_INDEX.get(code, 99)
    names = const.LANGUAGE_NAMES_BY_APP_LANG.get(app_language or const.DEFAULT_APP_LANGUAGE)
    fallback = const.LANGUAGE_NAMES_BY_APP_LANG.get(const.DEFAULT_APP_LANGUAGE, {})
    label = (names or {}).get(code) or fallback.get(code) or code.upper()
    sanitized = _strip_accents(label)
    cleaned = "".join(ch for ch in sanitized if ch.isalnum()) or code.upper()
    return f"{index:02d}-{cleaned}"


def get_scryfall_id(card: Dict[str, Any]) -> Optional[str]:
    identifiers = card.get("identifiers") or {}
    return card.get("scryfallId") or identifiers.get("scryfallId")


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


def download_binary(url: str, destination: Path) -> tuple[bool, Optional[str]]:
    try:
        response = requests.get(url, timeout=const.REQUEST_TIMEOUT)
        if response.status_code == 200:
            destination.write_bytes(response.content)
            return True, None
        return False, f"status {response.status_code}"
    except requests.RequestException as exc:
        return False, str(exc)
