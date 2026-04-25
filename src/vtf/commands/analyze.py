from __future__ import annotations

import json
import sys

import click

from vtf._ctx import get_config, get_logger
from vtf.errors import VtfError
from vtf.pipeline.analyze import analyze


@click.command(name="analyze", help="为某种 kind 生成 LLM prompt(stdin: {meta, lines})")
@click.option("--kind", required=True, type=click.Choice(["summary", "breakdown", "rewrite"]))
@click.pass_context
def cmd(ctx: click.Context, kind: str) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    payload = json.load(sys.stdin)
    try:
        out = analyze(
            kind=kind,
            meta=payload.get("meta", {}),
            lines=payload.get("lines", []),
            cfg=cfg,
        )
    except VtfError as e:
        log.error(str(e), step="analyze")
        raise SystemExit(e.exit_code) from e
    click.echo(json.dumps(out, ensure_ascii=False))
