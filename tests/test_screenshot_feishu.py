"""截图飞书集成测试"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vtf.config import Config
from vtf.errors import UserError
from vtf.sinks.feishu import Feishu, _ScreenshotFeishuConfig


def _screenshot_schema(tmp_path: Path) -> Path:
    schema = tmp_path / "screenshot.toml"
    schema.write_text(
        '[[fields]]\n'
        'name = "视频ID"\n'
        'type = "text"\n'
        'source = "meta.video_id"\n\n'
        '[[fields]]\n'
        'name = "时间点(可读)"\n'
        'type = "text"\n'
        'source = "screenshots.timestamp_str"\n\n'
        '[[fields]]\n'
        'name = "字幕文本"\n'
        'type = "text"\n'
        'source = "screenshots.subtitle_text"\n\n'
        '[[fields]]\n'
        'name = "截图描述"\n'
        'type = "text"\n'
        'source = "screenshots.description"\n\n'
        '[[fields]]\n'
        'name = "截图文件"\n'
        'type = "attachment"\n'
        'source = "screenshots.image_path"\n',
        encoding="utf-8",
    )
    return schema


def _screenshot_cfg(tmp_path: Path) -> Config:
    schema = _screenshot_schema(tmp_path)
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "main_tbl"
    cfg.sink.feishu.schema = "assets/schemas/baokuan.toml"
    cfg.sink.feishu.screenshot_table_id = "screenshot_tbl"
    cfg.sink.feishu.screenshot_schema = str(schema)
    cfg.sink.feishu.identity = "bot"
    return cfg


def _fake_create_resp(record_id: str = "rec_001") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {"ok": True, "data": {"records": [{"record_id": record_id}]}}
        ),
        stderr="",
    )


def _fake_upload_resp() -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps({"ok": True}), stderr=""
    )


class TestScreenshotFeishuConfig:
    """_ScreenshotFeishuConfig 适配器测试"""

    def test_basic_attrs(self):
        c = _ScreenshotFeishuConfig("tok", "tbl", "bot")
        assert c.base_token == "tok"
        assert c.table_id == "tbl"
        assert c.identity == "bot"


class TestEmitDetectsScreenshots:
    """emit() 方法截图列表检测测试"""

    def test_emit_routes_to_screenshots_when_configured(self, tmp_path):
        """配置了 screenshot_table_id 时，emit 自动走 emit_screenshots"""
        cfg = _screenshot_cfg(tmp_path)
        cfg.sink.feishu.lark_cli = "/fake/lark-cli"

        img = tmp_path / "test.jpg"
        img.write_bytes(b"\x00" * 100)

        result = {
            "meta": {
                "title": "测试视频",
                "video_id": "bv_123",
                "thumbnail": "https://example.com/cover.jpg",
                "screenshots": [
                    {
                        "timestamp_str": "01:23",
                        "subtitle_text": "字幕内容",
                        "description": "AI 描述",
                        "image_path": str(img),
                        "phash": "abc123",
                    }
                ],
            }
        }

        with patch.object(
            Feishu, "emit_screenshots", return_value=MagicMock(reason="ok")
        ) as mock_es:
            Feishu().emit(result, cfg)

        mock_es.assert_called_once()
        assert mock_es.call_args.args[0] == result["meta"]["screenshots"]

    def test_emit_normal_when_no_screenshot_table(self, tmp_path):
        """未配置 screenshot_table_id 时，走正常 emit 路径"""
        schema = tmp_path / "s.toml"
        schema.write_text(
            '[[fields]]\nname = "标题"\ntype = "text"\nsource = "meta.title"\n',
            encoding="utf-8",
        )
        cfg = Config()
        cfg.sink.feishu.base_token = "tok"
        cfg.sink.feishu.table_id = "tbl"
        cfg.sink.feishu.schema = str(schema)
        cfg.sink.feishu.screenshot_table_id = ""  # 未配置
        cfg.sink.feishu.identity = "bot"
        cfg.sink.feishu.lark_cli = "/fake/lark-cli"

        result = {
            "meta": {
                "title": "测试",
                "thumbnail": "https://example.com/cover.jpg",
                "screenshots": [{"timestamp_str": "00:01"}],
            }
        }

        with patch.object(
            Feishu, "emit_screenshots"
        ) as mock_es, patch.object(
            Feishu, "_batch_create", return_value="rec_1"
        ):
            Feishu().emit(result, cfg)

        mock_es.assert_not_called()

    def test_emit_normal_when_no_screenshots_in_result(self, tmp_path):
        """result 中无 screenshots 时，走正常 emit 路径"""
        schema = tmp_path / "s.toml"
        schema.write_text(
            '[[fields]]\nname = "标题"\ntype = "text"\nsource = "meta.title"\n',
            encoding="utf-8",
        )
        cfg = Config()
        cfg.sink.feishu.base_token = "tok"
        cfg.sink.feishu.table_id = "tbl"
        cfg.sink.feishu.schema = str(schema)
        cfg.sink.feishu.screenshot_table_id = "screenshot_tbl"
        cfg.sink.feishu.identity = "bot"
        cfg.sink.feishu.lark_cli = "/fake/lark-cli"

        result = {"meta": {"title": "测试", "thumbnail": "https://example.com/cover.jpg"}}

        with patch.object(
            Feishu, "emit_screenshots"
        ) as mock_es, patch.object(
            Feishu, "_batch_create", return_value="rec_1"
        ):
            Feishu().emit(result, cfg)

        mock_es.assert_not_called()


class TestEmitScreenshots:
    """emit_screenshots() 方法测试"""

    def test_single_screenshot_emit(self, tmp_path):
        """单张截图写入飞书"""
        cfg = _screenshot_cfg(tmp_path)
        cfg.sink.feishu.lark_cli = "/fake/lark-cli"

        img = tmp_path / "subtitle_0000_1000.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        screenshots = [
            {
                "index": 0,
                "timestamp_str": "00:01",
                "subtitle_text": "测试字幕",
                "description": "AI 描述内容",
                "image_path": str(img),
                "phash": "abc123",
            }
        ]
        meta = {"video_id": "bv_123", "title": "测试视频"}

        with patch(
            "vtf.sinks.feishu.subprocess.run",
            side_effect=[_fake_create_resp("rec_001"), _fake_upload_resp()],
        ) as run_mock:
            outcome = Feishu().emit_screenshots(screenshots, meta, cfg)

        # 验证 batch_create 调用
        create_cmd = run_mock.call_args_list[0].args[0]
        assert "+record-batch-create" in create_cmd
        assert create_cmd[create_cmd.index("--table-id") + 1] == "screenshot_tbl"
        assert create_cmd[create_cmd.index("--base-token") + 1] == "tok"

        # 验证 payload 内容
        json_idx = create_cmd.index("--json") + 1
        payload = json.loads(create_cmd[json_idx])
        assert "视频ID" in payload["fields"]
        assert "时间点(可读)" in payload["fields"]
        assert "字幕文本" in payload["fields"]
        assert "截图描述" in payload["fields"]

        # 验证附件上传调用
        upload_cmd = run_mock.call_args_list[1].args[0]
        assert "+record-upload-attachment" in upload_cmd
        assert upload_cmd[upload_cmd.index("--record-id") + 1] == "rec_001"
        assert upload_cmd[upload_cmd.index("--field-id") + 1] == "截图文件"

        assert "1 成功" in outcome.reason
        assert "已上传" in outcome.reason

    def test_multiple_screenshots_emit(self, tmp_path):
        """多张截图批量写入"""
        cfg = _screenshot_cfg(tmp_path)
        cfg.sink.feishu.lark_cli = "/fake/lark-cli"

        screenshots = []
        for i in range(3):
            img = tmp_path / f"subtitle_{i:04d}_{i * 1000}.jpg"
            img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)
            screenshots.append({
                "index": i,
                "timestamp_str": f"00:0{i}",
                "subtitle_text": f"字幕{i}",
                "description": "",
                "image_path": str(img),
                "phash": f"hash_{i}",
            })

        meta = {"video_id": "bv_456", "title": "多截图测试"}

        # 每张截图 2 次 subprocess 调用: batch_create + upload
        responses = []
        for i in range(3):
            responses.append(_fake_create_resp(f"rec_{i:03d}"))
            responses.append(_fake_upload_resp())

        with patch(
            "vtf.sinks.feishu.subprocess.run",
            side_effect=responses,
        ) as run_mock:
            outcome = Feishu().emit_screenshots(screenshots, meta, cfg)

        assert "3 成功" in outcome.reason
        # 3 张截图 × 2 次调用 (create + upload)
        assert run_mock.call_count == 6

    def test_partial_failure(self, tmp_path):
        """部分截图失败时继续处理其余截图"""
        cfg = _screenshot_cfg(tmp_path)
        cfg.sink.feishu.lark_cli = "/fake/lark-cli"

        screenshots = []
        for i in range(2):
            img = tmp_path / f"img_{i}.jpg"
            img.write_bytes(b"\x00" * 50)
            screenshots.append({
                "timestamp_str": f"00:0{i}",
                "subtitle_text": f"字幕{i}",
                "image_path": str(img),
            })

        meta = {"video_id": "bv_789"}

        fail_resp = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="permission denied"
        )

        # 第1张成功，第2张失败
        with patch(
            "vtf.sinks.feishu.subprocess.run",
            side_effect=[
                _fake_create_resp("rec_001"),
                _fake_upload_resp(),
                fail_resp,  # 第2张 batch_create 失败
            ],
        ):
            outcome = Feishu().emit_screenshots(screenshots, meta, cfg)

        assert "1 成功" in outcome.reason
        assert "1 失败" in outcome.reason

    def test_missing_schema_file(self, tmp_path):
        """schema 文件不存在时报错"""
        cfg = _screenshot_cfg(tmp_path)
        cfg.sink.feishu.screenshot_schema = "/nonexistent/schema.toml"
        cfg.sink.feishu.lark_cli = "/fake/lark-cli"

        with pytest.raises(UserError, match="截图 schema 文件不存在"):
            Feishu().emit_screenshots([{"timestamp_str": "00:01"}], {}, cfg)

    def test_empty_screenshots_list(self, tmp_path):
        """空截图列表不报错"""
        cfg = _screenshot_cfg(tmp_path)
        cfg.sink.feishu.lark_cli = "/fake/lark-cli"

        outcome = Feishu().emit_screenshots([], {}, cfg)
        assert "0 成功" in outcome.reason

    def test_screenshot_without_attachment(self, tmp_path):
        """截图无附件文件时只创建记录不上传"""
        cfg = _screenshot_cfg(tmp_path)
        cfg.sink.feishu.lark_cli = "/fake/lark-cli"

        screenshots = [{
            "timestamp_str": "00:05",
            "subtitle_text": "无图字幕",
            "image_path": "/nonexistent/img.jpg",
        }]

        with patch(
            "vtf.sinks.feishu.subprocess.run",
            return_value=_fake_create_resp("rec_no_img"),
        ) as run_mock:
            outcome = Feishu().emit_screenshots(screenshots, {}, cfg)

        # 只调用 batch_create，不调用 upload
        assert run_mock.call_count == 1
        assert "1 成功" in outcome.reason
        assert "跳过" in outcome.reason

    def test_render_field_resolves_screenshot_sources(self, tmp_path):
        """验证 render_field 能正确从 single_result 中解析 screenshots.xxx 路径"""
        cfg = _screenshot_cfg(tmp_path)
        cfg.sink.feishu.lark_cli = "/fake/lark-cli"

        img = tmp_path / "test.jpg"
        img.write_bytes(b"\x00" * 50)

        screenshots = [{
            "timestamp_str": "02:30",
            "subtitle_text": "关键内容",
            "description": "详细描述",
            "image_path": str(img),
        }]
        meta = {"video_id": "bv_test", "title": "标题"}

        captured_payload = {}

        def capture_run(cmd, **kwargs):
            if "+record-batch-create" in cmd:
                json_idx = cmd.index("--json") + 1
                captured_payload.update(json.loads(cmd[json_idx]))
                return _fake_create_resp("rec_capture")
            return _fake_upload_resp()

        with patch("vtf.sinks.feishu.subprocess.run", side_effect=capture_run):
            Feishu().emit_screenshots(screenshots, meta, cfg)

        row = captured_payload["rows"][0]
        fields = captured_payload["fields"]

        # 验证 meta 字段
        vid_idx = fields.index("视频ID")
        assert row[vid_idx] == "bv_test"

        # 验证 screenshots 字段
        ts_idx = fields.index("时间点(可读)")
        assert row[ts_idx] == "02:30"

        sub_idx = fields.index("字幕文本")
        assert row[sub_idx] == "关键内容"

        desc_idx = fields.index("截图描述")
        assert row[desc_idx] == "详细描述"


class TestScreenshotEmitCLI:
    """screenshot-emit 命令测试"""

    def test_help(self):
        from click.testing import CliRunner
        from vtf.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["screenshot-emit", "--help"])
        assert result.exit_code == 0
        assert "screenshots.json" in result.output

    def test_missing_screenshot_table_id(self, tmp_path):
        """未配置 screenshot_table_id 时报错"""
        from click.testing import CliRunner
        from vtf.cli import main

        screenshots_path = tmp_path / "screenshots.json"
        screenshots_path.write_text(
            json.dumps({"screenshots": [{"timestamp_str": "00:01"}]})
        )

        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text(
            '[sink.feishu]\n'
            'base_token = "tok"\n'
            'table_id = "tbl"\n'
            'screenshot_table_id = ""\n'
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--config", str(cfg_path), "screenshot-emit", "--input", str(screenshots_path)],
        )
        assert result.exit_code != 0
        output = result.output or str(result.exception or "")
        assert "screenshot_table_id" in output

    def test_empty_screenshots(self, tmp_path):
        """空截图列表"""
        from click.testing import CliRunner
        from vtf.cli import main

        screenshots_path = tmp_path / "screenshots.json"
        screenshots_path.write_text(json.dumps({"screenshots": []}))

        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text(
            '[sink.feishu]\n'
            'base_token = "tok"\n'
            'table_id = "tbl"\n'
            'screenshot_table_id = "ss_tbl"\n'
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--config", str(cfg_path), "screenshot-emit", "--input", str(screenshots_path)],
        )
        assert result.exit_code == 0
        assert "没有截图数据" in result.output

    def test_accepts_list_format(self, tmp_path):
        """兼容直接列表格式的 screenshots.json"""
        from click.testing import CliRunner
        from vtf.cli import main

        screenshots_path = tmp_path / "screenshots.json"
        screenshots_path.write_text(
            json.dumps([{"timestamp_str": "00:01", "image_path": "/tmp/x.jpg"}])
        )

        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text(
            '[sink.feishu]\n'
            'base_token = "tok"\n'
            'table_id = "tbl"\n'
            'screenshot_table_id = "ss_tbl"\n'
            'lark_cli = "/fake/lark-cli"\n'
        )

        with patch(
            "vtf.sinks.feishu.subprocess.run",
            return_value=_fake_create_resp(),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--config", str(cfg_path), "screenshot-emit", "--input", str(screenshots_path)],
            )

        assert result.exit_code == 0
