from __future__ import annotations

from pathlib import Path

import click

from vtf._ctx import get_config, get_logger, get_workdir
from vtf.commands.assemble import collect_and_assemble
from vtf.commands.emit import _report_outcome, run_sink
from vtf.errors import VtfError


@click.command(
    name="finish",
    help="LLM 回填 result 后一步收尾：装配 result.json 并写入当前 sink"
    "（= assemble + emit）。",
)
@click.option("--meta", "meta_path", type=click.Path(path_type=Path, exists=True))
@click.option("--lines", "lines_path", type=click.Path(path_type=Path, exists=True))
@click.option(
    "--analysis", "analyses", multiple=True, type=click.Path(path_type=Path, exists=True)
)
@click.option("--sink", "sink_name", default="", help="临时覆盖 sink:markdown / feishu")
@click.pass_context
def cmd(
    ctx: click.Context,
    meta_path: Path | None,
    lines_path: Path | None,
    analyses: tuple[Path, ...],
    sink_name: str,
) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    workdir = get_workdir(ctx)
    name = sink_name or cfg.output.sink
    try:
        result = collect_and_assemble(workdir, meta_path, lines_path, analyses)
        outcome = run_sink(result, cfg, sink_name)
    except VtfError as e:
        log.error(str(e), step="finish")
        raise SystemExit(e.exit_code) from e
    _report_outcome(name, outcome, log, step="finish")
