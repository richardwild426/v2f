from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from vtf._ctx import get_config
from vtf.pipeline.screenshot import (
    ProgressCallback,
    take_scene_screenshots,
    take_screenshots,
    take_screenshots_with_description,
)


def _make_progress_callback(bar: click.Progressbar) -> ProgressCallback:
    """创建进度回调函数，将进度更新到 click.progressbar。"""
    def callback(current: int, total: int, message: str = "") -> None:
        if total > 0:
            bar.length = total
            bar.update(current - bar.pos)
            if message:
                bar.label = message
    return callback


def _find_subtitle_file(video_path: Path, subtitles_dir: Path | None = None) -> Path | None:
    """查找视频对应的字幕文件。

    查找策略：
    1. 同目录下同名 .json 文件
    2. 指定的字幕目录下同名 .json 文件
    """
    # 同目录下同名 .json
    candidate = video_path.with_suffix(".json")
    if candidate.exists():
        return candidate

    # 字幕目录下同名 .json
    if subtitles_dir:
        candidate = subtitles_dir / video_path.with_suffix(".json").name
        if candidate.exists():
            return candidate

    return None


@click.command(name="screenshot-batch", help="批量处理多个视频的截图")
@click.option("--videos", "-v", multiple=True, required=True, help="视频文件路径（可多次指定）")
@click.option("--videos-dir", default=None, help="视频目录（自动查找所有视频文件）")
@click.option("--subtitles-dir", "-s", default=None, help="字幕目录（与视频同名的 .json 文件）")
@click.option("--output", "-o", default="screenshots", help="输出根目录")
@click.option("--mode", "-m", type=click.Choice(["subtitle", "scene", "auto"]), default="auto", help="截图模式")
@click.option("--quality", "-q", default=2, type=click.IntRange(1, 31), help="截图质量（1-31，越小质量越高）")
@click.option("--width", default=0, help="输出宽度（0 表示保持原始比例）")
@click.option("--height", default=0, help="输出高度（0 表示保持原始比例）")
@click.option("--scale", default=1.0, type=click.FloatRange(0.1, 10.0), help="缩放比例（0.5 表示缩小一半）")
@click.option("--ai-describe", is_flag=True, default=False, help="启用 AI 描述生成")
@click.option("--llm-provider", type=click.Choice(["openai", "anthropic", ""]), default="", help="LLM 提供商")
@click.option("--llm-model", default="", help="LLM 模型名称")
@click.option("--llm-api-key", default="", help="LLM API 密钥")
@click.option("--llm-base-url", default="", help="LLM 自定义端点 URL")
@click.option("--max-workers", default=4, help="并行处理线程数")
@click.option("--cache-dir", default=".cache/vtf", help="缓存目录")
@click.option("--use-cache/--no-cache", default=True, help="是否使用缓存")
@click.option("--progress/--no-progress", default=True, help="是否显示进度条")
@click.option("--video-extensions", default="mp4,mkv,avi,webm", help="视频文件扩展名（逗号分隔）")
@click.pass_context
def cmd(
    ctx: click.Context,
    videos: tuple[str, ...],
    videos_dir: str | None,
    subtitles_dir: str | None,
    output: str,
    mode: str,
    quality: int,
    width: int,
    height: int,
    scale: float,
    ai_describe: bool,
    llm_provider: str,
    llm_model: str,
    llm_api_key: str,
    llm_base_url: str,
    max_workers: int,
    cache_dir: str,
    use_cache: bool,
    progress: bool,
    video_extensions: str,
) -> None:
    """批量处理多个视频的截图"""
    cfg = get_config(ctx)

    # 收集所有视频文件
    video_paths: list[Path] = []
    extensions = {f".{ext.strip()}" for ext in video_extensions.split(",")}

    # 从 --videos 参数
    for v in videos:
        p = Path(v)
        if p.exists() and p.suffix.lower() in extensions:
            video_paths.append(p)
        elif p.exists():
            click.echo(f"警告：跳过不支持的文件格式：{v}", err=True)
        else:
            click.echo(f"警告：视频文件不存在：{v}", err=True)

    # 从 --videos-dir 目录
    if videos_dir:
        vdir = Path(videos_dir)
        if vdir.is_dir():
            for f in sorted(vdir.iterdir()):
                if f.suffix.lower() in extensions and f not in video_paths:
                    video_paths.append(f)
        else:
            click.echo(f"错误：视频目录不存在：{videos_dir}", err=True)
            sys.exit(1)

    if not video_paths:
        click.echo("错误：没有找到视频文件", err=True)
        sys.exit(1)

    click.echo(f"找到 {len(video_paths)} 个视频文件", err=True)

    # 更新配置
    if not hasattr(cfg, "screenshot"):
        cfg.screenshot = type("ScreenshotConfig", (), {
            "output_dir": output,
            "ffmpeg_path": "ffmpeg",
            "scene_threshold": 0.3,
            "min_interval_seconds": 2,
            "similarity_threshold": 0.95,
            "quality": quality,
            "width": width,
            "height": height,
            "scale": scale,
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
        cfg.screenshot.quality = quality
        cfg.screenshot.width = width
        cfg.screenshot.height = height
        cfg.screenshot.scale = scale
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

    # 创建进度回调
    progress_callback: ProgressCallback | None = None
    if progress and sys.stderr.isatty():
        bar = click.progressbar(
            length=len(video_paths),
            label="处理视频...",
            show_pos=True,
            show_percent=True,
        )
        progress_callback = _make_progress_callback(bar)

    # 处理每个视频
    all_results: list[dict] = []
    subtitles_path = Path(subtitles_dir) if subtitles_dir else None

    for i, video_path in enumerate(video_paths):
        click.echo(f"\n处理视频 {i + 1}/{len(video_paths)}: {video_path.name}", err=True)

        # 查找字幕文件
        subtitle_file = _find_subtitle_file(video_path, subtitles_path)
        lines: list[dict] = []

        if subtitle_file:
            try:
                with open(subtitle_file, encoding="utf-8") as f:
                    data = json.load(f)
                lines = data.get("lines", [])
            except (json.JSONDecodeError, OSError) as e:
                click.echo(f"警告：读取字幕文件失败：{e}", err=True)

        # 为每个视频创建独立的输出目录
        video_output = Path(output) / video_path.stem
        cfg.screenshot.output_dir = str(video_output)

        # 执行截图
        screenshots: list[dict] = []
        if mode == "subtitle":
            if not lines:
                click.echo(f"警告：{video_path.name} 没有字幕数据，跳过", err=True)
                continue
            if ai_describe or llm_provider:
                screenshots = take_screenshots_with_description(
                    video_path=video_path, lines=lines, cfg=cfg,
                    progress_callback=progress_callback,
                )
            else:
                screenshots = take_screenshots(
                    video_path=video_path, lines=lines, cfg=cfg,
                    progress_callback=progress_callback,
                )
        elif mode == "scene":
            screenshots = take_scene_screenshots(
                video_path=video_path, cfg=cfg,
                progress_callback=progress_callback,
            )
        else:  # auto
            if lines:
                if ai_describe or llm_provider:
                    screenshots = take_screenshots_with_description(
                        video_path=video_path, lines=lines, cfg=cfg,
                        progress_callback=progress_callback,
                    )
                else:
                    screenshots = take_screenshots(
                        video_path=video_path, lines=lines, cfg=cfg,
                        progress_callback=progress_callback,
                    )
            if not screenshots:
                click.echo(f"字幕截图失败，尝试场景变化检测...", err=True)
                screenshots = take_scene_screenshots(
                    video_path=video_path, cfg=cfg,
                    progress_callback=progress_callback,
                )

        # 保存单个视频结果
        video_result = {
            "meta": {
                "video_id": video_path.stem,
                "title": video_path.stem,
                "video_path": str(video_path),
            },
            "screenshots": screenshots,
            "total": len(screenshots),
        }

        # 保存到视频目录
        result_file = video_output / "screenshots.json"
        video_output.mkdir(parents=True, exist_ok=True)
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(video_result, ensure_ascii=False, indent=2, fp=f)

        click.echo(f"  截图 {len(screenshots)} 张，结果保存到 {result_file}", err=True)
        all_results.append(video_result)

    # 关闭进度条
    if progress_callback and progress and sys.stderr.isatty():
        bar.finish()

    # 输出汇总结果
    summary = {
        "total_videos": len(video_paths),
        "total_screenshots": sum(r["total"] for r in all_results),
        "videos": [
            {
                "video_id": r["meta"]["video_id"],
                "screenshots": r["total"],
            }
            for r in all_results
        ],
    }

    click.echo(json.dumps(summary, ensure_ascii=False, indent=2))


__all__ = ["cmd"]
