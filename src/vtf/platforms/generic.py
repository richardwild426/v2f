from __future__ import annotations

from typing import Any

from vtf.platforms._normalize import _common_normalize


class Generic:
    name = "generic"

    def matches(self, url: str) -> bool:
        return False

    def cookie_args(self, cfg: Any) -> list[str]:
        return []

    def normalize_metadata(self, raw: dict[str, Any]) -> dict[str, Any]:
        return _common_normalize(raw, platform="generic")