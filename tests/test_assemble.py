import pytest

from vtf.errors import UserError
from vtf.pipeline.assemble import assemble


def test_assemble_combines_inputs():
    meta = {"title": "T", "url": "u", "thumbnail": "https://example.com/cover.jpg"}
    lines = ["a", "b"]
    analyses = [
        {"kind": "summary", "result": {"text": "S", "points": ["p"], "tags": ["#x"]}},
        {"kind": "breakdown", "result": {"text": "B"}},
        {"kind": "rewrite", "result": {"text": "R"}},
    ]
    out = assemble(meta=meta, lines=lines, analyses=analyses)
    assert out["meta"] == meta
    assert out["lines"] == lines
    assert out["analyses"]["summary"]["text"] == "S"
    assert out["analyses"]["breakdown"]["text"] == "B"
    assert out["analyses"]["rewrite"]["text"] == "R"


def test_assemble_rejects_unfilled_result():
    meta = {"title": "T", "thumbnail": "https://example.com/cover.jpg"}
    lines = ["a"]
    analyses = [
        {"kind": "summary", "result": None},
        {"kind": "breakdown", "result": {"text": "B"}},
        {"kind": "rewrite", "result": {"text": "R"}},
    ]
    with pytest.raises(UserError, match="result not filled"):
        assemble(meta=meta, lines=lines, analyses=analyses)


def test_assemble_rejects_missing_kinds():
    meta = {"title": "X", "thumbnail": "https://example.com/cover.jpg"}
    lines = ["l"]
    analyses = [
        {"kind": "rewrite", "result": {"text": "R"}},
    ]
    with pytest.raises(UserError, match="缺少必填分析"):
        assemble(meta=meta, lines=lines, analyses=analyses)


def test_assemble_rejects_missing_thumbnail():
    analyses = [
        {"kind": "summary", "result": {"text": "S"}},
        {"kind": "breakdown", "result": {"text": "B"}},
        {"kind": "rewrite", "result": {"text": "R"}},
    ]
    with pytest.raises(UserError, match="thumbnail"):
        assemble(meta={"title": "X"}, lines=["l"], analyses=analyses)
