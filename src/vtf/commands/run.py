from __future__ import annotations

import json
from typing import Any

import click

from vtf._ctx import get_config, get_logger, get_workdir
from vtf.errors import VtfError
from vtf.pipeline.analyze import analyze
from vtf.pipeline.download import download
from vtf.pipeline.fetch import fetch
from vtf.pipeline.merge import merge_into_lines
from vtf.transcribe import transcribe

_ALL_KINDS = ["summary", "breakdown", "rewrite"]


@click.command(
    name="run",
    help="跑到 analyze 阶段并停下(LLM 接管点)。"
    "填充 result 字段后用 vtf assemble + vtf emit 收尾。",
)
@click.argument("url")
@click.pass_context
def cmd(ctx: click.Context, url: str) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    workdir = get_workdir(ctx)
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        log.info("fetch", step="run")
        meta = fetch(url=url, cfg=cfg)
        meta_path = workdir / "meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), "utf-8")

        log.info("download", step="run")
        keep_video = cfg.output.sink == "feishu"
        audio, video_path = download(
            meta=meta, cfg=cfg, workdir=workdir, keep_video=keep_video
        )
        if video_path is not None:
            meta["video_path"] = str(video_path)
            meta_path.write_text(json.dumps(meta, ensure_ascii=False), "utf-8")

        log.info("transcribe", step="run")
        transcript = transcribe(audio_path=audio, cfg=cfg)
        (workdir / "transcript.json").write_text(
            json.dumps(transcript, ensure_ascii=False), "utf-8"
        )

        log.info("merge", step="run")
        lines = merge_into_lines(transcript["sentences"])
        lines_path = workdir / "lines.json"
        lines_path.write_text(json.dumps({"lines": lines}, ensure_ascii=False), "utf-8")

        analyses_paths: list[str] = []
        for kind in _ALL_KINDS:
            log.info(f"analyze {kind}", step="run")
            a: dict[str, Any] = analyze(kind=kind, meta=meta, lines=lines, cfg=cfg)
            p = workdir / f"{kind}.json"
            p.write_text(json.dumps(a, ensure_ascii=False), "utf-8")
            analyses_paths.append(str(p))
    except VtfError as e:
        log.error(str(e), step="run")
        raise SystemExit(e.exit_code) from e

    click.echo(f"工作目录: {workdir}", err=True)
    click.echo("流水线已跑到 analyze 阶段，请填充以下文件的 result 字段:", err=True)
    for ap in analyses_paths:
        click.echo(f"  - {ap}", err=True)
    click.echo("\n填充完毕后用以下命令收尾:", err=True)
    cmd_lines = [
        f"  vtf assemble --meta {meta_path} --lines {lines_path} \\",
        *[f"    --analysis {ap} \\" for ap in analyses_paths],
        f"    > {workdir}/result.json",
        f"  vtf emit < {workdir}/result.json",
    ]
    click.echo("\n".join(cmd_lines), err=True)
