"""截图功能测试"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vtf.cli import main
from vtf.config import Config, ScreenshotConfig
from vtf.pipeline.screenshot import (
    _calculate_phash,
    _calculate_similarity,
    take_screenshots,
    take_scene_screenshots,
    take_screenshots_with_description,
)
from vtf.pipeline.screenshot_describe import (
    _parse_llm_result,
    generate_description_prompt,
    generate_descriptions,
)


class TestScreenshotConfig:
    """截图配置测试"""

    def test_default_config(self):
        cfg = ScreenshotConfig()
        assert cfg.enabled is True
        assert cfg.ffmpeg_path == "ffmpeg"
        assert cfg.scene_threshold == 0.3
        assert cfg.min_interval_seconds == 2
        assert cfg.similarity_threshold == 0.95
        assert cfg.output_dir == "screenshots"
        assert cfg.quality == 2
        assert cfg.width == 0
        assert cfg.height == 0
        assert cfg.scale == 1.0

    def test_custom_config(self):
        cfg = ScreenshotConfig(
            enabled=False,
            ffmpeg_path="/usr/local/bin/ffmpeg",
            scene_threshold=0.5,
            min_interval_seconds=5,
            similarity_threshold=0.9,
            output_dir="output/screenshots",
            quality=5,
            width=1280,
            height=720,
            scale=0.5,
        )
        assert cfg.enabled is False
        assert cfg.ffmpeg_path == "/usr/local/bin/ffmpeg"
        assert cfg.scene_threshold == 0.5
        assert cfg.min_interval_seconds == 5
        assert cfg.similarity_threshold == 0.9
        assert cfg.output_dir == "output/screenshots"
        assert cfg.quality == 5
        assert cfg.width == 1280
        assert cfg.height == 720
        assert cfg.scale == 0.5


class TestTakeScreenshots:
    """字幕截图测试"""

    @patch("subprocess.run")
    @patch("vtf.pipeline.screenshot._calculate_phash")
    def test_take_screenshots_success(self, mock_phash, mock_run, tmp_path):
        # 准备测试数据
        video_path = tmp_path / "test.mp4"
        video_path.touch()
        output_dir = tmp_path / "screenshots"
        output_dir.mkdir()

        lines = [
            {"text": "字幕1", "start_ms": 1000, "end_ms": 2000},
            {"text": "字幕2", "start_ms": 3000, "end_ms": 4000},
        ]

        cfg = MagicMock()
        cfg.screenshot.output_dir = str(output_dir)
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.similarity_threshold = 0.95

        # Mock subprocess.run
        mock_run.return_value = MagicMock(returncode=0)
        # Mock _calculate_phash 返回不同的值（避免被去重）
        mock_phash.side_effect = ["hash_0001", "hash_0002"]

        # 创建模拟的截图文件（批量处理生成的文件名）
        for i in range(len(lines)):
            filename = f"subtitle_{i+1:04d}.jpg"
            (output_dir / filename).touch()

        # 执行测试
        screenshots = take_screenshots(video_path=video_path, lines=lines, cfg=cfg)

        # 验证结果
        assert len(screenshots) == 2
        assert screenshots[0]["index"] == 0
        assert screenshots[0]["timestamp_ms"] == 1000
        assert screenshots[0]["subtitle_text"] == "字幕1"
        assert screenshots[0]["phash"] == "hash_0001"
        assert screenshots[1]["index"] == 1
        assert screenshots[1]["timestamp_ms"] == 3000
        assert screenshots[1]["subtitle_text"] == "字幕2"
        assert screenshots[1]["phash"] == "hash_0002"

    @patch("subprocess.run")
    @patch("vtf.pipeline.screenshot._calculate_phash")
    def test_take_screenshots_deduplication(self, mock_phash, mock_run, tmp_path):
        """测试相似截图去重功能"""
        video_path = tmp_path / "test.mp4"
        video_path.touch()
        output_dir = tmp_path / "screenshots"
        output_dir.mkdir()

        lines = [
            {"text": "字幕1", "start_ms": 1000, "end_ms": 2000},
            {"text": "字幕2", "start_ms": 3000, "end_ms": 4000},
        ]

        cfg = MagicMock()
        cfg.screenshot.output_dir = str(output_dir)
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.similarity_threshold = 0.95

        mock_run.return_value = MagicMock(returncode=0)
        # 返回相同的哈希，触发去重
        mock_phash.return_value = "same_hash"

        # 创建模拟的截图文件（批量处理生成的文件名）
        for i in range(len(lines)):
            filename = f"subtitle_{i+1:04d}.jpg"
            (output_dir / filename).touch()

        screenshots = take_screenshots(video_path=video_path, lines=lines, cfg=cfg)

        # 应该只保留第一个截图
        assert len(screenshots) == 1
        assert screenshots[0]["index"] == 0

    @patch("subprocess.run")
    def test_take_screenshots_ffmpeg_failure(self, mock_run, tmp_path):
        video_path = tmp_path / "test.mp4"
        video_path.touch()

        lines = [{"text": "字幕1", "start_ms": 1000, "end_ms": 2000}]

        cfg = MagicMock()
        cfg.screenshot.output_dir = str(tmp_path / "screenshots")
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.similarity_threshold = 0.95
        cfg.screenshot.max_workers = 4  # 添加 max_workers 配置

        # Mock subprocess.run 抛出异常
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")

        screenshots = take_screenshots(video_path=video_path, lines=lines, cfg=cfg)

        # 应该返回空列表
        assert len(screenshots) == 0


class TestTakeSceneScreenshots:
    """场景变化截图测试"""

    @patch("subprocess.run")
    @patch("vtf.pipeline.screenshot._calculate_phash")
    def test_take_scene_screenshots_success(self, mock_phash, mock_run, tmp_path):
        video_path = tmp_path / "test.mp4"
        video_path.touch()
        output_dir = tmp_path / "screenshots"
        output_dir.mkdir()

        cfg = MagicMock()
        cfg.screenshot.output_dir = str(output_dir)
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.scene_threshold = 0.3
        cfg.screenshot.min_interval_seconds = 2
        cfg.screenshot.similarity_threshold = 0.95

        # Mock subprocess.run
        mock_run.return_value = MagicMock(returncode=0)
        # 返回不同的哈希值
        mock_phash.side_effect = ["scene_hash_1", "scene_hash_2", "scene_hash_3"]

        # 创建模拟的场景截图文件
        for i in range(3):
            (output_dir / f"scene_{i + 1:04d}.jpg").touch()

        screenshots = take_scene_screenshots(video_path=video_path, cfg=cfg)

        # 验证结果
        assert len(screenshots) == 3
        assert screenshots[0]["type"] == "scene"
        assert screenshots[0]["phash"] == "scene_hash_1"

    @patch("subprocess.run")
    @patch("vtf.pipeline.screenshot._calculate_phash")
    def test_take_scene_screenshots_deduplication(self, mock_phash, mock_run, tmp_path):
        """测试场景截图去重"""
        video_path = tmp_path / "test.mp4"
        video_path.touch()
        output_dir = tmp_path / "screenshots"
        output_dir.mkdir()

        cfg = MagicMock()
        cfg.screenshot.output_dir = str(output_dir)
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.scene_threshold = 0.3
        cfg.screenshot.min_interval_seconds = 2
        cfg.screenshot.similarity_threshold = 0.95

        mock_run.return_value = MagicMock(returncode=0)
        # 返回相同的哈希，触发去重
        mock_phash.return_value = "same_scene_hash"

        for i in range(3):
            (output_dir / f"scene_{i + 1:04d}.jpg").touch()

        screenshots = take_scene_screenshots(video_path=video_path, cfg=cfg)

        # 应该只保留第一个场景截图
        assert len(screenshots) == 1


class TestPhash:
    """感知哈希测试"""

    def test_calculate_phash_fallback_to_md5(self, tmp_path):
        """当 imagehash 不可用时，回退到 MD5"""
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"test image content")

        with patch("vtf.pipeline.screenshot.HAS_IMAGEHASH", False):
            phash = _calculate_phash(img_path)

        assert len(phash) == 16  # MD5 的前 16 位

    def test_calculate_similarity_identical(self):
        """相同哈希的相似度为 1.0"""
        hash1 = "a" * 16
        similarity = _calculate_similarity(hash1, hash1)
        assert similarity == 1.0

    def test_calculate_similarity_different(self):
        """不同哈希的相似度计算"""
        hash1 = "a" * 16
        hash2 = "b" * 16
        similarity = _calculate_similarity(hash1, hash2)
        assert 0 <= similarity <= 1


class TestScreenshotCLI:
    """截图 CLI 命令测试"""

    def test_screenshot_help(self):
        """测试截图命令帮助信息"""
        runner = CliRunner()
        result = runner.invoke(main, ["screenshot", "--help"])
        assert result.exit_code == 0
        assert "根据字幕时间戳截取视频帧" in result.output
        assert "--video" in result.output
        assert "--subtitles" in result.output
        assert "--output" in result.output
        assert "--mode" in result.output

    def test_screenshot_missing_video(self):
        """测试缺少视频文件时的错误处理"""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["screenshot", "--video", "/nonexistent/video.mp4", "--subtitles", "subs.json"],
        )
        assert result.exit_code != 0
        assert "视频文件不存在" in result.output

    def test_screenshot_missing_subtitles(self, tmp_path):
        """测试缺少字幕文件时的错误处理"""
        video_path = tmp_path / "test.mp4"
        video_path.touch()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["screenshot", "--video", str(video_path), "--subtitles", "/nonexistent/subs.json"],
        )
        assert result.exit_code != 0
        assert "读取字幕文件失败" in result.output

    def test_screenshot_empty_subtitles(self, tmp_path):
        """测试空字幕文件时的错误处理"""
        video_path = tmp_path / "test.mp4"
        video_path.touch()
        subs_path = tmp_path / "subs.json"
        subs_path.write_text(json.dumps({"lines": []}))

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["screenshot", "--video", str(video_path), "--subtitles", str(subs_path)],
        )
        assert result.exit_code != 0
        assert "没有找到字幕数据" in result.output

    def test_screenshot_help_with_ai_describe(self):
        """测试 --ai-describe 选项在帮助信息中"""
        runner = CliRunner()
        result = runner.invoke(main, ["screenshot", "--help"])
        assert result.exit_code == 0
        assert "--ai-describe" in result.output


class TestAIDescriptionPrompt:
    """AI 描述 prompt 生成测试"""

    def test_generate_prompt_with_subtitle(self):
        """测试带字幕的 prompt 生成"""
        screenshot = {
            "timestamp_str": "01:23",
            "subtitle_text": "这是一段测试字幕",
            "type": "subtitle",
        }
        prompt = generate_description_prompt(screenshot)
        assert "01:23" in prompt
        assert "这是一段测试字幕" in prompt
        assert "subtitle" in prompt
        assert "description" in prompt
        assert "scene_tags" in prompt

    def test_generate_prompt_without_subtitle(self):
        """测试无字幕的 prompt 生成"""
        screenshot = {
            "timestamp_str": "00:05",
            "subtitle_text": "",
            "type": "scene",
        }
        prompt = generate_description_prompt(screenshot)
        assert "00:05" in prompt
        assert "（无字幕）" in prompt
        assert "scene" in prompt

    def test_generate_prompt_default_values(self):
        """测试默认值的 prompt 生成"""
        screenshot = {}
        prompt = generate_description_prompt(screenshot)
        assert "00:00" in prompt
        assert "（无字幕）" in prompt
        assert "subtitle" in prompt


class TestParseLlmResult:
    """LLM 结果解析测试"""

    def test_parse_dict(self):
        """测试解析 dict 类型结果"""
        result = {"description": "测试描述", "scene_tags": "标签1,标签2"}
        parsed = _parse_llm_result(result)
        assert parsed == result

    def test_parse_json_string(self):
        """测试解析 JSON 字符串"""
        result = '{"description": "测试描述", "scene_tags": "标签1,标签2"}'
        parsed = _parse_llm_result(result)
        assert parsed["description"] == "测试描述"
        assert parsed["scene_tags"] == "标签1,标签2"

    def test_parse_markdown_json(self):
        """测试解析 markdown code block 中的 JSON"""
        result = '```json\n{"description": "测试描述", "scene_tags": "标签1"}\n```'
        parsed = _parse_llm_result(result)
        assert parsed["description"] == "测试描述"
        assert parsed["scene_tags"] == "标签1"

    def test_parse_json_with_extra_text(self):
        """测试解析带额外文本的 JSON"""
        result = '这是分析结果：\n{"description": "测试描述", "scene_tags": "标签1"}\n以上。'
        parsed = _parse_llm_result(result)
        assert parsed["description"] == "测试描述"
        assert parsed["scene_tags"] == "标签1"

    def test_parse_invalid_json(self):
        """测试解析无效 JSON"""
        result = "这不是 JSON"
        parsed = _parse_llm_result(result)
        assert parsed == {}

    def test_parse_non_string(self):
        """测试解析非字符串类型"""
        parsed = _parse_llm_result(123)
        assert parsed == {}


class TestGenerateDescriptions:
    """AI 描述生成测试"""

    def test_generate_without_llm_caller(self, tmp_path):
        """测试无 LLM 调用器时只生成 prompt"""
        img_path = tmp_path / "test.jpg"
        img_path.touch()

        screenshots = [
            {
                "image_path": str(img_path),
                "timestamp_str": "01:23",
                "subtitle_text": "测试字幕",
                "type": "subtitle",
            }
        ]

        result = generate_descriptions(
            screenshots=screenshots,
            cfg=MagicMock(),
            llm_caller=None,
        )

        assert len(result) == 1
        assert "prompt" in result[0]
        assert "01:23" in result[0]["prompt"]
        assert result[0]["description"] == ""
        assert result[0]["scene_tags"] == ""

    def test_generate_with_llm_caller(self, tmp_path):
        """测试带 LLM 调用器的描述生成"""
        img_path = tmp_path / "test.jpg"
        img_path.touch()

        screenshots = [
            {
                "image_path": str(img_path),
                "timestamp_str": "01:23",
                "subtitle_text": "测试字幕",
                "type": "subtitle",
            }
        ]

        def mock_llm_caller(image_path, prompt):
            return '{"description": "测试描述", "scene_tags": "测试,标签"}'

        result = generate_descriptions(
            screenshots=screenshots,
            cfg=MagicMock(),
            llm_caller=mock_llm_caller,
        )

        assert len(result) == 1
        assert "prompt" in result[0]
        assert result[0]["description"] == "测试描述"
        assert result[0]["scene_tags"] == "测试,标签"

    def test_generate_with_missing_image(self, tmp_path):
        """测试图片文件不存在时的处理"""
        screenshots = [
            {
                "image_path": str(tmp_path / "nonexistent.jpg"),
                "timestamp_str": "01:23",
                "subtitle_text": "测试字幕",
                "type": "subtitle",
            }
        ]

        def mock_llm_caller(image_path, prompt):
            return '{"description": "测试", "scene_tags": "标签"}'

        result = generate_descriptions(
            screenshots=screenshots,
            cfg=MagicMock(),
            llm_caller=mock_llm_caller,
        )

        assert len(result) == 1
        assert result[0]["description"] == ""
        assert result[0]["scene_tags"] == ""

    def test_generate_with_llm_error(self, tmp_path):
        """测试 LLM 调用出错时的处理"""
        img_path = tmp_path / "test.jpg"
        img_path.touch()

        screenshots = [
            {
                "image_path": str(img_path),
                "timestamp_str": "01:23",
                "subtitle_text": "测试字幕",
                "type": "subtitle",
            }
        ]

        def mock_llm_caller(image_path, prompt):
            raise RuntimeError("LLM 调用失败")

        result = generate_descriptions(
            screenshots=screenshots,
            cfg=MagicMock(),
            llm_caller=mock_llm_caller,
        )

        assert len(result) == 1
        assert result[0]["description"] == ""
        assert result[0]["scene_tags"] == ""

    def test_generate_multiple_screenshots(self, tmp_path):
        """测试多张截图的描述生成"""
        screenshots = []
        for i in range(3):
            img_path = tmp_path / f"test_{i}.jpg"
            img_path.touch()
            screenshots.append(
                {
                    "image_path": str(img_path),
                    "timestamp_str": f"0{i}:00",
                    "subtitle_text": f"字幕{i}",
                    "type": "subtitle",
                }
            )

        call_count = 0

        def mock_llm_caller(image_path, prompt):
            nonlocal call_count
            call_count += 1
            return f'{{"description": "描述{call_count}", "scene_tags": "标签{call_count}"}}'

        result = generate_descriptions(
            screenshots=screenshots,
            cfg=MagicMock(),
            llm_caller=mock_llm_caller,
        )

        assert len(result) == 3
        assert call_count == 3
        for i, r in enumerate(result):
            assert r["description"] == f"描述{i + 1}"
            assert r["scene_tags"] == f"标签{i + 1}"


class TestTakeScreenshotsWithDescription:
    """截图 + AI 描述整合测试"""

    @patch("subprocess.run")
    @patch("vtf.pipeline.screenshot._calculate_phash")
    @patch("vtf.pipeline.screenshot.generate_descriptions")
    def test_with_ai_describe_enabled(
        self, mock_generate, mock_phash, mock_run, tmp_path
    ):
        """测试启用 AI 描述时的截图流程"""
        video_path = tmp_path / "test.mp4"
        video_path.touch()
        output_dir = tmp_path / "screenshots"
        output_dir.mkdir()

        lines = [{"text": "字幕1", "start_ms": 1000, "end_ms": 2000}]

        cfg = MagicMock()
        cfg.screenshot.output_dir = str(output_dir)
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.similarity_threshold = 0.95
        cfg.screenshot.ai_describe = True

        mock_run.return_value = MagicMock(returncode=0)
        mock_phash.return_value = "hash_0001"
        (output_dir / "subtitle_0000_1000.jpg").touch()

        # Mock generate_descriptions 返回带描述的结果
        mock_generate.return_value = [
            {
                "index": 0,
                "timestamp_ms": 1000,
                "timestamp_str": "00:01",
                "subtitle_text": "字幕1",
                "image_path": str(output_dir / "subtitle_0000_1000.jpg"),
                "phash": "hash_0001",
                "prompt": "test prompt",
                "description": "AI 生成的描述",
                "scene_tags": "标签1,标签2",
            }
        ]

        screenshots = take_screenshots_with_description(
            video_path=video_path, lines=lines, cfg=cfg
        )

        assert len(screenshots) == 1
        assert screenshots[0]["description"] == "AI 生成的描述"
        assert screenshots[0]["scene_tags"] == "标签1,标签2"
        mock_generate.assert_called_once()

    @patch("subprocess.run")
    @patch("vtf.pipeline.screenshot._calculate_phash")
    @patch("vtf.pipeline.screenshot.generate_descriptions")
    def test_with_ai_describe_disabled(
        self, mock_generate, mock_phash, mock_run, tmp_path
    ):
        """测试禁用 AI 描述时的截图流程"""
        video_path = tmp_path / "test.mp4"
        video_path.touch()
        output_dir = tmp_path / "screenshots"
        output_dir.mkdir()

        lines = [{"text": "字幕1", "start_ms": 1000, "end_ms": 2000}]

        cfg = MagicMock()
        cfg.screenshot.output_dir = str(output_dir)
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.similarity_threshold = 0.95
        cfg.screenshot.ai_describe = False

        mock_run.return_value = MagicMock(returncode=0)
        mock_phash.return_value = "hash_0001"
        # 创建模拟的截图文件（批量处理生成的文件名）
        (output_dir / "subtitle_0001.jpg").touch()

        screenshots = take_screenshots_with_description(
            video_path=video_path, lines=lines, cfg=cfg
        )

        assert len(screenshots) == 1
        # generate_descriptions 不应被调用
        mock_generate.assert_not_called()

    @patch("subprocess.run")
    @patch("vtf.pipeline.screenshot._calculate_phash")
    @patch("vtf.pipeline.screenshot.generate_descriptions")
    def test_with_llm_caller(
        self, mock_generate, mock_phash, mock_run, tmp_path
    ):
        """测试传入 llm_caller 时的截图流程"""
        video_path = tmp_path / "test.mp4"
        video_path.touch()
        output_dir = tmp_path / "screenshots"
        output_dir.mkdir()

        lines = [{"text": "字幕1", "start_ms": 1000, "end_ms": 2000}]

        cfg = MagicMock()
        cfg.screenshot.output_dir = str(output_dir)
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.similarity_threshold = 0.95
        cfg.screenshot.ai_describe = False  # 配置禁用

        mock_run.return_value = MagicMock(returncode=0)
        mock_phash.return_value = "hash_0001"
        (output_dir / "subtitle_0000_1000.jpg").touch()

        mock_generate.return_value = [
            {
                "index": 0,
                "timestamp_ms": 1000,
                "description": "LLM 描述",
                "scene_tags": "标签",
            }
        ]

        def mock_llm_caller(image_path, prompt):
            return '{"description": "LLM 描述", "scene_tags": "标签"}'

        screenshots = take_screenshots_with_description(
            video_path=video_path,
            lines=lines,
            cfg=cfg,
            llm_caller=mock_llm_caller,
        )

        assert len(screenshots) == 1
        # 即使配置禁用，传入 llm_caller 也会触发描述生成
        mock_generate.assert_called_once()


class TestProgressCallback:
    """进度回调测试"""

    @patch("subprocess.run")
    @patch("vtf.pipeline.screenshot._calculate_phash")
    def test_progress_callback_called(self, mock_phash, mock_run, tmp_path):
        """测试进度回调被正确调用"""
        video_path = tmp_path / "test.mp4"
        video_path.touch()
        output_dir = tmp_path / "screenshots"
        output_dir.mkdir()

        lines = [
            {"text": "字幕1", "start_ms": 1000, "end_ms": 2000},
            {"text": "字幕2", "start_ms": 3000, "end_ms": 4000},
        ]

        cfg = MagicMock()
        cfg.screenshot.output_dir = str(output_dir)
        cfg.screenshot.ffmpeg_path = "ffmpeg"
        cfg.screenshot.similarity_threshold = 0.95

        mock_run.return_value = MagicMock(returncode=0)
        mock_phash.side_effect = ["hash_1", "hash_2"]

        # 创建模拟的截图文件
        for i in range(len(lines)):
            (output_dir / f"subtitle_{i+1:04d}.jpg").touch()

        # 记录进度回调
        progress_calls = []

        def progress_callback(current, total, message=""):
            progress_calls.append((current, total, message))

        screenshots = take_screenshots(
            video_path=video_path,
            lines=lines,
            cfg=cfg,
            progress_callback=progress_callback,
        )

        assert len(screenshots) == 2
        # 验证进度回调被调用
        assert len(progress_calls) > 0
        # 最后一次调用应该是完成状态
        last_call = progress_calls[-1]
        assert last_call[0] == last_call[1]  # current == total

    def test_no_progress_callback(self, tmp_path):
        """测试没有进度回调时不会出错"""
        from vtf.pipeline.screenshot import _noop_progress

        # 空进度回调应该可以正常调用
        _noop_progress(0, 10, "测试")
        _noop_progress(5, 10, "测试")
        _noop_progress(10, 10, "完成")


class TestCLIQualityOptions:
    """CLI 质量/尺寸选项测试"""

    def test_screenshot_help_shows_quality_options(self):
        """测试帮助信息包含质量/尺寸选项"""
        runner = CliRunner()
        result = runner.invoke(main, ["screenshot", "--help"])
        assert result.exit_code == 0
        assert "--quality" in result.output
        assert "--width" in result.output
        assert "--height" in result.output
        assert "--scale" in result.output

    def test_screenshot_help_shows_progress_option(self):
        """测试帮助信息包含进度条选项"""
        runner = CliRunner()
        result = runner.invoke(main, ["screenshot", "--help"])
        assert result.exit_code == 0
        assert "--progress" in result.output
        assert "--no-progress" in result.output


class TestScreenshotBatchCLI:
    """批量截图 CLI 测试"""

    def test_screenshot_batch_help(self):
        """测试批量截图命令帮助信息"""
        runner = CliRunner()
        result = runner.invoke(main, ["screenshot-batch", "--help"])
        assert result.exit_code == 0
        assert "批量处理多个视频的截图" in result.output
        assert "--videos" in result.output
        assert "--videos-dir" in result.output
        assert "--subtitles-dir" in result.output
        assert "--quality" in result.output
        assert "--width" in result.output
        assert "--height" in result.output
        assert "--scale" in result.output

    def test_screenshot_batch_no_videos(self):
        """测试没有视频文件时的错误处理"""
        runner = CliRunner()
        result = runner.invoke(main, ["screenshot-batch", "-v", "/nonexistent/video.mp4"])
        assert result.exit_code != 0
