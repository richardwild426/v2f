from __future__ import annotations

import json
from pathlib import Path

import click

from vtf._ctx import get_config, get_logger, get_workdir
from vtf.errors import VtfError
from vtf.pipeline.download import download


@click.command(name="download", help="下载视频音频")
@click.option("--meta", "meta_path", type=click.Path(path_type=Path, exists=True), required=True)
@click.option(
    "--keep-video/--no-keep-video",
    "keep_video_flag",
    default=None,
    help="是否保留原视频文件（用于飞书附件）；未指定时按 output.sink 自动决定",
)
@click.pass_context
def cmd(ctx: click.Context, meta_path: Path, keep_video_flag: bool | None) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    meta = json.loads(meta_path.read_text("utf-8"))

    keep_video = cfg.output.sink == "feishu" if keep_video_flag is None else keep_video_flag

    try:
        audio_path, video_path = download(
            meta=meta, cfg=cfg, workdir=get_workdir(ctx), keep_video=keep_video
        )
    except VtfError as e:
        log.error(str(e), step="download")
        raise SystemExit(e.exit_code) from e

    if video_path is not None:
        meta["video_path"] = str(video_path)
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log.info(f"已保留原视频: {video_path}", step="download")

    click.echo(str(audio_path))
