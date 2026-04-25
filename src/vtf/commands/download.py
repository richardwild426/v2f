from __future__ import annotations

import json
from pathlib import Path

import click

from vtf._ctx import get_config, get_logger, get_workdir
from vtf.errors import VtfError
from vtf.pipeline.download import download


@click.command(name="download", help="下载视频音频")
@click.option("--meta", "meta_path", type=click.Path(path_type=Path, exists=True), required=True)
@click.pass_context
def cmd(ctx: click.Context, meta_path: Path) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    meta = json.loads(meta_path.read_text("utf-8"))
    try:
        out = download(meta=meta, cfg=cfg, workdir=get_workdir(ctx))
    except VtfError as e:
        log.error(str(e), step="download")
        raise SystemExit(e.exit_code) from e
    click.echo(str(out))
