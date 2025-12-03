"""Configuration persistence helpers for Magic All Cards."""

from __future__ import annotations

import json
from typing import Any, Dict

from . import constants as const


def load_config() -> Dict[str, Any]:
    if not const.LOCALE_CONFIG_FILE.exists():
        return {}
    try:
        with const.LOCALE_CONFIG_FILE.open(encoding="utf-8") as handler:
            return json.load(handler)
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data: Dict[str, Any]) -> None:
    try:
        const.LOCALE_CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass
