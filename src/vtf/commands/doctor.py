from __future__ import annotations

import json
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

    # lark-cli (optional, 飞书表格需要)
    lark = shutil.which("lark-cli")
    if lark:
        app_id = ""
        try:
            r = subprocess.run(
                [lark, "config", "show"], capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                try:
                    info = json.loads(r.stdout)
                    app_id = info.get("appId", "") or ""
                except json.JSONDecodeError:
                    app_id = ""
        except (OSError, subprocess.SubprocessError):
            pass
        identity = cfg.sink.feishu.identity
        if app_id:
            click.echo(
                f"✅ lark-cli: {lark} (appId={app_id}, identity={identity})"
            )
            if identity == "bot":
                click.echo(
                    "   ℹ️  机器人身份：请确认目标 base 已添加该应用为协作者并授予可编辑权限"
                )
        else:
            click.echo(
                f"⚠️  lark-cli: {lark} (未绑定应用；运行 `lark-cli config init --new` 创建/绑定飞书应用)"
            )
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

    # 飞书 sink 首次启用引导（首次安装时几乎必然命中）
    feishu_missing = (
        not cfg.sink.feishu.base_token
        or not cfg.sink.feishu.table_id
        or not cfg.sink.feishu.schema
    )
    if feishu_missing:
        click.echo("\n=== 飞书表格 sink（可选）===")
        click.echo("如要把分析结果写入飞书表格，请按以下步骤启用（推荐机器人身份）：")
        click.echo("  1. 安装 lark-cli 并绑定飞书应用：")
        click.echo("       lark-cli config init --new")
        click.echo("     验证：`lark-cli config show` 输出包含 appId")
        click.echo("  2. 把机器人加为目标 Bitable 协作者并授予「可编辑」权限：")
        click.echo("       浏览器打开 base → 「···」→「更多」→「添加文档应用」→ 搜机器人名 → 可编辑")
        click.echo("     不做这步会拿到 99991672 NoPermission")
        click.echo("  3. 在 ~/.config/vtf/config.toml 填入目标表格：")
        click.echo("       [output]")
        click.echo('       sink = "feishu"')
        click.echo("       [sink.feishu]")
        click.echo('       base_token = "bascn..."')
        click.echo('       table_id = "tbl..."')
        click.echo('       schema = "vtf/assets/examples/schemas/baokuan.toml"')
        click.echo('       identity = "bot"   # 默认值，可省')
        click.echo("  4. 再跑一次 `vtf doctor` 应输出 ✅ lark-cli ... (identity=bot)")
        click.echo("  详见：references/INSTALL.md 第 3 节")

    if issues:
        click.echo("\n=== 修复建议 ===")
        for i in issues:
            click.echo(f"  - {i}")
        click.echo("\n参考: AGENT_INSTALL.md 或 README.md")
        raise SystemExit(2)

    click.echo("\n✅ 环境检查通过，可以正常使用")
