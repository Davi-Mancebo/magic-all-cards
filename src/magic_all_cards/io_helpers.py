"""Pure helper utilities shared across the GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from . import constants as const


def sanitize_filename(name: str) -> str:
    safe = "".join(char for char in name if char.isalnum() or char in " -_#")
    return safe.strip() or "carta"


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_rarity_folder_name(rarity_value: Optional[str]) -> str:
    if not rarity_value:
        return "0-SemRaridade"
    cleaned = rarity_value.lower().strip()
    if not cleaned:
        return "0-SemRaridade"
    if cleaned in const.RARITY_FOLDER_LABELS:
        return const.RARITY_FOLDER_LABELS[cleaned]
    fallback = sanitize_filename(cleaned.title())
    return fallback or "0-SemRaridade"


def get_color_folder_name(card: Dict[str, Any]) -> str:
    colors = card.get("colors") or card.get("colorIdentity") or []
    if isinstance(colors, str):
        colors = list(colors)
    unique_colors = sorted({c for c in colors if isinstance(c, str)})
    if not unique_colors:
        return "0-Incolor"
    if len(unique_colors) == 1:
        label = const.COLOR_FOLDER_LABELS.get(unique_colors[0], unique_colors[0])
        return sanitize_filename(label) or "0-Incolor"
    return "7-Multicolor"


def get_type_folder_name(card: Dict[str, Any]) -> str:
    types = card.get("types") or []
    normalized = [str(t) for t in types]
    for keyword, label in const.TYPE_PRIORITY:
        if keyword in normalized:
            return label
    if normalized:
        return sanitize_filename(f"8-{normalized[0]}") or "8-Outros"
    return "8-Outros"


def get_language_folder_name(language_code: Optional[str]) -> str:
    code = (language_code or "en").lower()
    return const.LANGUAGE_FOLDER_LABELS.get(code, f"99-{code.upper()}")


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
