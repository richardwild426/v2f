from __future__ import annotations

import click


@click.command(name="install", help="安装 wrapper 到目标平台(暂未实现)")
@click.argument("platform", default="claude-code")
def cmd(platform: str) -> None:
    click.echo(f"install {platform} 暂未实现。请手动复制 wrappers/{platform}/ 到目标目录", err=True)
    raise SystemExit(2)
