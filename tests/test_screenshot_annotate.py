"""截图标注功能测试。"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from vtf.pipeline.screenshot_annotate import (
    Annotation,
    AnnotationConfig,
    AnnotationType,
    annotate_image,
    annotate_screenshots,
    create_arrow_annotation,
    create_highlight_annotation,
    create_rectangle_annotation,
    create_text_annotation,
    create_timestamp_annotation,
    hex_to_rgba,
    load_annotations_from_json,
)


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """创建测试图片。"""
    try:
        from PIL import Image, ImageDraw

        # 创建一个简单的测试图片
        img = Image.new("RGB", (400, 300), color="white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 350, 250], outline="black", width=2)
        draw.text((100, 100), "Test Image", fill="black")

        image_path = tmp_path / "test_image.jpg"
        img.save(image_path)
        return image_path
    except ImportError:
        pytest.skip("Pillow not installed")


@pytest.fixture
def sample_annotations_json(tmp_path: Path) -> Path:
    """创建测试标注配置 JSON。"""
    annotations = {
        "0": [
            {
                "type": "text",
                "position": [10, 10],
                "content": "重要信息",
                "color": "#FF0000",
                "size": 24,
            },
            {
                "type": "arrow",
                "position": [50, 50],
                "end_position": [200, 200],
                "color": "#00FF00",
            },
            {
                "type": "rectangle",
                "position": [100, 100],
                "end_position": [300, 250],
                "color": "#0000FF",
                "size": 3,
            },
        ],
        "1": [
            {
                "type": "highlight",
                "position": [50, 50],
                "end_position": [200, 150],
                "color": "#FFFF00",
            },
        ],
    }

    json_path = tmp_path / "annotations.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(annotations, f, ensure_ascii=False, indent=2)

    return json_path


class TestAnnotationTypes:
    """标注类型测试。"""

    def test_annotation_type_values(self):
        """测试标注类型枚举值。"""
        assert AnnotationType.TEXT == "text"
        assert AnnotationType.ARROW == "arrow"
        assert AnnotationType.RECTANGLE == "rectangle"
        assert AnnotationType.HIGHLIGHT == "highlight"
        assert AnnotationType.TIMESTAMP == "timestamp"

    def test_annotation_creation(self):
        """测试标注对象创建。"""
        annotation = Annotation(
            type=AnnotationType.TEXT,
            position=(100, 100),
            content="测试文字",
            color="#FF0000",
            size=20,
        )

        assert annotation.type == AnnotationType.TEXT
        assert annotation.position == (100, 100)
        assert annotation.content == "测试文字"
        assert annotation.color == "#FF0000"
        assert annotation.size == 20
        assert annotation.opacity == 1.0

    def test_annotation_with_end_position(self):
        """测试带终点的标注。"""
        annotation = Annotation(
            type=AnnotationType.ARROW,
            position=(50, 50),
            end_position=(200, 200),
            color="#00FF00",
        )

        assert annotation.end_position == (200, 200)


class TestColorConversion:
    """颜色转换测试。"""

    def test_hex_to_rgba_6digit(self):
        """测试 6 位十六进制颜色转换。"""
        r, g, b, a = hex_to_rgba("#FF0000", 1.0)
        assert r == 255
        assert g == 0
        assert b == 0
        assert a == 255

    def test_hex_to_rgba_with_opacity(self):
        """测试带透明度的颜色转换。"""
        r, g, b, a = hex_to_rgba("#00FF00", 0.5)
        assert r == 0
        assert g == 255
        assert b == 0
        assert a == 127

    def test_hex_to_rgba_8digit(self):
        """测试 8 位十六进制颜色转换。"""
        r, g, b, a = hex_to_rgba("#0000FF80", 1.0)
        assert r == 0
        assert g == 0
        assert b == 255
        assert a == 128

    def test_hex_to_rgba_invalid(self):
        """测试无效颜色格式。"""
        with pytest.raises(ValueError):
            hex_to_rgba("invalid")


class TestConvenienceFunctions:
    """便捷函数测试。"""

    def test_create_text_annotation(self):
        """测试创建文字标注。"""
        ann = create_text_annotation("测试", (100, 100), "#FF0000", 24)
        assert ann.type == AnnotationType.TEXT
        assert ann.content == "测试"
        assert ann.position == (100, 100)

    def test_create_arrow_annotation(self):
        """测试创建箭头标注。"""
        ann = create_arrow_annotation((50, 50), (200, 200), "#00FF00")
        assert ann.type == AnnotationType.ARROW
        assert ann.position == (50, 50)
        assert ann.end_position == (200, 200)

    def test_create_rectangle_annotation(self):
        """测试创建矩形标注。"""
        ann = create_rectangle_annotation((10, 10), (100, 100), "#0000FF", 3)
        assert ann.type == AnnotationType.RECTANGLE
        assert ann.position == (10, 10)
        assert ann.end_position == (100, 100)
        assert ann.size == 3

    def test_create_highlight_annotation(self):
        """测试创建高亮标注。"""
        ann = create_highlight_annotation((50, 50), (200, 200), "#FFFF00")
        assert ann.type == AnnotationType.HIGHLIGHT
        assert ann.color == "#FFFF00"

    def test_create_timestamp_annotation(self):
        """测试创建时间戳标注。"""
        ann = create_timestamp_annotation((10, 10), "00:01:30", "#FFFFFF")
        assert ann.type == AnnotationType.TIMESTAMP
        assert ann.content == "00:01:30"


class TestAnnotationConfig:
    """标注配置测试。"""

    def test_default_config(self):
        """测试默认配置。"""
        config = AnnotationConfig()
        assert config.default_font_size == 20
        assert config.default_color == "#FF0000"
        assert config.default_opacity == 1.0
        assert config.padding == 10
        assert config.show_background is True

    def test_custom_config(self):
        """测试自定义配置。"""
        config = AnnotationConfig(
            font_path="/path/to/font.ttf",
            default_font_size=24,
            default_color="#00FF00",
            show_background=False,
        )
        assert config.font_path == "/path/to/font.ttf"
        assert config.default_font_size == 24
        assert config.default_color == "#00FF00"
        assert config.show_background is False


class TestAnnotateImage:
    """图片标注测试。"""

    def test_annotate_image_with_text(self, sample_image: Path, tmp_path: Path):
        """测试文字标注。"""
        annotations = [
            create_text_annotation("测试文字", (50, 50), "#FF0000", 20),
        ]

        output_path = tmp_path / "annotated.jpg"
        result = annotate_image(sample_image, annotations, output_path)

        assert result.exists()
        assert result == output_path

    def test_annotate_image_with_arrow(self, sample_image: Path, tmp_path: Path):
        """测试箭头标注。"""
        annotations = [
            create_arrow_annotation((50, 50), (200, 200), "#00FF00"),
        ]

        output_path = tmp_path / "annotated_arrow.jpg"
        result = annotate_image(sample_image, annotations, output_path)

        assert result.exists()

    def test_annotate_image_with_rectangle(self, sample_image: Path, tmp_path: Path):
        """测试矩形标注。"""
        annotations = [
            create_rectangle_annotation((50, 50), (300, 250), "#0000FF", 3),
        ]

        output_path = tmp_path / "annotated_rect.jpg"
        result = annotate_image(sample_image, annotations, output_path)

        assert result.exists()

    def test_annotate_image_with_highlight(self, sample_image: Path, tmp_path: Path):
        """测试高亮标注。"""
        annotations = [
            create_highlight_annotation((100, 100), (250, 200), "#FFFF00"),
        ]

        output_path = tmp_path / "annotated_highlight.jpg"
        result = annotate_image(sample_image, annotations, output_path)

        assert result.exists()

    def test_annotate_image_with_timestamp(self, sample_image: Path, tmp_path: Path):
        """测试时间戳标注。"""
        annotations = [
            create_timestamp_annotation((10, 10), "00:01:30", "#FFFFFF"),
        ]

        output_path = tmp_path / "annotated_timestamp.jpg"
        result = annotate_image(sample_image, annotations, output_path)

        assert result.exists()

    def test_annotate_image_multiple(self, sample_image: Path, tmp_path: Path):
        """测试多个标注。"""
        annotations = [
            create_text_annotation("标题", (10, 10), "#FF0000", 24),
            create_arrow_annotation((50, 50), (200, 200), "#00FF00"),
            create_rectangle_annotation((100, 100), (300, 250), "#0000FF", 2),
        ]

        output_path = tmp_path / "annotated_multi.jpg"
        result = annotate_image(sample_image, annotations, output_path)

        assert result.exists()

    def test_annotate_image_overwrite(self, sample_image: Path):
        """测试覆盖原图。"""
        annotations = [
            create_text_annotation("覆盖测试", (50, 50), "#FF0000", 20),
        ]

        # 保存原图大小
        original_size = sample_image.stat().st_size

        result = annotate_image(sample_image, annotations)

        # 文件应该被修改
        assert result == sample_image
        assert sample_image.stat().st_size != original_size


class TestAnnotateScreenshots:
    """批量截图标注测试。"""

    def test_annotate_screenshots(self, sample_image: Path, tmp_path: Path):
        """测试批量标注截图。"""
        screenshots = [
            {
                "index": 0,
                "image_path": str(sample_image),
                "timestamp_ms": 1000,
            },
            {
                "index": 1,
                "image_path": str(sample_image),
                "timestamp_ms": 2000,
            },
        ]

        annotations_map = {
            0: [create_text_annotation("第一张", (10, 10), "#FF0000", 20)],
            1: [create_text_annotation("第二张", (10, 10), "#00FF00", 20)],
        }

        result = annotate_screenshots(screenshots, annotations_map)

        assert len(result) == 2
        # 第一张应该有标注
        assert "annotations" in result[0]
        assert len(result[0]["annotations"]) == 1
        # 第二张应该有标注
        assert "annotations" in result[1]
        assert len(result[1]["annotations"]) == 1

    def test_annotate_screenshots_no_annotations(self, sample_image: Path):
        """测试无标注情况。"""
        screenshots = [
            {
                "index": 0,
                "image_path": str(sample_image),
                "timestamp_ms": 1000,
            },
        ]

        annotations_map = {}

        result = annotate_screenshots(screenshots, annotations_map)

        assert len(result) == 1
        assert "annotations" not in result[0]

    def test_annotate_screenshots_missing_image(self, tmp_path: Path):
        """测试图片不存在的情况。"""
        screenshots = [
            {
                "index": 0,
                "image_path": str(tmp_path / "nonexistent.jpg"),
                "timestamp_ms": 1000,
            },
        ]

        annotations_map = {
            0: [create_text_annotation("测试", (10, 10), "#FF0000", 20)],
        }

        result = annotate_screenshots(screenshots, annotations_map)

        assert len(result) == 1
        assert "annotations" not in result[0]


class TestLoadAnnotationsFromJson:
    """加载标注配置测试。"""

    def test_load_annotations_from_json(self, sample_annotations_json: Path):
        """测试从 JSON 加载标注配置。"""
        annotations_map = load_annotations_from_json(sample_annotations_json)

        assert 0 in annotations_map
        assert 1 in annotations_map
        assert len(annotations_map[0]) == 3
        assert len(annotations_map[1]) == 1

        # 验证第一个标注
        first_ann = annotations_map[0][0]
        assert first_ann.type == AnnotationType.TEXT
        assert first_ann.content == "重要信息"
        assert first_ann.position == (10, 10)

    def test_load_annotations_from_nonexistent_json(self, tmp_path: Path):
        """测试加载不存在的 JSON 文件。"""
        json_path = tmp_path / "nonexistent.json"
        annotations_map = load_annotations_from_json(json_path)

        assert annotations_map == {}

    def test_load_annotations_from_empty_json(self, tmp_path: Path):
        """测试加载空 JSON 文件。"""
        json_path = tmp_path / "empty.json"
        with open(json_path, "w") as f:
            json.dump({}, f)

        annotations_map = load_annotations_from_json(json_path)

        assert annotations_map == {}


class TestAnnotationConfigCustomization:
    """标注配置自定义测试。"""

    def test_custom_font_size(self, sample_image: Path, tmp_path: Path):
        """测试自定义字体大小。"""
        config = AnnotationConfig(default_font_size=30)
        annotations = [create_text_annotation("大字", (50, 50))]

        output_path = tmp_path / "custom_font_size.jpg"
        result = annotate_image(sample_image, annotations, output_path, config)

        assert result.exists()

    def test_custom_padding(self, sample_image: Path, tmp_path: Path):
        """测试自定义内边距。"""
        config = AnnotationConfig(padding=20)
        annotations = [create_text_annotation("内边距测试", (50, 50))]

        output_path = tmp_path / "custom_padding.jpg"
        result = annotate_image(sample_image, annotations, output_path, config)

        assert result.exists()

    def test_no_background(self, sample_image: Path, tmp_path: Path):
        """测试无背景文字。"""
        config = AnnotationConfig(show_background=False)
        annotations = [create_text_annotation("无背景", (50, 50))]

        output_path = tmp_path / "no_background.jpg"
        result = annotate_image(sample_image, annotations, output_path, config)

        assert result.exists()

    def test_custom_background_color(self, sample_image: Path, tmp_path: Path):
        """测试自定义背景颜色。"""
        config = AnnotationConfig(background_color="#FFFFFF80")
        annotations = [create_text_annotation("白色背景", (50, 50))]

        output_path = tmp_path / "custom_bg_color.jpg"
        result = annotate_image(sample_image, annotations, output_path, config)

        assert result.exists()
