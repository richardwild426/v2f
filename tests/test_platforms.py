
from vtf.config import Config
from vtf.platforms import REGISTRY, detect


def test_detect_bilibili_long_url():
    p = detect("https://www.bilibili.com/video/BV1xxx")
    assert p.name == "bilibili"


def test_detect_bilibili_short_url():
    p = detect("https://b23.tv/abcd")
    assert p.name == "bilibili"


def test_detect_youtube_long_url():
    p = detect("https://www.youtube.com/watch?v=xxx")
    assert p.name == "youtube"


def test_detect_youtube_short_url():
    p = detect("https://youtu.be/xxx")
    assert p.name == "youtube"


def test_detect_unknown_falls_back_to_generic():
    p = detect("https://twitter.com/user/status/123")
    assert p.name == "generic"


def test_bilibili_default_cookie_args():
    p = next(x for x in REGISTRY if x.name == "bilibili")
    args = p.cookie_args(Config())
    assert args == ["--cookies-from-browser", "chrome"]


def test_bilibili_cookies_file_overrides_browser(tmp_path):
    cfg = Config()
    f = tmp_path / "c.txt"
    f.write_text("# cookie", encoding="utf-8")
    cfg.platform.bilibili.cookies_file = str(f)
    p = next(x for x in REGISTRY if x.name == "bilibili")
    args = p.cookie_args(cfg)
    assert args == ["--cookies", str(f)]


def test_youtube_no_cookie_by_default():
    p = next(x for x in REGISTRY if x.name == "youtube")
    args = p.cookie_args(Config())
    assert args == []


def test_bilibili_normalize(raw_bilibili):
    p = next(x for x in REGISTRY if x.name == "bilibili")
    out = p.normalize_metadata(raw_bilibili)
    assert out["platform"] == "bilibili"
    assert out["video_id"] == "BV1xxx"
    assert out["title"] == "测试视频"
    assert out["author"] == "测试UP"
    assert out["upload_date"] == "2026-04-01 00:00"
    assert out["duration_str"] == "10:00"
    assert out["view"] == 12345
    assert out["favorite"] == 0
    assert out["share"] == 0
    assert out["reply"] == 0


def test_youtube_normalize_uses_comment_count(raw_youtube):
    p = next(x for x in REGISTRY if x.name == "youtube")
    out = p.normalize_metadata(raw_youtube)
    assert out["reply"] == 7
    assert out["duration_str"] == "2:05"
