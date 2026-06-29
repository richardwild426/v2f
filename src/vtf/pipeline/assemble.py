from __future__ import annotations

from typing import Any

from vtf.errors import UserError
from vtf.sinks.schema import is_missing_value, resolve_path

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
        _check_result_completeness(a)
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


def _check_result_completeness(analysis: dict[str, Any]) -> None:
    """按 analyze 写入的 required_result_fields 提前校验 result 完整性。

    opt-in：仅当条目携带 required_result_fields 时校验（markdown sink / 无飞书
    schema 时为空，跳过）。把缺失就近报在 assemble 阶段，而非拖到 emit。
    """
    required = analysis.get("required_result_fields") or []
    if not required:
        return
    kind = analysis.get("kind")
    result = analysis["result"]
    missing: list[str] = []
    for item in required:
        path = str(item.get("result_path", ""))
        row_fields = item.get("row_fields") or []
        value = resolve_path(result, path)
        if row_fields:
            if not isinstance(value, list) or not value:
                missing.append(f"{path}（应为非空分镜数组）")
                continue
            for index, raw_row in enumerate(value, start=1):
                if not isinstance(raw_row, dict):
                    missing.append(f"{path}[{index}]（应为对象）")
                    continue
                for rf in row_fields:
                    if not rf.get("required", True):
                        continue
                    if is_missing_value(resolve_path(raw_row, str(rf.get("result_path", "")))):
                        missing.append(f"{path}[{index}].{rf.get('result_path')}")
        elif is_missing_value(value):
            missing.append(path)
    if missing:
        raise UserError(
            f"analyze {kind} result 缺少下游必填字段，已停止装配: {', '.join(missing)}"
        )
