from __future__ import annotations

import shutil
import subprocess

import click

from vtf._ctx import get_config
from vtf.transcribe.funasr import find_funasr_python


@click.command(name="doctor", help="环境自检")
@click.pass_context
def cmd(ctx: click.Context) -> None:
    issues = []
    cfg = get_config(ctx)

    click.echo("=== vtf 环境检查 ===\n")

    # yt-dlp / yt-dlp
    yt = shutil.which("yt-dlp")
    if yt:
        try:
            r = subprocess.run([yt, "--version"], capture_output=True, text=True, timeout=5)
            version = r.stdout.strip() if r.returncode == 0 else "未知"
            click.echo(f"✅ yt-dlp: {yt} (v{version})")
        except (OSError, subprocess.SubprocessError):
            click.echo(f"✅ yt-dlp: {yt}")
    else:
        issues.append("yt-dlp 未找到，请 pip install yt-dlp 或 brew install yt-dlp")
        click.echo("❌ yt-dlp: 未找到")

    # FunASR - 使用配置和环境变量
    funasr_py = find_funasr_python(cfg)
    if funasr_py:
        click.echo(f"✅ FunASR: {funasr_py}")
        # 显示配置来源
        env_py = cfg.transcribe.funasr_python
        if env_py:
            click.echo(f"   (配置: funasr_python = {env_py})")
    else:
        env_hint = cfg.transcribe.funasr_python or "未设置"
        issues.append(
            "FunASR 未找到。请在某个 Python 环境中 `pip install funasr`，"
            "并设置环境变量 VTF_TRANSCRIBE_FUNASR_PYTHON 或配置 transcribe.funasr_python"
        )
        click.echo(f"❌ FunASR: 未找到 (funasr_python 配置: {env_hint})")

    # lark-cli (optional)
    lark = shutil.which("lark-cli")
    if lark:
        try:
            r = subprocess.run([lark, "auth", "status"], capture_output=True, text=True, timeout=5)
            status = "已登录" if r.returncode == 0 else "未登录"
            click.echo(f"✅ lark-cli: {lark} ({status})")
        except (OSError, subprocess.SubprocessError):
            click.echo(f"✅ lark-cli: {lark}")
    else:
        click.echo("⚠️  lark-cli: 未找到（可选，仅飞书表格需要）")

    # 输出配置摘要
    click.echo("\n=== 当前配置 ===")
    click.echo(f"output.sink = {cfg.output.sink}")
    click.echo(f"transcribe.asr_model = {cfg.transcribe.asr_model}")
    bilibili_browser = cfg.platform.bilibili.cookies_from_browser
    if bilibili_browser:
        click.echo(f"platform.bilibili.cookies_from_browser = {bilibili_browser}")

    # 飞书配置（如果有）
    if cfg.sink.feishu.base_token:
        click.echo("sink.feishu.base_token = 已配置")
    if cfg.sink.feishu.table_id:
        click.echo("sink.feishu.table_id = 已配置")

    if issues:
        click.echo("\n=== 修复建议 ===")
        for i in issues:
            click.echo(f"  - {i}")
        click.echo("\n参考: AGENT_INSTALL.md 或 README.md")
        raise SystemExit(2)

    click.echo("\n✅ 环境检查通过，可以正常使用")
