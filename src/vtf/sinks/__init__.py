from __future__ import annotations

from vtf.errors import UserError
from vtf.sinks.base import EmitOutcome, Sink
from vtf.sinks.feishu import Feishu
from vtf.sinks.markdown import Markdown


def get(name: str) -> Sink:
    for s in (Markdown(), Feishu()):
        if s.name == name:
            return s
    raise UserError(f"unknown sink: {name!r}; allowed: markdown, feishu")


__all__ = ["EmitOutcome", "Sink", "get"]
