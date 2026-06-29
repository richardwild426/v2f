import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from vtf.config import Config
from vtf.errors import RemoteError, UserError
from vtf.sinks.feishu import Feishu


def _meta(**extra):
    return {"title": "Hi", "thumbnail": "https://example.com/cover.jpg", **extra}


def _configured_cfg(tmp_path, identity: str = "bot") -> Config:
    schema = tmp_path / "s.toml"
    schema.write_text(
        '[[fields]]\nname = "标题"\ntype = "text"\nsource = "meta.title"\n',
        encoding="utf-8",
    )
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "tbl"
    cfg.sink.feishu.schema = str(schema)
    cfg.sink.feishu.identity = identity
    return cfg


def _storyboard_cfg(tmp_path) -> Config:
    schema = tmp_path / "storyboard.toml"
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
        'source = "shot"\n\n'
        '[[storyboard.fields]]\n'
        'name = "素材"\n'
        'type = "text"\n'
        'source = "materials | joined"\n',
        encoding="utf-8",
    )
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "tblMain"
    cfg.sink.feishu.storyboard_table_id = "tblShots"
    cfg.sink.feishu.schema = str(schema)
    cfg.sink.feishu.identity = "bot"
    cfg.sink.feishu.lark_cli = "/fake/lark-cli"
    return cfg


def test_feishu_not_available_without_config():
    f = Feishu()
    cfg = Config()
    ok, reason = f.available(cfg)
    assert not ok
    assert "base_token" in reason


def test_feishu_available_when_configured():
    f = Feishu()
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "tbl"
    cfg.sink.feishu.schema = "schema.toml"
    ok, reason = f.available(cfg)
    assert ok


def test_feishu_rejects_invalid_identity():
    f = Feishu()
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "tbl"
    cfg.sink.feishu.schema = "schema.toml"
    cfg.sink.feishu.identity = "anonymous"
    ok, reason = f.available(cfg)
    assert not ok
    assert "identity" in reason


def test_feishu_available_respects_lark_cli_override():
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "tbl"
    cfg.sink.feishu.schema = "schema.toml"
    cfg.sink.feishu.lark_cli = "/custom/lark-cli"
    f = Feishu()
    ok, reason = f.available(cfg)
    assert ok


def test_emit_passes_as_bot_to_lark_cli(tmp_path):
    cfg = _configured_cfg(tmp_path, identity="bot")
    cfg.sink.feishu.lark_cli = "/fake/lark-cli"
    result = {"meta": _meta(title="Hello")}
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "rec_xxx"}]}}
        ),
        stderr="",
    )
    with patch(
        "vtf.sinks.feishu.subprocess.run", return_value=fake
    ) as run_mock:
        outcome = Feishu().emit(result, cfg)

    cmd = run_mock.call_args.args[0]
    assert "--as" in cmd
    assert cmd[cmd.index("--as") + 1] == "bot"
    assert outcome.sink == "feishu"
    assert "rec_xxx" in outcome.reason


def test_emit_rejects_missing_required_analysis_field_before_remote_call(tmp_path):
    schema = tmp_path / "s.toml"
    schema.write_text(
        '[[fields]]\nname = "开场钩子"\ntype = "text"\nsource = "analyses.breakdown.hook"\n',
        encoding="utf-8",
    )
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "tbl"
    cfg.sink.feishu.schema = str(schema)
    cfg.sink.feishu.lark_cli = "/fake/lark-cli"

    with (
        patch("vtf.sinks.feishu.subprocess.run") as run_mock,
        pytest.raises(UserError) as exc,
    ):
        Feishu().emit({"meta": _meta(), "analyses": {"breakdown": {}}}, cfg)

    assert not run_mock.called
    msg = str(exc.value)
    assert "开场钩子" in msg
    assert "analyses.breakdown.hook" in msg


def test_emit_allows_missing_optional_metadata_field(tmp_path):
    """meta.* 默认可空：缺失的 meta 字段不 block 写入，照常写空值。"""
    schema = tmp_path / "s.toml"
    schema.write_text(
        '[[fields]]\nname = "分享数"\ntype = "text"\nsource = "meta.share"\n',
        encoding="utf-8",
    )
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "tbl"
    cfg.sink.feishu.schema = str(schema)
    cfg.sink.feishu.lark_cli = "/fake/lark-cli"
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "rec_meta"}]}}
        ),
        stderr="",
    )

    with patch("vtf.sinks.feishu.subprocess.run", return_value=fake) as run_mock:
        outcome = Feishu().emit({"meta": _meta()}, cfg)

    # 缺失的 meta.share 不报错，写入照常进行，对应单元格为空字符串
    cmd = run_mock.call_args.args[0]
    payload = json.loads(cmd[cmd.index("--json") + 1])
    assert payload == {"fields": ["分享数"], "rows": [[""]]}
    assert "rec_meta" in outcome.reason


