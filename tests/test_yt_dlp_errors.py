import subprocess
from unittest.mock import patch

import pytest

from vtf.config import Config
from vtf.errors import RemoteError
from vtf.pipeline.download import download
from vtf.pipeline.fetch import fetch


def _http_412() -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="ERROR: [BiliBili] BV1: HTTP Error 412: Precondition Failed",
    )


def test_fetch_bilibili_412_includes_cookie_hint():
    with (
        patch("vtf.pipeline.fetch.shutil.which", return_value="/fake/yt-dlp"),
        patch("vtf.pipeline.fetch.subprocess.run", return_value=_http_412()),
        pytest.raises(RemoteError) as exc,
    ):
        fetch(url="https://www.bilibili.com/video/BV1xxx", cfg=Config())

    msg = str(exc.value)
    assert "HTTP 412" in msg
    assert "Cookie" in msg
    assert "cookies_from_browser" in msg
    assert "cookies_file" in msg


def test_download_bilibili_412_includes_cookie_hint(tmp_path):
    meta = {"video_id": "BV1xxx", "url": "https://www.bilibili.com/video/BV1xxx"}
    with (
        patch("vtf.pipeline.download.shutil.which", return_value="/fake/yt-dlp"),
        patch("vtf.pipeline.download.subprocess.run", return_value=_http_412()),
        pytest.raises(RemoteError) as exc,
    ):
        download(meta=meta, cfg=Config(), workdir=tmp_path)

    assert "B站返回 HTTP 412" in str(exc.value)


def test_youtube_error_does_not_get_bilibili_cookie_hint(tmp_path):
    meta = {"video_id": "yt1", "url": "https://youtu.be/xxx"}
    proc = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="ERROR: HTTP Error 403: Forbidden",
    )
    with (
        patch("vtf.pipeline.download.shutil.which", return_value="/fake/yt-dlp"),
        patch("vtf.pipeline.download.subprocess.run", return_value=proc),
        pytest.raises(RemoteError) as exc,
    ):
        download(meta=meta, cfg=Config(), workdir=tmp_path)

    msg = str(exc.value)
    assert "403" in msg
    assert "B站返回 HTTP 412" not in msg
