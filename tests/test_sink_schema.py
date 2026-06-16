import pytest

from vtf.sinks.schema import (
    is_required_field,
    load_storyboard_schema,
    missing_required_fields,
    render_field,
    required_analysis_fields,
    resolve_path,
    storyboard_required_analysis_field,
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


def test_load_storyboard_schema(tmp_path):
    schema = tmp_path / "s.toml"
    schema.write_text(
        '[[fields]]\nname = "标题"\ntype = "text"\nsource = "meta.title"\n\n'
        '[storyboard]\n'
        'table_name = "分镜明细"\n'
        'rows_source = "analyses.breakdown.shots"\n'
        'link_field = "所属视频"\n'
        'master_link_field = "脚本拆解"\n\n'
        '[[storyboard.fields]]\n'
        'name = "镜头"\n'
        'type = "number"\n'
        'source = "shot"\n',
        encoding="utf-8",
    )

    storyboard = load_storyboard_schema(schema)

    assert storyboard is not None
    assert storyboard.table_name == "分镜明细"
    assert storyboard.rows_source == "analyses.breakdown.shots"
    assert storyboard.link_field == "所属视频"
    assert storyboard.master_link_field == "脚本拆解"
    assert storyboard.fields == [{"name": "镜头", "type": "number", "source": "shot"}]


def test_storyboard_required_analysis_field_for_kind(tmp_path):
    schema = tmp_path / "s.toml"
    schema.write_text(
        '[[fields]]\nname = "标题"\ntype = "text"\nsource = "meta.title"\n\n'
        '[storyboard]\n'
        'rows_source = "analyses.breakdown.shots"\n\n'
        '[[storyboard.fields]]\n'
        'name = "镜头"\n'
        'source = "shot"\n',
        encoding="utf-8",
    )
    storyboard = load_storyboard_schema(schema)

    required = storyboard_required_analysis_field(storyboard, "breakdown")

    assert required is not None
    assert required.name == "分镜明细"
    assert required.source == "analyses.breakdown.shots"
    assert required.result_path == "shots"
    assert storyboard_required_analysis_field(storyboard, "summary") is None
