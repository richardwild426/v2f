from __future__ import annotations

import shutil

import click


@click.command(name="doctor", help="环境自检")
def cmd() -> None:
    issues = []
    # yt-dlp
    yt = shutil.which("yt-dlp")
    if yt:
        click.echo(f"✅ yt-dlp: {yt}")
    else:
        issues.append("yt-dlp 未找到，请 pip install yt-dlp")
        click.echo("❌ yt-dlp: 未找到")

    # FunASR
    import subprocess
    for py in ["python3", "python"]:
        if shutil.which(py):
            r = subprocess.run([py, "-c", "import funasr"], capture_output=True, timeout=10)
            if r.returncode == 0:
                click.echo(f"✅ FunASR: {py}")
                break
    else:
        issues.append("FunASR 未找到，请 pip install funasr")
        click.echo("❌ FunASR: 未找到")

    # lark-cli (optional)
    lark = shutil.which("lark-cli")
    if lark:
        click.echo(f"✅ lark-cli: {lark}")
    else:
        click.echo("⚠️  lark-cli: 未找到(可选，仅飞书表格需要)")

    if issues:
        click.echo("\n修复建议:")
        for i in issues:
            click.echo(f"  - {i}")
        raise SystemExit(2)
