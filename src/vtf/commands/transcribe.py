from __future__ import annotations

import json
from pathlib import Path

import click

from vtf._ctx import get_config, get_logger
from vtf.errors import VtfError
from vtf.transcribe import transcribe


@click.command(name="transcribe", help="FunASR 转录音频")
@click.argument("audio", type=click.Path(path_type=Path, exists=True))
@click.pass_context
def cmd(ctx: click.Context, audio: Path) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    try:
        out = transcribe(audio_path=audio, cfg=cfg)
    except VtfError as e:
        log.error(str(e), step="transcribe")
        raise SystemExit(e.exit_code) from e
    click.echo(json.dumps(out, ensure_ascii=False))
