from __future__ import annotations

from typing import Any

from vtf.config import resolve_feishu_schema_path
from vtf.errors import UserError
from vtf.prompts import load_prompt, render_prompt
from vtf.sinks.schema import (
    RequiredAnalysisField,
    load_schema_fields,
    load_storyboard_schema,
    required_analysis_fields,
    storyboard_required_analysis_field,
)

_KINDS = {"summary", "breakdown", "rewrite"}


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
        "schema_hint": _schema_hint(downstream_fields),
        "required_result_fields": [_required_field_entry(item) for item in downstream_fields],
        "result": None,
    }


def _required_field_entry(item: RequiredAnalysisField) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "field": item.name,
        "source": item.source,
        "result_path": item.result_path,
    }
    if item.row_fields:
        entry["row_fields"] = [
            {"field": rf.name, "result_path": rf.result_path, "required": rf.required}
            for rf in item.row_fields
        ]
    return entry


def _downstream_fields(kind: str, cfg: Any) -> list[RequiredAnalysisField]:
    schema_path = resolve_feishu_schema_path(cfg)
    if not schema_path.exists():
        return []
    fields_def = load_schema_fields(schema_path)
    out = required_analysis_fields(fields_def, kind)
    storyboard = load_storyboard_schema(schema_path)
    storyboard_field = storyboard_required_analysis_field(storyboard, kind)
    if storyboard_field is not None:
        out.append(storyboard_field)
    return out


def _schema_hint(fields: list[RequiredAnalysisField]) -> str:
    """仅描述下游飞书必填字段；result 的形状以 prompt 模板为权威。

    无下游 schema（如 markdown sink）时返回空串，agent 按 prompt 输出即可。
    """
    if not fields:
        return ""
    parts: list[str] = []
    for item in fields:
        if item.row_fields:
            sub = "/".join(rf.result_path for rf in item.row_fields if rf.required)
            parts.append(f"{item.result_path}[]:{{{sub}}}")
        else:
            parts.append(item.result_path)
    return f"required for Feishu: {', '.join(parts)}"
