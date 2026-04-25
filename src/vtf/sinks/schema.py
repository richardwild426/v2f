from __future__ import annotations

from typing import Any

from vtf.errors import UserError


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
