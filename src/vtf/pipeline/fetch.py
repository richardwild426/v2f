from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

from vtf.errors import EnvironmentError as VtfEnvError
from vtf.errors import RemoteError
from vtf.platforms import detect


def fetch(*, url: str, cfg: Any) -> dict[str, Any]:
    yt_dlp = os.environ.get("VTF_YT_DLP") or shutil.which("yt-dlp")
    if not yt_dlp:
        raise VtfEnvError("yt-dlp 未找到。请 `pip install yt-dlp` 或设置 VTF_YT_DLP")
    platform = detect(url)
    cmd = [yt_dlp, "-J", *platform.cookie_args(cfg), url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RemoteError(f"yt-dlp 失败({r.returncode}):{r.stderr.strip()[:200]}")
    raw = json.loads(r.stdout)
    return platform.normalize_metadata(raw)
