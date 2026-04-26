from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from vtf._ctx import get_config, get_logger
from vtf.errors import VtfError
from vtf.pipeline.analyze import analyze


@click.command(
    name="analyze",
    help="为某种 kind 生成 LLM prompt(stdin: lines.json; --meta 注入元数据)",
)
@click.option("--kind", required=True, type=click.Choice(["summary", "breakdown", "rewrite"]))
@click.option(
    "--meta",
    "meta_path",
    type=click.Path(path_type=Path, exists=True),
    required=False,
    help="meta.json 路径; 若 stdin payload 已含 meta 字段则可省略",
)
@click.pass_context
def cmd(ctx: click.Context, kind: str, meta_path: Path | None) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    payload = json.load(sys.stdin)
    meta = payload.get("meta")
    if meta is None and meta_path is not None:
        meta = json.loads(meta_path.read_text("utf-8"))
    if meta is None:
        meta = {}
    try:
        out = analyze(
            kind=kind,
            meta=meta,
            lines=payload.get("lines", []),
            cfg=cfg,
        )
    except VtfError as e:
        log.error(str(e), step="analyze")
        raise SystemExit(e.exit_code) from e
    click.echo(json.dumps(out, ensure_ascii=False))
