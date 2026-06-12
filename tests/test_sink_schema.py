import pytest

from vtf.sinks.schema import (
    is_required_field,
    missing_required_fields,
    render_field,
    required_analysis_fields,
    resolve_path,
)

RESULT = {
    "meta": {"url": "https://x", "title": "T"},
    "lines": ["a", "b"],
    "analyses": {
        "summary": {"text": "S", "tags": ["#x", "#y"]},
        "rewrite": {"text": "R1\nR2"},
    },
}


def test_resolve_basic():
    assert resolve_path(RESULT, "meta.url") == "https://x"
    assert resolve_path(RESULT, "analyses.summary.text") == "S"


def test_resolve_missing_returns_none():
    assert resolve_path(RESULT, "analyses.breakdown.text") is None
    assert resolve_path(RESULT, "x.y.z") is None


def test_render_field_joined():
    assert render_field(RESULT, "lines | joined") == "a\nb"


def test_render_field_tags_hashtag():
    assert render_field(RESULT, "analyses.summary.tags | tags_hashtag") == "#x #y"


def test_render_field_stats_compact():
    r = {"meta": {"view": 100, "like": 5, "favorite": 0, "share": 0, "reply": 1}}
    assert (
        render_field(r, "meta | stats_compact")
        == "播放100 | 点赞5 | 收藏0 | 分享0 | 评论1"
    )


def test_render_field_unknown_transformer_raises():
    from vtf.errors import UserError

    with pytest.raises(UserError, match="transformer"):
        render_field(RESULT, "lines | nonsense")


def test_required_field_inference():
    assert is_required_field(
        {"name": "摘要", "type": "text", "source": "analyses.summary.text"}
    )
    assert not is_required_field(
        {"name": "播放数", "type": "text", "source": "meta.view"}
    )
    assert not is_required_field(
        {"name": "原始素材", "type": "attachment", "source": "analyses.rewrite.text"}
    )


def test_missing_required_fields_reports_name_and_source():
    fields = [
        {"name": "摘要", "type": "text", "source": "analyses.summary.text"},
        {"name": "亮点", "type": "text", "source": "analyses.breakdown.pros | joined"},
        {"name": "播放数", "type": "text", "source": "meta.view"},
    ]

    missing = missing_required_fields(RESULT, fields)

    assert [(item.name, item.source) for item in missing] == [
        ("亮点", "analyses.breakdown.pros | joined")
    ]


def test_required_analysis_fields_for_kind():
    fields = [
        {"name": "摘要", "type": "text", "source": "analyses.summary.text"},
        {"name": "标签", "type": "text", "source": "analyses.summary.tags | tags_hashtag"},
        {"name": "二创改写", "type": "text", "source": "analyses.rewrite.text"},
        {"name": "标题", "type": "text", "source": "meta.title"},
    ]

    required = required_analysis_fields(fields, "summary")

    assert [(item.name, item.result_path) for item in required] == [
        ("摘要", "text"),
        ("标签", "tags"),
    ]
