from __future__ import annotations

from vtf.platforms.base import Platform
from vtf.platforms.bilibili import Bilibili
from vtf.platforms.generic import Generic
from vtf.platforms.youtube import YouTube

REGISTRY: list[Platform] = [Bilibili(), YouTube()]
_FALLBACK: Platform = Generic()


def detect(url: str) -> Platform:
    for p in REGISTRY:
        if p.matches(url):
            return p
    return _FALLBACK


__all__ = ["Platform", "detect", "REGISTRY"]