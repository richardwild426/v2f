from __future__ import annotations

import json
import sys

import click

from vtf._ctx import get_config, get_logger
from vtf.errors import UserError, VtfError
from vtf.sinks import get as get_sink


@click.command(name="emit", help="把 result.json 落到当前 sink(stdin)")
@click.option("--sink", "sink_name", default="", help="临时覆盖 sink:markdown / feishu")
@click.pass_context
def cmd(ctx: click.Context, sink_name: str) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    name = sink_name or cfg.output.sink
    result = json.load(sys.stdin)
    try:
        sink = get_sink(name)
        ok, reason = sink.available(cfg)
        if not ok:
            raise UserError(f"sink {name!r} 不可用: {reason}")
        outcome = sink.emit(result, cfg)
        if outcome.reason:
            if name == "markdown":
                click.echo(outcome.reason)
            else:
                click.echo(outcome.reason, err=True)
    except VtfError as e:
        log.error(str(e), step="emit")
        raise SystemExit(e.exit_code) from e
    if outcome.degraded:
        log.warn(f"{name} degraded", step="emit", data={"reason": outcome.reason})
