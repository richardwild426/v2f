from __future__ import annotations

from typing import Any, Protocol


class Platform(Protocol):
    name: str

    def matches(self, url: str) -> bool: ...
    def cookie_args(self, cfg: Any) -> list[str]: ...
    def normalize_metadata(self, raw: dict[str, Any]) -> dict[str, Any]: ...
