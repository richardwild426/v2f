from vtf.sinks.markdown import Markdown


def test_markdown_available():
    m = Markdown()
    ok, reason = m.available({})
    assert ok
    assert reason == ""


def test_markdown_render():
    m = Markdown()
    thumbnail = "https://example.com/cover.jpg"
    result = {
        "meta": {
            "title": "T",
            "author": "A",
            "platform": "bilibili",
            "url": "u",
            "thumbnail": thumbnail,
        },
        "lines": ["a", "b"],
        "analyses": {"summary": {"text": "S"}},
    }
    out = m.emit(result, {})
    assert f"![封面]({thumbnail})<br>{thumbnail}" in out.reason
    assert not out.degraded
    assert "T" in out.reason
    assert "a" in out.reason
    assert "S" in out.reason


def test_markdown_degrades_missing_thumbnail_defensively():
    result = {
        "meta": {"title": "T"},
        "lines": [],
        "analyses": {},
    }
    out = Markdown().emit(result, {})
    assert out.degraded
    assert "封面 URL 缺失" in out.reason
