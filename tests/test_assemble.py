import pytest

from vtf.errors import UserError
from vtf.pipeline.assemble import assemble


def test_assemble_combines_inputs():
    meta = {"title": "T", "url": "u"}
    lines = ["a", "b"]
    analyses = [
        {"kind": "summary", "result": {"text": "S", "points": ["p"], "tags": ["#x"]}},
        {"kind": "breakdown", "result": {"text": "B"}},
    ]
    out = assemble(meta=meta, lines=lines, analyses=analyses)
    assert out["meta"] == meta
    assert out["lines"] == lines
    assert out["analyses"]["summary"]["text"] == "S"
    assert out["analyses"]["breakdown"]["text"] == "B"
    assert "rewrite" not in out["analyses"]


def test_assemble_rejects_unfilled_result():
    meta = {"title": "T"}
    lines = ["a"]
    analyses = [{"kind": "summary", "result": None}]
    with pytest.raises(UserError, match="result not filled"):
        assemble(meta=meta, lines=lines, analyses=analyses)


def test_assemble_skips_missing_kinds():
    meta = {"title": "X"}
    lines = ["l"]
    analyses = [{"kind": "rewrite", "result": {"text": "R"}}]
    out = assemble(meta=meta, lines=lines, analyses=analyses)
    assert out["analyses"]["rewrite"]["text"] == "R"
    assert "summary" not in out["analyses"]
    assert "breakdown" not in out["analyses"]
