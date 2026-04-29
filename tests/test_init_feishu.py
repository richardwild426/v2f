"""Tests for `vtf init feishu`：建表 / 同步字段 / config 回写。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from vtf.cli import main

# ----- 通用 fixtures -----------------------------------------------------------


@pytest.fixture
def schema_file(tmp_path: Path) -> Path:
    p = tmp_path / "schema.toml"
    p.write_text(
        '[[fields]]\nname = "对标素材链接"\ntype = "text"\nsource = "meta.url"\n\n'
        '[[fields]]\nname = "原始素材"\ntype = "attachment"\nsource = "meta.video_path"\n\n'
        '[[fields]]\nname = "标题"\ntype = "text"\nsource = "meta.title"\n',
        encoding="utf-8",
    )
    return p


def _ok(stdout: dict) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(stdout), stderr=""
    )


def _config_show_ok(app_id: str = "cli_test") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps({"appId": app_id, "users": ""}),
        stderr="",
    )


# ----- 测试：没 base_token，建 base + table -------------------------------------


def test_init_feishu_creates_base_and_table_with_all_fields(
    tmp_path: Path, schema_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 让 default_user_path 指向 tmp_path，避免污染真实 ~/.config
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    config_show = _config_show_ok()
    base_create = _ok(
        {
            "ok": True,
            "data": {
                "base": {
                    "token": "bascnNEW",
                    "url": "https://feishu.cn/base/bascnNEW",
                }
            },
        }
    )
    table_create = _ok(
        {"ok": True, "data": {"table": {"table_id": "tblNEW"}}}
    )

    with patch(
        "vtf.config.shutil.which", return_value="/fake/lark-cli"
    ), patch(
        "vtf.commands.init.subprocess.run",
        side_effect=[config_show, base_create, table_create],
    ) as run_mock:
        runner = CliRunner()
        result = runner.invoke(
            main, ["init", "feishu", "--schema", str(schema_file), "--name", "测试 base"]
        )

    assert result.exit_code == 0, result.output
    # 第二次调用是 +base-create
    base_args = run_mock.call_args_list[1].args[0]
    assert "+base-create" in base_args
    assert base_args[base_args.index("--name") + 1] == "测试 base"
    # 第三次调用是 +table-create，--fields 含全部 3 个字段
    table_args = run_mock.call_args_list[2].args[0]
    assert "+table-create" in table_args
    fields_payload = json.loads(table_args[table_args.index("--fields") + 1])
    assert [f["name"] for f in fields_payload] == ["对标素材链接", "原始素材", "标题"]
    assert {f["type"] for f in fields_payload} == {"text", "attachment"}
    # 输出包含关键信息
    assert "bascnNEW" in result.output
    assert "tblNEW" in result.output
    assert "协作者" in result.output  # 提示加协作者权限

    # 验证 config 被写入
    cfg_path = tmp_path / "xdg" / "vtf" / "config.toml"
    assert cfg_path.exists()
    content = cfg_path.read_text("utf-8")
    assert 'base_token = "bascnNEW"' in content
    assert 'table_id = "tblNEW"' in content
    assert 'sink = "feishu"' in content


def test_init_feishu_uses_default_packaged_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    config_show = _config_show_ok()
    base_create = _ok({"ok": True, "data": {"base": {"token": "bascnNEW"}}})
    table_create = _ok({"ok": True, "data": {"table": {"table_id": "tblNEW"}}})

    with (
        patch("vtf.config.shutil.which", return_value="/fake/lark-cli"),
        patch(
            "vtf.commands.init.subprocess.run",
            side_effect=[config_show, base_create, table_create],
        ) as run_mock,
    ):
        result = CliRunner().invoke(main, ["init", "feishu"])

    assert result.exit_code == 0, result.output
    table_args = run_mock.call_args_list[2].args[0]
    fields_payload = json.loads(table_args[table_args.index("--fields") + 1])
    field_names = [field["name"] for field in fields_payload]
    assert "对标素材链接" in field_names
    assert "封面链接" in field_names

    content = (tmp_path / "xdg" / "vtf" / "config.toml").read_text("utf-8")
    assert 'schema = "' in content
    assert "baokuan.toml" in content


def test_default_schema_documents_attachment_as_auto_created() -> None:
    schema_text = Path("vtf/assets/schemas/baokuan.toml").read_text("utf-8")
    assert "name = \"原始素材\"" in schema_text
    assert "type = \"attachment\"" in schema_text
    assert "一起自动创建这一列" in schema_text
    assert "手动加这一列" not in schema_text


def test_init_feishu_no_write_config_skips_patch(
    tmp_path: Path, schema_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    with patch(
        "vtf.config.shutil.which", return_value="/fake/lark-cli"
    ), patch(
        "vtf.commands.init.subprocess.run",
        side_effect=[
            _config_show_ok(),
            _ok({"ok": True, "data": {"base": {"token": "bascnX"}}}),
            _ok({"ok": True, "data": {"table": {"table_id": "tblX"}}}),
        ],
    ):
        result = CliRunner().invoke(
            main,
            [
                "init",
                "feishu",
                "--schema",
                str(schema_file),
                "--no-write-config",
            ],
        )

    assert result.exit_code == 0
    assert "请手动把以下三行加到" in result.output
    assert not (tmp_path / "xdg" / "vtf" / "config.toml").exists()


# ----- 测试：已有 base_token，同步缺字段 ---------------------------------------


def test_init_feishu_syncs_missing_fields_when_base_exists(
    tmp_path: Path, schema_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 准备一个含 base_token / table_id 的 config
    cfg_dir = tmp_path / "xdg" / "vtf"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.toml").write_text(
        f'[output]\nsink = "feishu"\n\n'
        f'[sink.feishu]\nbase_token = "bascnEXIST"\ntable_id = "tblEXIST"\n'
        f'schema = "{schema_file}"\nidentity = "bot"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    field_list = _ok(
        {
            "ok": True,
            "data": {
                "items": [
                    {"field_name": "对标素材链接", "type": "text"},
                    # 「原始素材」「标题」缺失
                ]
            },
        }
    )
    create_a = _ok({"ok": True, "data": {"field": {"field_id": "fldA"}}})
    create_b = _ok({"ok": True, "data": {"field": {"field_id": "fldB"}}})

    with patch(
        "vtf.config.shutil.which", return_value="/fake/lark-cli"
    ), patch(
        "vtf.commands.init.subprocess.run",
        side_effect=[_config_show_ok(), field_list, create_a, create_b],
    ) as run_mock:
        result = CliRunner().invoke(main, ["init", "feishu"])

    assert result.exit_code == 0, result.output
    calls = run_mock.call_args_list
    assert "+field-list" in calls[1].args[0]
    # 接下来两次是 +field-create
    create_args_a = calls[2].args[0]
    payload_a = json.loads(create_args_a[create_args_a.index("--json") + 1])
    assert payload_a == {"name": "原始素材", "type": "attachment"}
    create_args_b = calls[3].args[0]
    payload_b = json.loads(create_args_b[create_args_b.index("--json") + 1])
    assert payload_b == {"name": "标题", "type": "text"}
    assert "已补齐 2 个字段" in result.output


def test_init_feishu_sync_no_missing_fields(
    tmp_path: Path, schema_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_dir = tmp_path / "xdg" / "vtf"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.toml").write_text(
        f'[sink.feishu]\nbase_token = "bascnE"\ntable_id = "tblE"\nschema = "{schema_file}"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    field_list = _ok(
        {
            "ok": True,
            "data": {
                "items": [
                    {"field_name": "对标素材链接", "type": "text"},
                    {"field_name": "原始素材", "type": "attachment"},
                    {"field_name": "标题", "type": "text"},
                ]
            },
        }
    )

    with patch(
        "vtf.config.shutil.which", return_value="/fake/lark-cli"
    ), patch(
        "vtf.commands.init.subprocess.run",
        side_effect=[_config_show_ok(), field_list],
    ) as run_mock:
        result = CliRunner().invoke(main, ["init", "feishu"])

    assert result.exit_code == 0, result.output
    assert len(run_mock.call_args_list) == 2  # 仅 config show + field-list
    assert "无需补齐" in result.output


# ----- 测试：pre-flight 失败提示 -----------------------------------------------


def test_init_feishu_fails_when_lark_cli_not_installed(
    tmp_path: Path, schema_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    with patch("vtf.config.shutil.which", return_value=None), patch(
        "vtf.commands.init.subprocess.run"
    ) as run_mock:
        result = CliRunner().invoke(
            main, ["init", "feishu", "--schema", str(schema_file)]
        )
    # 应当 fail 且不调任何 lark-cli 子进程
    assert result.exit_code != 0
    assert run_mock.call_count == 0


def test_init_feishu_fails_when_app_not_bound(
    tmp_path: Path, schema_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    no_app = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps({"appId": ""}), stderr=""
    )
    with patch(
        "vtf.config.shutil.which", return_value="/fake/lark-cli"
    ), patch("vtf.commands.init.subprocess.run", side_effect=[no_app]) as run_mock:
        result = CliRunner().invoke(
            main, ["init", "feishu", "--schema", str(schema_file)]
        )
    # 应当 fail 且只调 config show 一次，不进入 base/table 创建
    assert result.exit_code != 0
    assert run_mock.call_count == 1
    assert "config" in run_mock.call_args_list[0].args[0]


# ----- 测试：--recreate 强制重建（即使已有 base_token） ------------------------


def test_init_feishu_recreate_forces_new_base(
    tmp_path: Path, schema_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_dir = tmp_path / "xdg" / "vtf"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.toml").write_text(
        f'[sink.feishu]\nbase_token = "bascnOLD"\ntable_id = "tblOLD"\nschema = "{schema_file}"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    base_create = _ok(
        {"ok": True, "data": {"base": {"token": "bascnNEW"}}}
    )
    table_create = _ok({"ok": True, "data": {"table": {"table_id": "tblNEW"}}})
    with patch(
        "vtf.config.shutil.which", return_value="/fake/lark-cli"
    ), patch(
        "vtf.commands.init.subprocess.run",
        side_effect=[_config_show_ok(), base_create, table_create],
    ) as run_mock:
        result = CliRunner().invoke(
            main, ["init", "feishu", "--recreate"]
        )

    assert result.exit_code == 0, result.output
    # 第二次调用是 +base-create 而不是 +field-list
    assert "+base-create" in run_mock.call_args_list[1].args[0]
    # 配置已被覆盖
    new_cfg = (cfg_dir / "config.toml").read_text("utf-8")
    assert 'base_token = "bascnNEW"' in new_cfg
    assert "bascnOLD" not in new_cfg
