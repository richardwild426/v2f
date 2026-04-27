import json
import subprocess
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
