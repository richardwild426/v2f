import pytest

from vtf.sinks.schema import render_field, resolve_path

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
