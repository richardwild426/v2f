from __future__ import annotations

import click


@click.command(name="init", help="交互式配置向导(暂未实现)")
@click.argument("sink", default="feishu")
def cmd(sink: str) -> None:
    click.echo(
        f"init {sink} 暂未实现。请手动配置环境变量或编辑 ~/.config/vtf/config.toml",
        err=True,
    )
    raise SystemExit(2)
