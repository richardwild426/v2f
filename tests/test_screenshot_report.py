"""Tests for screenshot report generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vtf.pipeline.screenshot_report import generate_html_report, generate_json_report


@pytest.fixture
def sample_screenshots():
    return [
        {
            "index": 0,
            "timestamp_ms": 5000,
            "timestamp_str": "00:05",
            "subtitle_text": "大家好",
            "image_path": "/tmp/test.jpg",
            "phash": "abc123",
            "type": "subtitle",
            "description": "主持人开场",
            "scene_tags": "主持人,开场",
        },
        {
            "index": 1,
            "timestamp_ms": 15000,
            "timestamp_str": "00:15",
            "subtitle_text": "",
            "image_path": "/tmp/scene.jpg",
            "phash": "def456",
            "type": "scene",
            "description": "会议室场景",
            "scene_tags": "会议室,讨论",
        },
    ]


class TestHTMLReport:
    """HTML 报告生成测试。"""

    def test_generate_html_basic(self, sample_screenshots):
        """测试基本 HTML 报告生成。"""
        html = generate_html_report(screenshots=sample_screenshots)
        
        assert "<!DOCTYPE html>" in html
        assert "视频截图报告" in html
        assert "总截图数: 2" in html
        assert "字幕截图: 1" in html
        assert "场景截图: 1" in html

    def test_generate_html_custom_title(self, sample_screenshots):
        """测试自定义标题。"""
        html = generate_html_report(
            screenshots=sample_screenshots,
            title="自定义标题",
        )
        
        assert "自定义标题" in html

    def test_generate_html_contains_timestamp(self, sample_screenshots):
        """测试报告包含时间戳。"""
        html = generate_html_report(screenshots=sample_screenshots)
        
        assert "00:05" in html
        assert "00:15" in html

    def test_generate_html_contains_subtitle(self, sample_screenshots):
        """测试报告包含字幕文本。"""
        html = generate_html_report(screenshots=sample_screenshots)
        
        assert "大家好" in html

    def test_generate_html_contains_description(self, sample_screenshots):
        """测试报告包含 AI 描述。"""
        html = generate_html_report(screenshots=sample_screenshots)
        
        assert "主持人开场" in html
        assert "会议室场景" in html

    def test_generate_html_contains_tags(self, sample_screenshots):
        """测试报告包含场景标签。"""
        html = generate_html_report(screenshots=sample_screenshots)
        
        assert "主持人" in html
        assert "开场" in html

    def test_generate_html_type_labels(self, sample_screenshots):
        """测试类型标签。"""
        html = generate_html_report(screenshots=sample_screenshots)
        
        assert "字幕" in html
        assert "场景" in html

    def test_generate_html_empty_screenshots(self):
        """测试空截图列表。"""
        html = generate_html_report(screenshots=[])
        
        assert "总截图数: 0" in html
        assert "字幕截图: 0" in html
        assert "场景截图: 0" in html

    def test_generate_html_save_to_file(self, sample_screenshots, tmp_path):
        """测试保存到文件。"""
        output_path = tmp_path / "report.html"
        html = generate_html_report(
            screenshots=sample_screenshots,
            output_path=output_path,
        )
        
        assert output_path.exists()
        saved = output_path.read_text(encoding="utf-8")
        assert saved == html

    def test_generate_html_responsive(self, sample_screenshots):
        """测试 HTML 包含响应式设计元素。"""
        html = generate_html_report(screenshots=sample_screenshots)
        
        assert "viewport" in html
        assert "grid-template-columns" in html

    def test_generate_html_modal(self, sample_screenshots):
        """测试 HTML 包含图片放大模态框。"""
        html = generate_html_report(screenshots=sample_screenshots)
        
        assert "modal" in html
        assert "openModal" in html
        assert "closeModal" in html


class TestJSONReport:
    """JSON 报告生成测试。"""

    def test_generate_json_basic(self, sample_screenshots):
        """测试基本 JSON 报告生成。"""
        report = generate_json_report(screenshots=sample_screenshots)
        
        assert "generated_at" in report
        assert report["total_count"] == 2
        assert len(report["screenshots"]) == 2

    def test_generate_json_screenshots_data(self, sample_screenshots):
        """测试 JSON 报告包含完整截图数据。"""
        report = generate_json_report(screenshots=sample_screenshots)
        
        first = report["screenshots"][0]
        assert first["index"] == 0
        assert first["timestamp_str"] == "00:05"
        assert first["subtitle_text"] == "大家好"
        assert first["description"] == "主持人开场"

    def test_generate_json_save_to_file(self, sample_screenshots, tmp_path):
        """测试保存 JSON 到文件。"""
        output_path = tmp_path / "report.json"
        report = generate_json_report(
            screenshots=sample_screenshots,
            output_path=output_path,
        )
        
        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["total_count"] == report["total_count"]

    def test_generate_json_empty_screenshots(self):
        """测试空截图列表。"""
        report = generate_json_report(screenshots=[])
        
        assert report["total_count"] == 0
        assert report["screenshots"] == []


class TestScreenshotReportCLI:
    """截图报告 CLI 测试。"""

    def test_report_help(self):
        """测试帮助信息。"""
        from click.testing import CliRunner
        from vtf.commands.screenshot_report import cmd
        
        runner = CliRunner()
        result = runner.invoke(cmd, ["--help"])
        assert result.exit_code == 0
        assert "截图" in result.output
