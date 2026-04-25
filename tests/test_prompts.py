from vtf.prompts import load_prompt, render_prompt


def test_load_builtin_summary():
    text = load_prompt("summary", override_path="")
    assert "{{ title }}" in text
    assert "{{ lines }}" in text


def test_load_override(tmp_path):
    p = tmp_path / "my.md"
    p.write_text("custom {{ title }}", encoding="utf-8")
    assert load_prompt("summary", override_path=str(p)) == "custom {{ title }}"


def test_render_substitutes():
    out = render_prompt("hello {{ title }} by {{ author }}", {"title": "T", "author": "A"})
    assert out == "hello T by A"


def test_render_lines_joined():
    out = render_prompt("L:\n{{ lines }}", {"lines": ["a", "b", "c"]})
    assert out == "L:\na\nb\nc"
