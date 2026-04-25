from __future__ import annotations

import re
from typing import Any

from vtf.platforms._normalize import _common_normalize


class Bilibili:
    name = "bilibili"
    _pat = re.compile(r"(?:bilibili\.com|b23\.tv)")

    def matches(self, url: str) -> bool:
        return bool(self._pat.search(url))

    def cookie_args(self, cfg: Any) -> list[str]:
        b = cfg.platform.bilibili
        if b.cookies_file:
            return ["--cookies", b.cookies_file]
        if b.cookies_from_browser:
            return ["--cookies-from-browser", b.cookies_from_browser]
        return []

    def normalize_metadata(self, raw: dict[str, Any]) -> dict[str, Any]:
        return _common_normalize(raw, platform="bilibili")