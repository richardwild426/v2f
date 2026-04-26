from __future__ import annotations

from typing import Any

from vtf.sinks.base import EmitOutcome


def _bullets(items: list[Any] | None) -> str:
    if not items:
        return ""
    return "\n".join(f"- {it}" for it in items)


def _kv_block(d: dict[str, Any], keys: list[tuple[str, str]]) -> str:
    """Render an ordered list of (key, label) pairs from a dict, skipping empties."""
    out = []
    for k, label in keys:
        v = d.get(k)
        if v in (None, "", [], {}):
            continue
        if isinstance(v, list):
            out.append(f"**{label}**\n\n{_bullets(v)}")
        else:
            out.append(f"**{label}**：{v}")
    return "\n\n".join(out)


class Markdown:
    name = "markdown"

    def available(self, cfg: Any) -> tuple[bool, str]:
        return (True, "")

    def emit(self, result: dict[str, Any], cfg: Any) -> EmitOutcome:
        meta = result.get("meta", {})
        lines = result.get("lines", [])
        analyses = result.get("analyses", {})
        summary = analyses.get("summary", {})
        breakdown = analyses.get("breakdown", {})
        rewrite = analyses.get("rewrite", {})

        thumbnail = meta.get("thumbnail", "")
        cover_cell = f"![封面]({thumbnail})<br>{thumbnail}" if thumbnail else ""

        summary_text = summary.get("text", "")
        summary_points = _bullets(summary.get("points"))
        summary_tags = " ".join(summary.get("tags", []) or [])

        breakdown_block = _kv_block(
            breakdown,
            [
                ("hook", "Hook（开场钩子）"),
                ("core", "Core（核心信息）"),
                ("cta", "CTA（行动召唤）"),
                ("pros", "Pros（亮点）"),
                ("suggestions", "Suggestions（优化建议）"),
            ],
        )
        breakdown_text = breakdown.get("text", "")

        rewrite_text = rewrite.get("text", "")
        rewrite_meta = rewrite.get("_meta", {}) or {}
        rewrite_footer = ""
        if rewrite_meta:
            ratio = rewrite_meta.get("比值", "")
            o = rewrite_meta.get("原稿总字数", "")
            r = rewrite_meta.get("改写总字数", "")
            thinking = rewrite_meta.get("thinking", "")
            parts = []
            if thinking:
                parts.append(f"_内核_：{thinking}")
            if ratio or o or r:
                parts.append(f"_字数_：原 {o} → 改 {r}（比值 {ratio}）")
            if parts:
                rewrite_footer = "\n\n" + "  \n".join(parts)

        md = f"""# 🎬 视频分析报告

## 基本信息

| 字段 | 内容 |
|------|------|
| **封面** | {cover_cell} |
| **标题** | {meta.get('title', '')} |
| **作者** | {meta.get('author', '')} |
| **平台** | {meta.get('platform', '')} |
| **时长** | {meta.get('duration_str', '')} |
| **发布时间** | {meta.get('upload_date', '')} |
| **链接** | {meta.get('url', '')} |

## 数据

- 播放数：{meta.get('view', 0)}
- 点赞数：{meta.get('like', 0)}
- 收藏数：{meta.get('favorite', 0)}
- 分享数：{meta.get('share', 0)}
- 评论数：{meta.get('reply', 0)}

---

## 📝 文案提取（{len(lines)}行）

{chr(10).join(lines)}

---

## ✍️ 二创改写

{rewrite_text}{rewrite_footer}

---

## 📊 摘要

{summary_text}

{f"**核心要点**{chr(10)}{chr(10)}{summary_points}" if summary_points else ""}

{f"**标签**：{summary_tags}" if summary_tags else ""}

---

## 🔍 视频拆解

{breakdown_block}

{breakdown_text}
"""
        return EmitOutcome(sink="markdown", reason=md)
