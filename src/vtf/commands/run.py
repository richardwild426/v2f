from __future__ import annotations

import json
from typing import Any

import click

from vtf._ctx import get_config, get_logger, get_workdir
from vtf.errors import VtfError
from vtf.pipeline.analyze import analyze
from vtf.pipeline.assemble import assemble
from vtf.pipeline.download import download
from vtf.pipeline.fetch import fetch
from vtf.pipeline.merge import merge_into_lines
from vtf.sinks import get as get_sink
from vtf.transcribe import transcribe

_ALL_KINDS = ["summary", "breakdown", "rewrite"]


@click.command(name="run", help="端到端流水线:URL → 落 sink")
@click.argument("url")
@click.option("--sink", "sink_name", default="", help="临时覆盖 sink")
@click.option("--skip", "skips", multiple=True, type=click.Choice(_ALL_KINDS),
              help="跳过某个 analyze kind(可重复)")
@click.pass_context
def cmd(ctx: click.Context, url: str, sink_name: str, skips: tuple[str, ...]) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    workdir = get_workdir(ctx)
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        log.info("fetch", step="run")
        meta = fetch(url=url, cfg=cfg)
        (workdir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), "utf-8")
        log.info("download", step="run")
        audio = download(meta=meta, cfg=cfg, workdir=workdir)
        log.info("transcribe", step="run")
        transcript = transcribe(audio_path=audio, cfg=cfg)
        log.info("merge", step="run")
        lines = merge_into_lines(transcript["sentences"])
        (workdir / "lines.json").write_text(
            json.dumps({"lines": lines}, ensure_ascii=False), "utf-8"
        )
        analyses: list[dict[str, Any]] = []
        for kind in _ALL_KINDS:
            if kind in skips:
                continue
            log.info(f"analyze {kind}", step="run")
            a = analyze(kind=kind, meta=meta, lines=lines, cfg=cfg)
            a["result"] = {"text": f"[{kind} placeholder - agent should fill]"}
            analyses.append(a)
        log.info("assemble", step="run")
        result = assemble(meta=meta, lines=lines, analyses=analyses)
        log.info("emit", step="run")
        name = sink_name or cfg.output.sink
        sink = get_sink(name)
        outcome = sink.emit(result, cfg)
        if outcome.reason and name == "markdown":
            click.echo(outcome.reason)
        if outcome.degraded:
            log.warn("sink degraded", step="emit", data={"reason": outcome.reason})
    except VtfError as e:
        log.error(str(e), step="run")
        raise SystemExit(e.exit_code) from e
