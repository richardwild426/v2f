from vtf.sinks.markdown import Markdown


def test_markdown_available():
    m = Markdown()
    ok, reason = m.available({})
    assert ok
    assert reason == ""


def test_markdown_render():
    m = Markdown()
    result = {
        "meta": {"title": "T", "author": "A", "platform": "bilibili", "url": "u"},
        "lines": ["a", "b"],
        "analyses": {"summary": {"text": "S"}},
    }
    out = m.emit(result, {})
    assert "T" in out.reason
    assert "a" in out.reason
    assert "S" in out.reason
