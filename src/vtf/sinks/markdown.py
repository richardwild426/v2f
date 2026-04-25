from __future__ import annotations

from typing import Any

from vtf.sinks.base import EmitOutcome


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

        md = f"""# 🎬 视频分析报告

## 基本信息

| 字段 | 内容 |
|------|------|
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

## ✍️ 二创改写（可选）

{rewrite.get('text', '')}

---

## 📊 摘要

{summary.get('text', '')}

---

## 🔍 视频拆解

{breakdown.get('text', '')}
"""
        return EmitOutcome(sink="markdown", reason=md)
