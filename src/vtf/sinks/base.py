from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class EmitOutcome:
    sink: str
    degraded: bool = False
    reason: str = ""


class Sink(Protocol):
    name: str

    def available(self, cfg: Any) -> tuple[bool, str]: ...
    def emit(self, result: dict[str, Any], cfg: Any) -> EmitOutcome: ...
