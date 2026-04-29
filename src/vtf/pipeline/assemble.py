from __future__ import annotations

from typing import Any

from vtf.errors import UserError

_REQUIRED_KINDS = {"summary", "breakdown", "rewrite"}


def assemble(
    *,
    meta: dict[str, Any],
    lines: list[str],
    analyses: list[dict[str, Any]],
) -> dict[str, Any]:
    if not meta.get("thumbnail"):
        raise UserError("meta.thumbnail missing; final output must include cover URL")

    analyses_by_kind: dict[str, dict[str, Any]] = {}
    for a in analyses:
        if a.get("result") is None:
            raise UserError(f"analyze {a.get('kind')} result not filled")
        analyses_by_kind[a["kind"]] = a["result"]

    present = set(analyses_by_kind)
    missing = _REQUIRED_KINDS - present
    if missing:
        raise UserError(
            f"缺少必填分析: {', '.join(sorted(missing))}。"
            f"请先完成 summarize/breakdown/rewrite 三个分析的 LLM 回填。"
        )

    return {
        "meta": meta,
        "lines": lines,
        "analyses": analyses_by_kind,
    }
