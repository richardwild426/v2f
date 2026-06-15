"""截图标注命令。

在截图上添加文字、箭头、高亮等标注。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from vtf.pipeline.screenshot_annotate import (
    Annotation,
    AnnotationConfig,
    AnnotationType,
    annotate_screenshots,
    load_annotations_from_json,
)


@click.command(name="screenshot-annotate", help="为截图添加标注（文字、箭头、高亮等）")
@click.option("--input", "-i", "input_json", required=True, help="截图 JSON 文件路径（screenshot 命令的输出）")
@click.option("--annotations", "-a", "annotations_json", required=True, help="标注配置 JSON 文件路径")
@click.option("--output", "-o", default=None, help="输出 JSON 文件路径（默认覆盖输入文件）")
@click.option("--font", default=None, help="自定义字体文件路径")
@click.option("--font-size", default=20, help="默认字体大小")
@click.option("--color", default="#FF0000", help="默认标注颜色")
@click.option("--opacity", default=1.0, type=click.FloatRange(0.0, 1.0), help="默认透明度 (0-1)")
@click.option("--padding", default=10, help="文字内边距")
@click.option("--no-background", is_flag=True, help="不显示文字背景")
@click.option("--background-color", default="#00000080", help="文字背景颜色")
@click.pass_context
def cmd(
    ctx: click.Context,
    input_json: str,
    annotations_json: str,
    output: str | None,
    font: str | None,
    font_size: int,
    color: str,
    opacity: float,
    padding: int,
    no_background: bool,
    background_color: str,
) -> None:
    """为截图添加标注"""
    input_path = Path(input_json)
    annotations_path = Path(annotations_json)

    # 验证输入文件
    if not input_path.exists():
        click.echo(f"错误：输入文件不存在：{input_json}", err=True)
        sys.exit(1)

    if not annotations_path.exists():
        click.echo(f"错误：标注配置文件不存在：{annotations_json}", err=True)
        sys.exit(1)

    # 读取截图数据
    try:
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        click.echo(f"错误：读取截图文件失败：{e}", err=True)
        sys.exit(1)

    screenshots = data.get("screenshots", [])
    if not screenshots:
        click.echo("警告：没有找到截图数据", err=True)
        sys.exit(1)

    # 加载标注配置
    annotations_map = load_annotations_from_json(annotations_path)

    if not annotations_map:
        click.echo("警告：没有找到标注配置", err=True)
        sys.exit(1)

    # 创建标注配置
    config = AnnotationConfig(
        font_path=font,
        default_font_size=font_size,
        default_color=color,
        default_opacity=opacity,
        padding=padding,
        show_background=not no_background,
        background_color=background_color,
    )

    # 执行标注
    click.echo(f"正在为 {len(screenshots)} 张截图添加标注...", err=True)

    try:
        annotated_screenshots = annotate_screenshots(screenshots, annotations_map, config)
    except ImportError as e:
        click.echo(f"错误：{e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"错误：标注失败：{e}", err=True)
        sys.exit(1)

    # 更新数据
    data["screenshots"] = annotated_screenshots

    # 输出结果
    output_path = Path(output) if output else input_path
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    click.echo(f"标注完成，结果已保存到：{output_path}", err=True)
    click.echo(json.dumps(data, ensure_ascii=False, indent=2))


__all__ = ["cmd"]
