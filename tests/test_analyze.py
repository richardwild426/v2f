from vtf.config import Config
from vtf.pipeline.analyze import analyze


def test_analyze_summary_emits_prompt_and_context():
    cfg = Config()
    out = analyze(
        kind="summary",
        meta={"title": "T", "author": "A", "platform": "bilibili"},
        lines=["第一行", "第二行"],
        cfg=cfg,
    )
    assert out["kind"] == "summary"
    assert "T" in out["prompt"]
    assert "第一行" in out["prompt"]
    assert out["context"]["lines_count"] == 2
    assert out["result"] is None
    assert "schema_hint" in out


def test_analyze_uses_override_prompt(tmp_path):
    p = tmp_path / "my.md"
    p.write_text("MY {{ title }} END", encoding="utf-8")
    cfg = Config()
    cfg.analyze.prompts.summary = str(p)
    out = analyze(
        kind="summary",
        meta={"title": "Z", "author": "", "platform": ""},
        lines=[],
        cfg=cfg,
    )
    assert "MY Z END" in out["prompt"]


def test_analyze_unknown_kind_raises():
    import pytest

    from vtf.errors import UserError

    with pytest.raises(UserError):
        analyze(
            kind="bogus",
            meta={"title": "", "author": "", "platform": ""},
            lines=[],
            cfg=Config(),
        )
