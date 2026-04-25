from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any


def _common_normalize(raw: dict[str, Any], *, platform: str) -> dict[str, Any]:
    upload_date = raw.get("upload_date", "") or ""
    if upload_date and len(upload_date) == 8:
        with contextlib.suppress(ValueError):
            upload_date = datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d %H:%M")
    duration = int(raw.get("duration") or 0)
    return {
        "platform": platform,
        "video_id": raw.get("id", "") or "",
        "url": raw.get("webpage_url", "") or "",
        "title": raw.get("title", "") or "",
        "author": raw.get("uploader", "") or "",
        "upload_date": upload_date,
        "duration": duration,
        "duration_str": f"{duration // 60}:{duration % 60:02d}",
        "thumbnail": raw.get("thumbnail", "") or "",
        "description": (raw.get("description", "") or "")[:500],
        "view": int(raw.get("view_count") or 0),
        "like": int(raw.get("like_count") or 0),
        "favorite": 0,
        "share": 0,
        "reply": 0,
    }
