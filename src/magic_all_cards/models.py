"""Data models shared across modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SetMetadata:
    code: str
    name: str
    release: str
    search: str
