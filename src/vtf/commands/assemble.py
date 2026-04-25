from __future__ import annotations

import json
from pathlib import Path

import click

from vtf._ctx import get_logger
from vtf.errors import VtfError
from vtf.pipeline.assemble import assemble


@click.command(name="assemble", help="拼装最终 result.json")
@click.option("--meta", "meta_path", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--lines", "lines_path", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--analysis", "analyses", multiple=True, type=click.Path(path_type=Path, exists=True))
@click.pass_context
def cmd(ctx: click.Context, meta_path: Path, lines_path: Path, analyses: tuple[Path, ...]) -> None:
    log = get_logger(ctx)
    meta = json.loads(meta_path.read_text("utf-8"))
    lines_data = json.loads(lines_path.read_text("utf-8"))
    items = [json.loads(p.read_text("utf-8")) for p in analyses]
    try:
        out = assemble(meta=meta, lines=lines_data["lines"], analyses=items)
    except VtfError as e:
        log.error(str(e), step="assemble")
        raise SystemExit(e.exit_code) from e
    click.echo(json.dumps(out, ensure_ascii=False))
