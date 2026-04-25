from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from vtf.errors import EnvironmentError as VtfEnvError
from vtf.errors import RemoteError
from vtf.platforms import detect


def download(*, meta: dict[str, Any], cfg: Any, workdir: Path) -> Path:
    yt_dlp = os.environ.get("VTF_YT_DLP") or shutil.which("yt-dlp")
    if not yt_dlp:
        raise VtfEnvError("yt-dlp 未找到。请 `pip install yt-dlp` 或设置 VTF_YT_DLP")
    workdir.mkdir(parents=True, exist_ok=True)
    out_path = workdir / f"{meta['video_id']}.{cfg.download.audio_format}"
    platform = detect(meta["url"])
    cmd = [
        yt_dlp,
        "--retries",
        str(cfg.download.retries),
        "--fragment-retries",
        str(cfg.download.retries),
        "-f",
        "bestaudio",
        "-x",
        "--audio-format",
        cfg.download.audio_format,
        "--audio-quality",
        cfg.download.audio_quality,
        "-o",
        str(out_path),
        *platform.cookie_args(cfg),
        meta["url"],
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RemoteError(f"yt-dlp 下载失败({r.returncode}):{r.stderr.strip()[:200]}")
    return out_path
