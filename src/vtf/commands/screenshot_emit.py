"""将 screenshots.json 中的截图批量写入飞书截图表，并可选生成报告。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from vtf._ctx import get_config, get_logger
from vtf.errors import UserError, VtfError
from vtf.sinks.feishu import Feishu


@click.command(
    name="screenshot-emit",
    help="将 screenshots.json 中的截图记录批量写入飞书截图专用表",
)
@click.option(
    "--input", "-i",
    "input_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="screenshots.json 路径（默认从 workdir 自动查找）",
)
@click.option(
    "--report",
    "report_path",
    type=click.Path(path_type=Path),
    default=None,
    help="生成报告文件路径（.html 或 .json），不指定则跳过",
)
@click.option(
    "--report-title",
    default=None,
    help="报告标题（默认从配置读取）",
)
@click.option(
    "--embed-images",
    is_flag=True,
    default=False,
    help="将图片嵌入 HTML 报告（base64）",
)
@click.pass_context
def cmd(
    ctx: click.Context,
    input_path: Path | None,
    report_path: Path | None,
    report_title: str | None,
    embed_images: bool,
) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)

    # 查找 screenshots.json
    if input_path is None:
        from vtf._ctx import get_workdir
        workdir = get_workdir(ctx)
        input_path = workdir / "screenshots.json"
        if not input_path.exists():
            raise UserError(
                f"找不到 screenshots.json: {input_path}\n"
                "请先运行 `vtf screenshot` 或 `vtf run <url>` 生成截图，"
                "或用 --input 指定文件路径。"
            )

    data = json.loads(input_path.read_text("utf-8"))

    # 兼容两种格式：直接列表 或 {"screenshots": [...]}
    if isinstance(data, list):
        screenshots = data
        meta: dict = {}
    elif isinstance(data, dict):
        screenshots = data.get("screenshots", [])
        meta = data.get("meta", {})
    else:
        raise UserError(f"无法解析 screenshots 文件: {input_path}")

    if not screenshots:
        click.echo("没有截图数据，跳过。", err=True)
        return

    f = cfg.sink.feishu
    if not f.screenshot_table_id:
        raise UserError(
            "未配置 screenshot_table_id。\n"
            "请在 config.toml 中添加:\n"
            "  [sink.feishu]\n"
            '  screenshot_table_id = "你的截图表ID"'
        )

    if not f.base_token:
        raise UserError(
            "未配置 base_token。请运行 `vtf init feishu` 或手动配置。"
        )

    sink = Feishu()
    try:
        outcome = sink.emit_screenshots(screenshots, meta, cfg)
        click.echo(outcome.reason, err=True)
    except VtfError as e:
        log.error(str(e), step="screenshot-emit")
        raise SystemExit(e.exit_code) from e

    # 可选：生成报告
    if report_path:
        from vtf.pipeline.screenshot_report import generate_html_report, generate_json_report

        screenshot_cfg = getattr(cfg, "screenshot", None)
        title = report_title or (
            getattr(screenshot_cfg, "report_title", "视频截图报告")
            if screenshot_cfg else "视频截图报告"
        )

        if report_path.suffix.lower() == ".html":
            generate_html_report(
                screenshots=screenshots,
                title=title,
                embed_images=embed_images,
                output_path=report_path,
            )
            click.echo(f"HTML 报告已生成: {report_path}", err=True)
        elif report_path.suffix.lower() == ".json":
            generate_json_report(
                screenshots=screenshots,
                output_path=report_path,
            )
            click.echo(f"JSON 报告已生成: {report_path}", err=True)
        else:
            click.echo(f"不支持的报告格式: {report_path.suffix}，跳过报告生成", err=True)