def test_emit_writes_storyboard_rows_linked_to_main_record(tmp_path):
    cfg = _storyboard_cfg(tmp_path)
    result = {
        "meta": _meta(title="Video A"),
        "analyses": {
            "breakdown": {
                "shots": [
                    {"shot": 1, "materials": ["cover", "screen"]},
                    {"shot": 2, "materials": ["demo"]},
                ]
            }
        },
    }
    main_resp = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "recMain"}]}}
        ),
        stderr="",
    )
    storyboard_resp = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "recShot"}]}}
        ),
        stderr="",
    )

    with patch(
        "vtf.sinks.feishu.subprocess.run",
        side_effect=[main_resp, storyboard_resp],
    ) as run_mock:
        outcome = Feishu().emit(result, cfg)

    main_cmd = run_mock.call_args_list[0].args[0]
    main_payload = json.loads(main_cmd[main_cmd.index("--json") + 1])
    assert main_cmd[main_cmd.index("--table-id") + 1] == "tblMain"
    assert main_payload == {"fields": ["标题"], "rows": [["Video A"]]}

    storyboard_cmd = run_mock.call_args_list[1].args[0]
    storyboard_payload = json.loads(
        storyboard_cmd[storyboard_cmd.index("--json") + 1]
    )
    assert storyboard_cmd[storyboard_cmd.index("--table-id") + 1] == "tblShots"
    assert storyboard_payload == {
        "fields": ["所属视频", "镜头", "素材"],
        "rows": [
            [[{"id": "recMain"}], 1, "cover\nscreen"],
            [[{"id": "recMain"}], 2, "demo"],
        ],
    }
    assert "recMain" in outcome.reason


def test_emit_rejects_missing_storyboard_row_field_before_remote_call(tmp_path):
    """子表某行缺必填子字段时 fail loud，报行号+字段，不再静默写空。"""
    cfg = _storyboard_cfg(tmp_path)
    result = {
        "meta": _meta(title="Video A"),
        "analyses": {
            "breakdown": {
                "shots": [
                    {"shot": 1, "materials": ["cover"]},
                    {"shot": 2},  # 缺 materials
                ]
            }
        },
    }

    with (
        patch("vtf.sinks.feishu.subprocess.run") as run_mock,
        pytest.raises(UserError) as exc,
    ):
        Feishu().emit(result, cfg)

    assert not run_mock.called
    msg = str(exc.value)
    assert "第2行" in msg
    assert "素材" in msg


def test_emit_rejects_missing_storyboard_table_id(tmp_path):
    cfg = _storyboard_cfg(tmp_path)
    cfg.sink.feishu.storyboard_table_id = ""

    with (
        patch("vtf.sinks.feishu.subprocess.run") as run_mock,
        pytest.raises(UserError, match="storyboard_table_id"),
    ):
        Feishu().emit(
            {
                "meta": _meta(),
                "analyses": {"breakdown": {"shots": [{"shot": 1}]}},
            },
            cfg,
        )

    assert not run_mock.called


def test_emit_rejects_empty_storyboard_rows_before_remote_call(tmp_path):
    cfg = _storyboard_cfg(tmp_path)

    with (
        patch("vtf.sinks.feishu.subprocess.run") as run_mock,
        pytest.raises(UserError) as exc,
    ):
        Feishu().emit(
            {"meta": _meta(), "analyses": {"breakdown": {"shots": []}}},
            cfg,
        )

    assert not run_mock.called
    assert "分镜明细" in str(exc.value)
    assert "analyses.breakdown.shots" in str(exc.value)


def test_emit_no_permission_error_includes_collaborator_hint(tmp_path):
    cfg = _configured_cfg(tmp_path, identity="bot")
    cfg.sink.feishu.lark_cli = "/fake/lark-cli"
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {
                "ok": False,
                "error": {"code": 99991672, "message": "NoPermission"},
            }
        ),
        stderr="",
    )
    with (
        patch("vtf.sinks.feishu.subprocess.run", return_value=fake),
        pytest.raises(RemoteError) as exc,
    ):
        Feishu().emit({"meta": _meta(title="x")}, cfg)

    msg = str(exc.value)
    assert "99991672" in msg
    assert "协作者" in msg


def test_emit_passes_as_user_when_identity_user(tmp_path):
    cfg = _configured_cfg(tmp_path, identity="user")
    cfg.sink.feishu.lark_cli = "/fake/lark-cli"
    result = {"meta": _meta()}
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps({"ok": True, "data": {"records": [{"record_id": "r1"}]}}),
        stderr="",
    )
    with patch(
        "vtf.sinks.feishu.subprocess.run", return_value=fake
    ) as run_mock:
        Feishu().emit(result, cfg)

    cmd = run_mock.call_args.args[0]
    assert cmd[cmd.index("--as") + 1] == "user"


