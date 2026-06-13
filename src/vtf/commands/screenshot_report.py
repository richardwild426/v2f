from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from vtf._ctx import get_config
from vtf.pipeline.screenshot_report import generate_html_report, generate_json_report


@click.command(name="screenshot-report", help="为截图生成 HTML 或 JSON 报告")
@click.option("--input", "-i", "input_file", required=True, help="截图数据 JSON 文件路径（screenshot 命令输出）")
@click.option("--output", "-o", required=True, help="输出文件路径（.html 或 .json）")
@click.option("--title", "-t", default=None, help="报告标题（默认从配置读取）")
@click.option("--embed-images", is_flag=True, default=None, help="将图片嵌入 HTML（base64）")
@click.pass_context
def cmd(
    ctx: click.Context,
    input_file: str,
    output: str,
    title: str | None,
    embed_images: bool | None,
) -> None:
    """为截图生成 HTML 或 JSON 报告"""
    cfg = get_config(ctx)
    
    # 从配置中读取默认值
    screenshot_cfg = getattr(cfg, "screenshot", None)
    if title is None:
        title = getattr(screenshot_cfg, "report_title", "视频截图报告") if screenshot_cfg else "视频截图报告"
    if embed_images is None:
        embed_images = getattr(screenshot_cfg, "report_embed_images", False) if screenshot_cfg else False

    # 读取截图数据
    try:
        with open(input_file, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        click.echo(f"错误：读取截图数据失败：{e}", err=True)
        sys.exit(1)

    screenshots = data.get("screenshots", [])
    if not screenshots:
        click.echo("警告：没有找到截图数据", err=True)
        sys.exit(1)

    output_path = Path(output)
    
    # 根据输出文件扩展名选择格式
    if output_path.suffix.lower() == ".html":
        # 生成 HTML 报告
        html = generate_html_report(
            screenshots=screenshots,
            title=title,
            embed_images=embed_images,
            output_path=output_path,
        )
        click.echo(f"HTML 报告已生成：{output_path}")
        click.echo(f"包含 {len(screenshots)} 张截图")
    elif output_path.suffix.lower() == ".json":
        # 生成 JSON 报告
        report = generate_json_report(
            screenshots=screenshots,
            output_path=output_path,
        )
        click.echo(f"JSON 报告已生成：{output_path}")
        click.echo(f"包含 {report['total_count']} 张截图")
    else:
        click.echo(f"错误：不支持的输出格式：{output_path.suffix}", err=True)
        click.echo("支持格式：.html, .json", err=True)
        sys.exit(1)


__all__ = ["cmd"]