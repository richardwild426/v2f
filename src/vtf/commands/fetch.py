from __future__ import annotations

import json

import click

from vtf._ctx import get_config, get_logger
from vtf.errors import VtfError
from vtf.pipeline.fetch import fetch


@click.command(name="fetch", help="抓取视频元数据(yt-dlp -J)")
@click.argument("url")
@click.pass_context
def cmd(ctx: click.Context, url: str) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    try:
        meta = fetch(url=url, cfg=cfg)
    except VtfError as e:
        log.error(str(e), step="fetch")
        raise SystemExit(e.exit_code) from e
    click.echo(json.dumps(meta, ensure_ascii=False))
