from __future__ import annotations

from typing import Any

from vtf.errors import UserError


def assemble(
    *,
    meta: dict[str, Any],
    lines: list[str],
    analyses: list[dict[str, Any]],
) -> dict[str, Any]:
    analyses_by_kind: dict[str, dict[str, Any]] = {}
    for a in analyses:
        if a.get("result") is None:
            raise UserError(f"analyze {a.get('kind')} result not filled")
        analyses_by_kind[a["kind"]] = a["result"]
    return {
        "meta": meta,
        "lines": lines,
        "analyses": analyses_by_kind,
    }
