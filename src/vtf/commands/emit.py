from __future__ import annotations

import json
import sys
from typing import Any

import click

from vtf._ctx import get_config, get_logger
from vtf.errors import UserError, VtfError
from vtf.sinks import get as get_sink
from vtf.sinks.base import EmitOutcome


def run_sink(result: dict[str, Any], cfg: Any, sink_name: str) -> EmitOutcome:
    """校验并调用指定 sink 输出。供 `emit` 与 `finish` 命令复用。

    不依赖 click ctx；失败时 raise VtfError。sink 名为空时用配置默认。
    """
    name = sink_name or cfg.output.sink
    sink = get_sink(name)
    ok, reason = sink.available(cfg)
    if not ok:
        raise UserError(f"sink {name!r} 不可用: {reason}")
    return sink.emit(result, cfg)


def _report_outcome(
    name: str, outcome: EmitOutcome, log: Any, step: str = "emit"
) -> None:
    if outcome.reason:
        if name == "markdown":
            click.echo(outcome.reason)
        else:
            click.echo(outcome.reason, err=True)
    if outcome.degraded:
        log.warn(f"{name} degraded", step=step, data={"reason": outcome.reason})


@click.command(name="emit", help="把 result.json 落到当前 sink(stdin)")
@click.option("--sink", "sink_name", default="", help="临时覆盖 sink:markdown / feishu")
@click.pass_context
def cmd(ctx: click.Context, sink_name: str) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    name = sink_name or cfg.output.sink
    result = json.load(sys.stdin)
    try:
        outcome = run_sink(result, cfg, sink_name)
    except VtfError as e:
        log.error(str(e), step="emit")
        raise SystemExit(e.exit_code) from e
    _report_outcome(name, outcome, log)
