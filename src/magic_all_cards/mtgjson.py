"""MTGJSON metadata helpers."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from . import constants as const
from .models import SetMetadata


def fetch_allprintings_remote_meta() -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(const.META_URL, timeout=const.REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        return None

    data = payload.get("data") or []
    candidates = data.values() if isinstance(data, dict) else data

    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("fileName")
        file_name = entry.get("fileName") or entry.get("name")
        if name == "AllPrintings" or file_name == "AllPrintings.json":
            return entry
    return None


def load_local_meta() -> Optional[Dict[str, Any]]:
    if not const.ALL_PRINTINGS_META_FILE.exists():
        return None
    try:
        with const.ALL_PRINTINGS_META_FILE.open(encoding="utf-8") as handler:
            return json.load(handler)
    except (OSError, json.JSONDecodeError):
        return None


def save_local_meta(meta_entry: Dict[str, Any]) -> None:
    try:
        const.ALL_PRINTINGS_META_FILE.write_text(json.dumps(meta_entry, indent=2), encoding="utf-8")
    except OSError:
        pass


def needs_database_update(remote_meta: Optional[Dict[str, Any]]) -> bool:
    if not const.ALL_PRINTINGS_FILE.exists():
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


def download_allprintings(
    remote_meta: Optional[Dict[str, Any]],
    progress_hook: Optional[Callable[[float, float], None]] = None,
) -> Tuple[bool, Optional[str]]:
    try:
        if not const.ALL_PRINTINGS_FILE.parent.exists():
            const.ALL_PRINTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(const.ALL_PRINTINGS_URL, stream=True, timeout=60)
        response.raise_for_status()

        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        start_time = time.perf_counter()
        with const.ALL_PRINTINGS_FILE.open("wb") as file_handle:
            for chunk in response.iter_content(chunk_size=1024 * 512):
                if not chunk:
                    continue
                file_handle.write(chunk)
                downloaded += len(chunk)
                if progress_hook and total:
                    percent = (downloaded / total) * 100
                    elapsed = max(time.perf_counter() - start_time, 1e-6)
                    speed = downloaded / elapsed / (1024 * 1024)
                    progress_hook(percent, speed)

        if remote_meta:
            save_local_meta(remote_meta)
        elif const.ALL_PRINTINGS_META_FILE.exists():
            try:
                const.ALL_PRINTINGS_META_FILE.unlink()
            except OSError:
                pass
        return True, None
    except (requests.RequestException, OSError) as exc:
        return False, str(exc)


def load_sets_from_file() -> Tuple[Dict[str, Any], List[SetMetadata]]:
    with const.ALL_PRINTINGS_FILE.open(encoding="utf-8") as handler:
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
    return data, metadata


def reset_local_database() -> None:
    for file_path in (const.ALL_PRINTINGS_FILE, const.ALL_PRINTINGS_META_FILE):
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            pass
