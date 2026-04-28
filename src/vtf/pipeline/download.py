from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from vtf.errors import EnvironmentError as VtfEnvError
from vtf.errors import RemoteError
from vtf.platforms import detect


def download(
    *,
    meta: dict[str, Any],
    cfg: Any,
    workdir: Path,
    keep_video: bool = False,
) -> tuple[Path, Path | None]:
    """下载音频；可选同时保留原始视频文件。

    返回 ``(audio_path, video_path)``。``video_path`` 仅在 ``keep_video=True``
    且找得到原视频文件时非 None；否则 None（不视为错误，只是降级到只有音频）。
    """
    yt_dlp = os.environ.get("VTF_YT_DLP") or shutil.which("yt-dlp")
    if not yt_dlp:
        raise VtfEnvError("yt-dlp 未找到。请 `pip install yt-dlp` 或设置 VTF_YT_DLP")
    workdir.mkdir(parents=True, exist_ok=True)
    audio_format = cfg.download.audio_format
    audio_path = workdir / f"{meta['video_id']}.{audio_format}"
    platform = detect(meta["url"])

    if keep_video:
        # 下载 best（合并视频+音频）→ 原视频保留 + 提取 mp3
        out_template = workdir / f"{meta['video_id']}.%(ext)s"
        cmd = [
            yt_dlp,
            "--retries",
            str(cfg.download.retries),
            "--fragment-retries",
            str(cfg.download.retries),
            "-f",
            "best",
            "-k",
            "-x",
            "--audio-format",
            audio_format,
            "--audio-quality",
            cfg.download.audio_quality,
            "-o",
            str(out_template),
            *platform.cookie_args(cfg),
            meta["url"],
        ]
    else:
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
            audio_format,
            "--audio-quality",
            cfg.download.audio_quality,
            "-o",
            str(audio_path),
            *platform.cookie_args(cfg),
            meta["url"],
        ]

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RemoteError(f"yt-dlp 下载失败({r.returncode}):{r.stderr.strip()[:200]}")

    video_path: Path | None = None
    if keep_video:
        # 扫描 workdir 找 <id>.* 中非音频扩展名的文件作为视频
        candidates = [
            p
            for p in workdir.glob(f"{meta['video_id']}.*")
            if p.suffix.lstrip(".").lower() not in (audio_format.lower(), "part", "ytdl")
            and p.is_file()
        ]
        if candidates:
            # 取最大的那个（视频通常远大于其它中间产物）
            video_path = max(candidates, key=lambda p: p.stat().st_size)

    return audio_path, video_path
