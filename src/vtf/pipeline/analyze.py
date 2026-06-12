from __future__ import annotations

from typing import Any

from vtf.config import resolve_feishu_schema_path
from vtf.errors import UserError
from vtf.prompts import load_prompt, render_prompt
from vtf.sinks.schema import (
    RequiredAnalysisField,
    load_schema_fields,
    required_analysis_fields,
)

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
    downstream_fields = _downstream_fields(kind, cfg)
    return {
        "kind": kind,
        "prompt": prompt,
        "context": {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "platform": meta.get("platform", ""),
            "lines_count": len(lines),
        },
        "schema_hint": _schema_hint(kind, downstream_fields),
        "required_result_fields": [
            {
                "field": item.name,
                "source": item.source,
                "result_path": item.result_path,
            }
            for item in downstream_fields
        ],
        "result": None,
    }


def _downstream_fields(kind: str, cfg: Any) -> list[RequiredAnalysisField]:
    schema_path = resolve_feishu_schema_path(cfg)
    if not schema_path.exists():
        return []
    fields_def = load_schema_fields(schema_path)
    return required_analysis_fields(fields_def, kind)


def _schema_hint(kind: str, fields: list[RequiredAnalysisField]) -> str:
    if not fields:
        return _SCHEMA_HINTS[kind]
    required = ", ".join(item.result_path for item in fields)
    return f"{_SCHEMA_HINTS[kind]}; required for Feishu: {required}"
