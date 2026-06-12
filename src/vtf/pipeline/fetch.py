from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

from vtf.errors import EnvironmentError as VtfEnvError
from vtf.errors import RemoteError
from vtf.pipeline.yt_dlp import format_yt_dlp_error
from vtf.platforms import detect


def fetch(*, url: str, cfg: Any) -> dict[str, Any]:
    yt_dlp = os.environ.get("VTF_YT_DLP") or shutil.which("yt-dlp")
    if not yt_dlp:
        raise VtfEnvError("yt-dlp 未找到。请 `pip install yt-dlp` 或设置 VTF_YT_DLP")
    platform = detect(url)
    cmd = [yt_dlp, "-J", *platform.cookie_args(cfg), url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RemoteError(
            format_yt_dlp_error(
                action="抓取元数据",
                returncode=r.returncode,
                stderr=r.stderr,
                platform=platform,
            )
        )
    raw = json.loads(r.stdout)
    return platform.normalize_metadata(raw)
