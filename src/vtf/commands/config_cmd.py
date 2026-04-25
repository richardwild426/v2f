from __future__ import annotations

import click


@click.group(name="config", help="配置管理")
def cmd() -> None:
    pass


@cmd.command("list", help="列出当前配置")
@click.pass_context
def list_config(ctx: click.Context) -> None:
    from vtf._ctx import get_config
    cfg = get_config(ctx)
    click.echo(f"output.sink = {cfg.output.sink}")
    click.echo(f"transcribe.asr_model = {cfg.transcribe.asr_model}")
    click.echo(f"bilibili.cookies_from_browser = {cfg.platform.bilibili.cookies_from_browser}")
