from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from vtf._ctx import get_config
from vtf.pipeline.screenshot import take_screenshots, take_scene_screenshots, take_screenshots_with_description


@click.command(name="screenshot", help="根据字幕时间戳截取视频帧")
@click.option("--video", "-v", required=True, help="视频文件路径")
@click.option("--subtitles", "-s", required=True, help="字幕 JSON 文件路径")
@click.option("--output", "-o", default="screenshots", help="输出目录")
@click.option("--mode", "-m", type=click.Choice(["subtitle", "scene", "auto"]), default="auto", help="截图模式")
@click.option("--ai-describe", is_flag=True, default=False, help="启用 AI 描述生成（生成 prompt 供 LLM 填充）")
@click.option("--llm-provider", type=click.Choice(["openai", "anthropic", ""]), default="", help="LLM 提供商（直接调用模式）")
@click.option("--llm-model", default="", help="LLM 模型名称")
@click.option("--llm-api-key", default="", help="LLM API 密钥（或设置环境变量 VTF_SCREENSHOT_LLM_API_KEY）")
@click.option("--llm-base-url", default="", help="LLM 自定义端点 URL")
@click.option("--max-workers", default=4, help="并行处理线程数")
@click.option("--cache-dir", default=".cache/vtf", help="缓存目录")
@click.option("--use-cache/--no-cache", default=True, help="是否使用缓存")
@click.pass_context
def cmd(
    ctx: click.Context,
    video: str,
    subtitles: str,
    output: str,
    mode: str,
    ai_describe: bool,
    llm_provider: str,
    llm_model: str,
    llm_api_key: str,
    llm_base_url: str,
    max_workers: int,
    cache_dir: str,
    use_cache: bool,
) -> None:
    """根据字幕时间戳截取视频帧"""
    cfg = get_config(ctx)

    video_path = Path(video)
    if not video_path.exists():
        click.echo(f"错误：视频文件不存在：{video}", err=True)
        sys.exit(1)

    # 读取字幕数据
    try:
        with open(subtitles, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        click.echo(f"错误：读取字幕文件失败：{e}", err=True)
        sys.exit(1)

    # 提取字幕行
    lines = data.get("lines", [])
    if not lines:
        click.echo("警告：没有找到字幕数据", err=True)
        sys.exit(1)

    # 更新配置
    if not hasattr(cfg, "screenshot"):
        cfg.screenshot = type("ScreenshotConfig", (), {
            "output_dir": output,
            "ffmpeg_path": "ffmpeg",
            "scene_threshold": 0.3,
            "min_interval_seconds": 2,
            "similarity_threshold": 0.95,
            "ai_describe": ai_describe,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "llm_api_key": llm_api_key or os.environ.get("VTF_SCREENSHOT_LLM_API_KEY", ""),
            "llm_base_url": llm_base_url,
            "llm_max_tokens": 300,
            "max_workers": max_workers,
            "cache_dir": cache_dir,
            "use_cache": use_cache,
        })()
    else:
        cfg.screenshot.output_dir = output
        cfg.screenshot.ai_describe = ai_describe
        if llm_provider:
            cfg.screenshot.llm_provider = llm_provider
        if llm_model:
            cfg.screenshot.llm_model = llm_model
        if llm_api_key:
            cfg.screenshot.llm_api_key = llm_api_key
        elif not cfg.screenshot.llm_api_key:
            cfg.screenshot.llm_api_key = os.environ.get("VTF_SCREENSHOT_LLM_API_KEY", "")
        if llm_base_url:
            cfg.screenshot.llm_base_url = llm_base_url
        cfg.screenshot.max_workers = max_workers
        cfg.screenshot.cache_dir = cache_dir
        cfg.screenshot.use_cache = use_cache

    # 初始化缓存
    if use_cache:
        from vtf.cache import HashCache
        cache = HashCache(cache_dir)
    
    # 根据模式执行截图
    screenshots = []
    if mode == "subtitle":
        if ai_describe or llm_provider:
            screenshots = take_screenshots_with_description(
                video_path=video_path, lines=lines, cfg=cfg
            )
        else:
            screenshots = take_screenshots(video_path=video_path, lines=lines, cfg=cfg)
    elif mode == "scene":
        screenshots = take_scene_screenshots(video_path=video_path, cfg=cfg)
    else:  # auto
        if ai_describe or llm_provider:
            screenshots = take_screenshots_with_description(
                video_path=video_path, lines=lines, cfg=cfg
            )
        else:
            screenshots = take_screenshots(video_path=video_path, lines=lines, cfg=cfg)
        if not screenshots:
            click.echo("字幕截图失败，尝试场景变化检测...", err=True)
            screenshots = take_scene_screenshots(video_path=video_path, cfg=cfg)

    # 输出结果
    result = {
        "meta": {
            "video_id": video_path.stem,
            "title": video_path.stem,
        },
        "screenshots": screenshots,
        "total": len(screenshots),
    }

    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


__all__ = ["cmd"]
