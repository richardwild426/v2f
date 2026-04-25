from __future__ import annotations

from typing import Any

from vtf.errors import UserError
from vtf.prompts import load_prompt, render_prompt

_KINDS = {"summary", "breakdown", "rewrite"}

_SCHEMA_HINTS = {
    "summary": "expected: {text, points[], tags[]}",
    "breakdown": "expected: {hook, core, cta, pros, suggestions, text}",
    "rewrite": "expected: {text}",
}


def analyze(
    *,
    kind: str,
    meta: dict[str, Any],
    lines: list[str],
    cfg: Any,
) -> dict[str, Any]:
    if kind not in _KINDS:
        raise UserError(f"unknown analyze kind: {kind!r}; allowed: {sorted(_KINDS)}")
    override = getattr(cfg.analyze.prompts, kind, "") or ""
    template = load_prompt(kind, override_path=override)
    prompt = render_prompt(
        template,
        {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "platform": meta.get("platform", ""),
            "lines": lines,
        },
    )
    return {
        "kind": kind,
        "prompt": prompt,
        "context": {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "platform": meta.get("platform", ""),
            "lines_count": len(lines),
        },
        "schema_hint": _SCHEMA_HINTS[kind],
        "result": None,
    }
