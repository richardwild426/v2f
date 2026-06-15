"""截图标注功能模块。

支持在截图上添加文字、箭头、高亮等标注，增强截图的可读性和信息量。

功能：
- 文字标注：在指定位置添加文字说明
- 箭头标注：绘制箭头指向特定区域
- 高亮标注：高亮显示重要区域
- 矩形标注：绘制矩形框标注区域
- 时间戳标注：在截图上显示时间信息

依赖：
- Pillow (PIL)：图像处理
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class AnnotationType(str, Enum):
    """标注类型枚举。"""
    TEXT = "text"
    ARROW = "arrow"
    RECTANGLE = "rectangle"
    HIGHLIGHT = "highlight"
    TIMESTAMP = "timestamp"


@dataclass
class Annotation:
    """标注数据类。"""
    type: AnnotationType
    position: tuple[int, int]  # (x, y) 坐标
    content: str = ""  # 文字内容或描述
    color: str = "#FF0000"  # 颜色 (十六进制)
    size: int = 20  # 字体大小或线宽
    end_position: tuple[int, int] | None = None  # 箭头终点或矩形对角点
    opacity: float = 1.0  # 透明度 (0-1)
    style: str = "solid"  # 样式: solid, dashed, dotted
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnnotationConfig:
    """标注配置。"""
    font_path: str | None = None  # 自定义字体路径
    default_font_size: int = 20
    default_color: str = "#FF0000"
    default_opacity: float = 1.0
    padding: int = 10  # 文字内边距
    background_color: str = "#00000080"  # 文字背景色
    show_background: bool = True  # 是否显示文字背景
    timestamp_format: str = "%H:%M:%S"  # 时间戳格式


def hex_to_rgba(hex_color: str, opacity: float = 1.0) -> tuple[int, int, int, int]:
    """将十六进制颜色转换为 RGBA 元组。

    Args:
        hex_color: 十六进制颜色字符串 (#RRGGBB 或 #RRGGBBAA)
        opacity: 透明度 (0-1)

    Returns:
        RGBA 颜色元组
    """
    hex_color = hex_color.lstrip("#")

    if len(hex_color) == 6:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        a = int(opacity * 255)
    elif len(hex_color) == 8:
        r, g, b, a = (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
            int(hex_color[6:8], 16),
        )
        a = int(a * opacity)
    else:
        raise ValueError(f"Invalid hex color: {hex_color}")

    return (r, g, b, a)


def load_font(
    font_path: str | None = None,
    size: int = 20,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """加载字体。

    Args:
        font_path: 字体文件路径，None 则使用默认字体
        size: 字体大小

    Returns:
        字体对象
    """
    if font_path and Path(font_path).exists():
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    # 尝试加载系统字体
    system_fonts = [
        "/System/Library/Fonts/PingFang.ttc",  # macOS
        "/System/Library/Fonts/STHeiti Light.ttc",  # macOS 中文
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "C:/Windows/Fonts/msyh.ttc",  # Windows
    ]

    for sys_font in system_fonts:
        try:
            return ImageFont.truetype(sys_font, size)
        except (OSError, IOError):
            continue

    # 回退到默认字体
    try:
        return ImageFont.truetype("arial.ttf", size)
    except (OSError, IOError):
        return ImageFont.load_default()


def annotate_image(
    image_path: Path | str,
    annotations: Sequence[Annotation],
    output_path: Path | str | None = None,
    config: AnnotationConfig | None = None,
) -> Path:
    """在图片上添加标注。

    Args:
        image_path: 输入图片路径
        annotations: 标注列表
        output_path: 输出路径，None 则覆盖原图
        config: 标注配置

    Returns:
        输出图片路径
    """
    if not HAS_PIL:
        raise ImportError("Pillow is required for annotation. Install with: pip install Pillow")

    config = config or AnnotationConfig()
    image_path = Path(image_path)
    output_path = Path(output_path) if output_path else image_path

    # 打开图片
    img = Image.open(image_path)
    
    # 转换为 RGBA 以支持透明度
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # 创建绘图层
    draw = ImageDraw.Draw(img, "RGBA")

    # 加载字体
    font = load_font(config.font_path, config.default_font_size)

    # 绘制每个标注
    for annotation in annotations:
        _draw_annotation(draw, img, annotation, config, font)

    # 保存图片
    if output_path.suffix.lower() in (".jpg", ".jpeg"):
        # JPEG 不支持透明度，转换为 RGB
        img = img.convert("RGB")
    
    img.save(output_path, quality=95)
    return output_path


def _draw_annotation(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    annotation: Annotation,
    config: AnnotationConfig,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """绘制单个标注。"""
    color = hex_to_rgba(annotation.color, annotation.opacity)

    if annotation.type == AnnotationType.TEXT:
        _draw_text(draw, img, annotation, config, font, color)
    elif annotation.type == AnnotationType.ARROW:
        _draw_arrow(draw, annotation, color)
    elif annotation.type == AnnotationType.RECTANGLE:
        _draw_rectangle(draw, annotation, color)
    elif annotation.type == AnnotationType.HIGHLIGHT:
        _draw_highlight(draw, img, annotation, color)
    elif annotation.type == AnnotationType.TIMESTAMP:
        _draw_timestamp(draw, img, annotation, config, font, color)


def _draw_text(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    annotation: Annotation,
    config: AnnotationConfig,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: tuple[int, int, int, int],
) -> None:
    """绘制文字标注。"""
    x, y = annotation.position
    text = annotation.content

    if not text:
        return

    # 获取文字大小
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # 绘制背景
    if config.show_background:
        bg_color = hex_to_rgba(config.background_color, annotation.opacity * 0.8)
        padding = config.padding
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=bg_color,
        )

    # 绘制文字
    draw.text((x, y), text, fill=color, font=font)


def _draw_arrow(
    draw: ImageDraw.ImageDraw,
    annotation: Annotation,
    color: tuple[int, int, int, int],
) -> None:
    """绘制箭头标注。"""
    if not annotation.end_position:
        return

    start = annotation.position
    end = annotation.end_position
    line_width = max(2, annotation.size // 10)

    # 绘制主线
    draw.line([start, end], fill=color, width=line_width)

    # 计算箭头
    import math
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle = math.atan2(dy, dx)
    arrow_length = max(15, annotation.size)
    arrow_angle = math.pi / 6  # 30 度

    # 箭头两个点
    arrow_x1 = end[0] - arrow_length * math.cos(angle - arrow_angle)
    arrow_y1 = end[1] - arrow_length * math.sin(angle - arrow_angle)
    arrow_x2 = end[0] - arrow_length * math.cos(angle + arrow_angle)
    arrow_y2 = end[1] - arrow_length * math.sin(angle + arrow_angle)

    # 绘制箭头
    draw.polygon([end, (int(arrow_x1), int(arrow_y1)), (int(arrow_x2), int(arrow_y2))], fill=color)


def _draw_rectangle(
    draw: ImageDraw.ImageDraw,
    annotation: Annotation,
    color: tuple[int, int, int, int],
) -> None:
    """绘制矩形标注。"""
    if not annotation.end_position:
        return

    start = annotation.position
    end = annotation.end_position
    line_width = max(2, annotation.size // 10)

    draw.rectangle([start, end], outline=color, width=line_width)


def _draw_highlight(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    annotation: Annotation,
    color: tuple[int, int, int, int],
) -> None:
    """绘制高亮标注（半透明填充）。"""
    if not annotation.end_position:
        return

    start = annotation.position
    end = annotation.end_position

    # 使用半透明颜色填充
    highlight_color = (color[0], color[1], color[2], int(color[3] * 0.3))
    draw.rectangle([start, end], fill=highlight_color)


def _draw_timestamp(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    annotation: Annotation,
    config: AnnotationConfig,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: tuple[int, int, int, int],
) -> None:
    """绘制时间戳标注。"""
    import time

    x, y = annotation.position
    timestamp_str = annotation.content or time.strftime(config.timestamp_format)

    # 使用较小的字体
    small_font_size = max(12, config.default_font_size - 4)
    small_font = load_font(config.font_path, small_font_size)

    # 获取文字大小
    bbox = small_font.getbbox(timestamp_str)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # 绘制背景
    if config.show_background:
        bg_color = hex_to_rgba("#000000", 0.7)
        padding = 5
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=bg_color,
        )

    # 绘制时间戳文字
    draw.text((x, y), timestamp_str, fill=color, font=small_font)


def annotate_screenshots(
    screenshots: list[dict[str, Any]],
    annotations_map: dict[int, list[Annotation]],
    config: AnnotationConfig | None = None,
) -> list[dict[str, Any]]:
    """批量为截图添加标注。

    Args:
        screenshots: 截图信息列表
        annotations_map: 标注映射 {截图索引: 标注列表}
        config: 标注配置

    Returns:
        更新后的截图信息列表
    """
    config = config or AnnotationConfig()
    result = []

    for screenshot in screenshots:
        index = screenshot.get("index", 0)
        image_path = Path(screenshot.get("image_path", ""))

        if not image_path.exists():
            result.append(screenshot)
            continue

        # 获取该截图的标注
        annotations = annotations_map.get(index, [])

        if annotations:
            # 添加标注
            output_path = image_path.parent / f"{image_path.stem}_annotated{image_path.suffix}"
            annotate_image(image_path, annotations, output_path, config)

            # 更新截图信息
            screenshot = screenshot.copy()
            screenshot["image_path"] = str(output_path)
            screenshot["annotations"] = [
                {
                    "type": a.type.value,
                    "position": a.position,
                    "content": a.content,
                    "color": a.color,
                }
                for a in annotations
            ]

        result.append(screenshot)

    return result


def create_text_annotation(
    text: str,
    position: tuple[int, int],
    color: str = "#FF0000",
    size: int = 20,
) -> Annotation:
    """创建文字标注的便捷函数。

    Args:
        text: 标注文字
        position: 位置 (x, y)
        color: 颜色
        size: 字体大小

    Returns:
        Annotation 对象
    """
    return Annotation(
        type=AnnotationType.TEXT,
        position=position,
        content=text,
        color=color,
        size=size,
    )


def create_arrow_annotation(
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = "#FF0000",
    size: int = 20,
) -> Annotation:
    """创建箭头标注的便捷函数。

    Args:
        start: 起点 (x, y)
        end: 终点 (x, y)
        color: 颜色
        size: 大小

    Returns:
        Annotation 对象
    """
    return Annotation(
        type=AnnotationType.ARROW,
        position=start,
        end_position=end,
        color=color,
        size=size,
    )


def create_rectangle_annotation(
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    color: str = "#FF0000",
    size: int = 20,
) -> Annotation:
    """创建矩形标注的便捷函数。

    Args:
        top_left: 左上角 (x, y)
        bottom_right: 右下角 (x, y)
        color: 颜色
        size: 线宽

    Returns:
        Annotation 对象
    """
    return Annotation(
        type=AnnotationType.RECTANGLE,
        position=top_left,
        end_position=bottom_right,
        color=color,
        size=size,
    )


def create_highlight_annotation(
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    color: str = "#FFFF00",
) -> Annotation:
    """创建高亮标注的便捷函数。

    Args:
        top_left: 左上角 (x, y)
        bottom_right: 右下角 (x, y)
        color: 颜色

    Returns:
        Annotation 对象
    """
    return Annotation(
        type=AnnotationType.HIGHLIGHT,
        position=top_left,
        end_position=bottom_right,
        color=color,
    )


def create_timestamp_annotation(
    position: tuple[int, int],
    timestamp: str = "",
    color: str = "#FFFFFF",
) -> Annotation:
    """创建时间戳标注的便捷函数。

    Args:
        position: 位置 (x, y)
        timestamp: 时间戳字符串，空则使用当前时间
        color: 颜色

    Returns:
        Annotation 对象
    """
    return Annotation(
        type=AnnotationType.TIMESTAMP,
        position=position,
        content=timestamp,
        color=color,
    )


def load_annotations_from_json(json_path: Path | str) -> dict[int, list[Annotation]]:
    """从 JSON 文件加载标注配置。

    JSON 格式：
    {
        "0": [  // 截图索引
            {
                "type": "text",
                "position": [100, 100],
                "content": "重要信息",
                "color": "#FF0000",
                "size": 24
            },
            {
                "type": "arrow",
                "position": [50, 50],
                "end_position": [200, 200],
                "color": "#00FF00"
            }
        ]
    }

    Args:
        json_path: JSON 文件路径

    Returns:
        标注映射
    """
    json_path = Path(json_path)
    if not json_path.exists():
        return {}

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    annotations_map: dict[int, list[Annotation]] = {}

    for index_str, annotations_data in data.items():
        index = int(index_str)
        annotations = []

        for ann_data in annotations_data:
            ann_type = AnnotationType(ann_data.get("type", "text"))
            position = tuple(ann_data.get("position", [0, 0]))
            end_position = tuple(ann_data.get("end_position")) if "end_position" in ann_data else None

            annotation = Annotation(
                type=ann_type,
                position=position,
                content=ann_data.get("content", ""),
                color=ann_data.get("color", "#FF0000"),
                size=ann_data.get("size", 20),
                end_position=end_position,
                opacity=ann_data.get("opacity", 1.0),
            )
            annotations.append(annotation)

        annotations_map[index] = annotations

    return annotations_map


__all__ = [
    "AnnotationType",
    "Annotation",
    "AnnotationConfig",
    "annotate_image",
    "annotate_screenshots",
    "create_text_annotation",
    "create_arrow_annotation",
    "create_rectangle_annotation",
    "create_highlight_annotation",
    "create_timestamp_annotation",
    "load_annotations_from_json",
]
