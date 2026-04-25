from __future__ import annotations

import re
from typing import Any

from vtf.platforms._normalize import _common_normalize


class YouTube:
    name = "youtube"
    _pat = re.compile(r"(?:youtube\.com|youtu\.be)")

    def matches(self, url: str) -> bool:
        return bool(self._pat.search(url))

    def cookie_args(self, cfg: Any) -> list[str]:
        y = cfg.platform.youtube
        if y.cookies_file:
            return ["--cookies", y.cookies_file]
        if y.cookies_from_browser:
            return ["--cookies-from-browser", y.cookies_from_browser]
        return []

    def normalize_metadata(self, raw: dict[str, Any]) -> dict[str, Any]:
        out = _common_normalize(raw, platform="youtube")
        out["reply"] = raw.get("comment_count", 0)
        return out