from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vtf.errors import UserError


@dataclass(frozen=True)
class MissingField:
    name: str
    source: str


@dataclass(frozen=True)
class RequiredAnalysisField:
    name: str
    source: str
    result_path: str


@dataclass(frozen=True)
class StoryboardSchema:
    table_name: str
    rows_source: str
    link_field: str
    master_link_field: str
    fields: list[dict[str, Any]]


def load_schema_fields(schema_path: Path) -> list[dict[str, Any]]:
    schema = _load_schema(schema_path)
    fields_def = schema.get("fields", [])
    if not fields_def:
        raise UserError(f"schema 文件无 fields 定义: {schema_path}")
    return list(fields_def)


def load_storyboard_schema(schema_path: Path) -> StoryboardSchema | None:
    schema = _load_schema(schema_path)
    raw = schema.get("storyboard")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise UserError(f"schema storyboard 定义必须是 TOML table: {schema_path}")

    rows_source = str(raw.get("rows_source", "")).strip()
    if not rows_source:
        raise UserError(f"schema storyboard 缺少 rows_source: {schema_path}")

    fields_def = raw.get("fields", [])
    if not isinstance(fields_def, list) or not fields_def:
        raise UserError(f"schema storyboard 无 fields 定义: {schema_path}")

    fields_out: list[dict[str, Any]] = []
    for item in fields_def:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        source = str(item.get("source", "")).strip()
        if not name or not source:
            continue
        fields_out.append(
            {
                "name": name,
                "type": str(item.get("type", "text")),
                "source": source,
            }
        )
    if not fields_out:
        raise UserError(f"schema storyboard 解析后字段列表为空: {schema_path}")

    return StoryboardSchema(
        table_name=str(raw.get("table_name", "分镜明细")),
        rows_source=rows_source,
        link_field=str(raw.get("link_field", "所属视频")),
        master_link_field=str(raw.get("master_link_field", "脚本拆解")),
        fields=fields_out,
    )


def storyboard_required_analysis_field(
    storyboard: StoryboardSchema | None, kind: str
) -> RequiredAnalysisField | None:
    if storyboard is None:
        return None
    prefix = f"analyses.{kind}."
    path = source_path(storyboard.rows_source)
    if not path.startswith(prefix):
        return None
    return RequiredAnalysisField(
        name=storyboard.table_name,
        source=storyboard.rows_source,
        result_path=path.removeprefix(prefix),
    )


def resolve_path(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def render_field(data: dict[str, Any], expr: str) -> Any:
    if "|" in expr:
        left, right = (s.strip() for s in expr.split("|", 1))
        value = resolve_path(data, left)
        return _apply_transformer(value, right)
    return resolve_path(data, expr)


def source_path(expr: str) -> str:
    if "|" in expr:
        left, _ = (s.strip() for s in expr.split("|", 1))
        return left
    return expr.strip()


def is_required_field(field_def: dict[str, Any]) -> bool:
    return True


def missing_required_fields(
    data: dict[str, Any], fields_def: list[dict[str, Any]]
) -> list[MissingField]:
    missing: list[MissingField] = []
    for field_def in fields_def:
        name = str(field_def.get("name", ""))
        source = str(field_def.get("source", ""))
        if not name or not source or not is_required_field(field_def):
            continue
        value = render_field(data, source)
        if _is_missing_value(value):
            missing.append(MissingField(name=name, source=source))
    return missing


def required_analysis_fields(
    fields_def: list[dict[str, Any]], kind: str
) -> list[RequiredAnalysisField]:
    prefix = f"analyses.{kind}."
    out: list[RequiredAnalysisField] = []
    for field_def in fields_def:
        name = str(field_def.get("name", ""))
        source = str(field_def.get("source", ""))
        path = source_path(source)
        if not name or not source or not is_required_field(field_def):
            continue
        if not path.startswith(prefix):
            continue
        out.append(
            RequiredAnalysisField(
                name=name,
                source=source,
                result_path=path.removeprefix(prefix),
            )
        )
    return out


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _apply_transformer(value: Any, name: str) -> Any:
    if name == "joined":
        if not isinstance(value, list):
            return ""
        return "\n".join(str(x) for x in value)
    if name == "tags_hashtag":
        if not isinstance(value, list):
            return ""
        return " ".join(str(x) for x in value)
    if name == "stats_compact":
        if not isinstance(value, dict):
            return ""
        return (
            f"播放{value.get('view', 0)} | 点赞{value.get('like', 0)} | "
            f"收藏{value.get('favorite', 0)} | 分享{value.get('share', 0)} | "
            f"评论{value.get('reply', 0)}"
        )
    raise UserError(f"unknown transformer: {name!r}; allowed: joined, tags_hashtag, stats_compact")


def _load_schema(schema_path: Path) -> dict[str, Any]:
    return tomllib.loads(schema_path.read_text("utf-8"))
