from __future__ import annotations

import json
from pathlib import Path

import click

from vtf._ctx import get_logger, get_workdir
from vtf.errors import UserError, VtfError
from vtf.pipeline.assemble import assemble

_AUTO_KINDS = ("summary", "breakdown", "rewrite")


@click.command(
    name="assemble",
    help="拼装最终 result.json。"
    "默认从 --workdir 自动收集 meta.json / lines.json / {summary,breakdown,rewrite}.json；"
    "也可显式传 --meta / --lines / --analysis 覆盖。",
)
@click.option("--meta", "meta_path", type=click.Path(path_type=Path, exists=True))
@click.option("--lines", "lines_path", type=click.Path(path_type=Path, exists=True))
@click.option("--analysis", "analyses", multiple=True, type=click.Path(path_type=Path, exists=True))
@click.pass_context
def cmd(
    ctx: click.Context,
    meta_path: Path | None,
    lines_path: Path | None,
    analyses: tuple[Path, ...],
) -> None:
    log = get_logger(ctx)
    workdir = get_workdir(ctx)

    if meta_path is None:
        meta_path = workdir / "meta.json"
    if lines_path is None:
        lines_path = workdir / "lines.json"

    analysis_paths: list[Path] = list(analyses)
    if not analysis_paths:
        for kind in _AUTO_KINDS:
            p = workdir / f"{kind}.json"
            if p.exists():
                analysis_paths.append(p)

    for p, label in [(meta_path, "meta.json"), (lines_path, "lines.json")]:
        if not p.exists():
            raise UserError(
                f"找不到 {label}: {p}"
                f"（用 --workdir 指定目录或显式 --{label.split('.')[0]}）"
            )
    if not analysis_paths:
        raise UserError(
            f"未找到任何 analysis 文件（{', '.join(f'{k}.json' for k in _AUTO_KINDS)} "
            f"在 {workdir} 内不存在；显式用 --analysis 指定）"
        )

    meta = json.loads(meta_path.read_text("utf-8"))
    lines_data = json.loads(lines_path.read_text("utf-8"))
    items = [json.loads(p.read_text("utf-8")) for p in analysis_paths]
    try:
        out = assemble(meta=meta, lines=lines_data["lines"], analyses=items)
    except VtfError as e:
        log.error(str(e), step="assemble")
        raise SystemExit(e.exit_code) from e
    click.echo(json.dumps(out, ensure_ascii=False))
