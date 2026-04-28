import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from vtf.config import Config
from vtf.errors import RemoteError
from vtf.sinks.feishu import Feishu


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


def test_emit_passes_as_bot_to_lark_cli(tmp_path):
    cfg = _configured_cfg(tmp_path, identity="bot")
    result = {"meta": {"title": "Hello"}}
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "rec_xxx"}]}}
        ),
        stderr="",
    )
    with patch("vtf.sinks.feishu.shutil.which", return_value="/fake/lark-cli"), patch(
        "vtf.sinks.feishu.subprocess.run", return_value=fake
    ) as run_mock:
        outcome = Feishu().emit(result, cfg)

    cmd = run_mock.call_args.args[0]
    assert "--as" in cmd
    assert cmd[cmd.index("--as") + 1] == "bot"
    assert outcome.sink == "feishu"
    assert "rec_xxx" in outcome.reason


def test_emit_no_permission_error_includes_collaborator_hint(tmp_path):
    cfg = _configured_cfg(tmp_path, identity="bot")
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
    with patch("vtf.sinks.feishu.shutil.which", return_value="/fake/lark-cli"), patch(
        "vtf.sinks.feishu.subprocess.run", return_value=fake
    ):
        with pytest.raises(RemoteError) as exc:
            Feishu().emit({"meta": {"title": "x"}}, cfg)

    msg = str(exc.value)
    assert "99991672" in msg
    assert "协作者" in msg


def test_emit_passes_as_user_when_identity_user(tmp_path):
    cfg = _configured_cfg(tmp_path, identity="user")
    result = {"meta": {"title": "Hi"}}
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps({"ok": True, "data": {"records": [{"record_id": "r1"}]}}),
        stderr="",
    )
    with patch("vtf.sinks.feishu.shutil.which", return_value="/fake/lark-cli"), patch(
        "vtf.sinks.feishu.subprocess.run", return_value=fake
    ) as run_mock:
        Feishu().emit(result, cfg)

    cmd = run_mock.call_args.args[0]
    assert cmd[cmd.index("--as") + 1] == "user"


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
    video = tmp_path / "v.mp4"
    video.write_bytes(b"\x00" * 1024)
    result = {"meta": {"title": "Hi", "video_path": str(video)}}

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

    with patch("vtf.sinks.feishu.shutil.which", return_value="/fake/lark-cli"), patch(
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
    result = {"meta": {"title": "Hi", "video_path": str(tmp_path / "missing.mp4")}}

    create_resp = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "rec_yyy"}]}}
        ),
        stderr="",
    )

    with patch("vtf.sinks.feishu.shutil.which", return_value="/fake/lark-cli"), patch(
        "vtf.sinks.feishu.subprocess.run", side_effect=[create_resp]
    ) as run_mock:
        outcome = Feishu().emit(result, cfg)

    # 只调一次 batch-create，没调 upload-attachment
    assert len(run_mock.call_args_list) == 1
    assert "跳过" in outcome.reason
    assert "文件不存在" in outcome.reason


def test_attachment_skipped_when_oversize(tmp_path):
    cfg = _attachment_cfg(tmp_path)
    big = tmp_path / "big.mp4"
    big.touch()
    # 通过 stat 拦截绕过实际写 2GB
    create_resp = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "rec_zzz"}]}}
        ),
        stderr="",
    )
    result = {"meta": {"title": "Hi", "video_path": str(big)}}

    class FakeStat:
        st_size = 2 * 1024 * 1024 * 1024  # 2GB

    with patch("vtf.sinks.feishu.shutil.which", return_value="/fake/lark-cli"), patch(
        "vtf.sinks.feishu.subprocess.run", side_effect=[create_resp]
    ) as run_mock, patch.object(Path, "stat", return_value=FakeStat()):
        outcome = Feishu().emit(result, cfg)

    assert len(run_mock.call_args_list) == 1
    assert "跳过" in outcome.reason
    assert "1900MB" in outcome.reason


def test_attachment_skipped_when_source_empty(tmp_path):
    """meta.video_path 不存在时，附件字段直接被忽略，仅写 batch_create。"""
    cfg = _attachment_cfg(tmp_path)
    result = {"meta": {"title": "Hi"}}  # 没有 video_path
    create_resp = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": "rec_w"}]}}
        ),
        stderr="",
    )
    with patch("vtf.sinks.feishu.shutil.which", return_value="/fake/lark-cli"), patch(
        "vtf.sinks.feishu.subprocess.run", side_effect=[create_resp]
    ) as run_mock:
        outcome = Feishu().emit(result, cfg)

    assert len(run_mock.call_args_list) == 1
    assert "rec_w" in outcome.reason
    assert "附件" not in outcome.reason  # 没有 attachments 时不带附件段
