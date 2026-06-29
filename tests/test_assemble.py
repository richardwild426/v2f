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


def _full_analyses(breakdown_result):
    return [
        {"kind": "summary", "result": {"text": "S"}},
        {"kind": "breakdown", "result": breakdown_result},
        {"kind": "rewrite", "result": {"text": "R"}},
    ]


def test_assemble_rejects_incomplete_result_by_contract():
    """带 required_result_fields 时，残缺 result 在 assemble 阶段即报错。"""
    meta = {"title": "T", "thumbnail": "https://example.com/cover.jpg"}
    analyses = [
        {
            "kind": "summary",
            "required_result_fields": [
                {"field": "摘要", "source": "analyses.summary.text", "result_path": "text"}
            ],
            "result": {"text": None},  # 残缺：text 为 null
        },
        {"kind": "breakdown", "result": {"text": "B"}},
        {"kind": "rewrite", "result": {"text": "R"}},
    ]
    with pytest.raises(UserError, match="summary result 缺少下游必填字段"):
        assemble(meta=meta, lines=["l"], analyses=analyses)


def test_assemble_rejects_missing_storyboard_row_field_by_contract():
    """带 row_fields 契约时，分镜行缺必填子字段在 assemble 阶段即报错。"""
    meta = {"title": "T", "thumbnail": "https://example.com/cover.jpg"}
    analyses = [
        {"kind": "summary", "result": {"text": "S"}},
        {
            "kind": "breakdown",
            "required_result_fields": [
                {
                    "field": "分镜明细",
                    "source": "analyses.breakdown.shots",
                    "result_path": "shots",
                    "row_fields": [
                        {"field": "镜头", "result_path": "shot", "required": True},
                        {"field": "文案", "result_path": "script", "required": True},
                    ],
                }
            ],
            "result": {"shots": [{"shot": 1, "script": "ok"}, {"shot": 2}]},
        },
        {"kind": "rewrite", "result": {"text": "R"}},
    ]
    with pytest.raises(UserError, match=r"shots\[2\].script"):
        assemble(meta=meta, lines=["l"], analyses=analyses)


def test_assemble_skips_contract_check_when_no_required_fields():
    """无 required_result_fields（markdown sink）时不校验子字段，向后兼容。"""
    meta = {"title": "T", "thumbnail": "https://example.com/cover.jpg"}
    # breakdown result 仅含 text，缺 hook 等，但无契约 → 放行
    out = assemble(meta=meta, lines=["l"], analyses=_full_analyses({"text": "B"}))
    assert out["analyses"]["breakdown"] == {"text": "B"}


def test_assemble_rejects_missing_thumbnail():
    analyses = [
        {"kind": "summary", "result": {"text": "S"}},
        {"kind": "breakdown", "result": {"text": "B"}},
        {"kind": "rewrite", "result": {"text": "R"}},
    ]
    with pytest.raises(UserError, match="thumbnail"):
        assemble(meta={"title": "X"}, lines=["l"], analyses=analyses)
