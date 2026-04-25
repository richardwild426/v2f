import json
from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture()
def raw_bilibili():
    return json.loads((FIX / "raw_yt_dlp_bilibili.json").read_text("utf-8"))


@pytest.fixture()
def raw_youtube():
    return json.loads((FIX / "raw_yt_dlp_youtube.json").read_text("utf-8"))
