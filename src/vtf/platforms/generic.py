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
        out = _common_normalize(raw, platform="generic")
        out["reply"] = int(raw.get("comment_count") or 0)
        out["favorite"] = int(raw.get("favorite_count") or 0)
        out["share"] = int(raw.get("repost_count") or 0)
        return out