def test_emit_rejects_missing_thumbnail(tmp_path):
    cfg = _configured_cfg(tmp_path)
    cfg.sink.feishu.lark_cli = "/fake/lark-cli"
    with pytest.raises(UserError, match="thumbnail"):
        Feishu().emit({"meta": {"title": "Hi"}}, cfg)


def _attachment_cfg(tmp_path) -> Config:
    schema = tmp_path / "s.toml"
    schema.write_text(
        '[[fields]]\nname = "标题"\ntype = "text"\nsource = "meta.title"\n\n'
        '[[fields]]\nname = "原始素材"\ntype = "attachment"\nsource = "meta.video_path"\n',
        encoding="utf-8",
    )
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "tbl"
    cfg.sink.feishu.schema = str(schema)
    cfg.sink.feishu.identity = "bot"
    return cfg


def test_attachment_field_excluded_from_batch_create_and_uploaded(tmp_path):
    cfg = _attachment_cfg(tmp_path)
    cfg.sink.feishu.lark_cli = "/fake/lark-cli"
    video = tmp_path / "v.mp4"
    video.write_bytes(b"\x00" * 1024)
    result = {"meta": _meta(video_path=str(video))}

    create_resp = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "rec_xxx"}]}}
        ),
        stderr="",
    )
    upload_resp = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps({"ok": True}), stderr=""
    )

    with patch(
        "vtf.sinks.feishu.subprocess.run", side_effect=[create_resp, upload_resp]
    ) as run_mock:
        outcome = Feishu().emit(result, cfg)

    create_cmd = run_mock.call_args_list[0].args[0]
    create_payload_idx = create_cmd.index("--json") + 1
    payload = json.loads(create_cmd[create_payload_idx])
    assert "原始素材" not in payload["fields"]
    assert "标题" in payload["fields"]

    upload_cmd = run_mock.call_args_list[1].args[0]
    assert "+record-upload-attachment" in upload_cmd
    assert upload_cmd[upload_cmd.index("--record-id") + 1] == "rec_xxx"
    assert upload_cmd[upload_cmd.index("--field-id") + 1] == "原始素材"
    assert upload_cmd[upload_cmd.index("--file") + 1] == str(video)
    assert "已上传" in outcome.reason


def test_attachment_skipped_when_file_missing(tmp_path):
    cfg = _attachment_cfg(tmp_path)
    cfg.sink.feishu.lark_cli = "/fake/lark-cli"
    result = {"meta": _meta(video_path=str(tmp_path / "missing.mp4"))}

    create_resp = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "rec_yyy"}]}}
        ),
        stderr="",
    )

    with patch(
        "vtf.sinks.feishu.subprocess.run", side_effect=[create_resp]
    ) as run_mock:
        outcome = Feishu().emit(result, cfg)

    assert len(run_mock.call_args_list) == 1
    assert "跳过" in outcome.reason
    assert "文件不存在" in outcome.reason


def test_attachment_skipped_when_oversize(tmp_path):
    cfg = _attachment_cfg(tmp_path)
    cfg.sink.feishu.lark_cli = "/fake/lark-cli"
    big = tmp_path / "big.mp4"
    big.touch()
    create_resp = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "rec_zzz"}]}}
        ),
        stderr="",
    )
    result = {"meta": _meta(video_path=str(big))}

    class FakeStat:
        st_size = 2 * 1024 * 1024 * 1024  # 2GB

    with (
        patch(
            "vtf.sinks.feishu.subprocess.run", side_effect=[create_resp]
        ) as run_mock,
        patch.object(Path, "stat", return_value=FakeStat()),
    ):
        outcome = Feishu().emit(result, cfg)

    assert len(run_mock.call_args_list) == 1
    assert "跳过" in outcome.reason
    assert "1900MB" in outcome.reason


def test_attachment_skipped_when_source_empty(tmp_path):
    """meta.video_path 不存在时，附件字段不参与必填校验，仅写 batch_create。"""
    cfg = _attachment_cfg(tmp_path)
    cfg.sink.feishu.lark_cli = "/fake/lark-cli"
    result = {"meta": _meta()}
    create_resp = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "rec_w"}]}}
        ),
        stderr="",
    )
    with patch(
        "vtf.sinks.feishu.subprocess.run", side_effect=[create_resp]
    ) as run_mock:
        outcome = Feishu().emit(result, cfg)

    # 附件源缺失不报错；只发一次 batch_create，不发 upload-attachment
    assert len(run_mock.call_args_list) == 1
    create_cmd = run_mock.call_args_list[0].args[0]
    payload = json.loads(create_cmd[create_cmd.index("--json") + 1])
    assert "原始素材" not in payload["fields"]
    assert "rec_w" in outcome.reason
