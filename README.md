# vtf - 视频内容流水线

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**URL → 转录 → AI 分析 → markdown / 飞书表格**，一条命令跑通预处理，AI 接管分析，再一条命令输出结果。

本项目遵循 [Agent Skills](https://agentskills.io) 标准，智能体加载 [vtf/SKILL.md](vtf/SKILL.md) 即可自动执行。

---

## 快速开始

```bash
# 一键安装
bash vtf/scripts/setup.sh

# 跑一条流水线
mkdir -p ~/vtf-tasks/my-video && cd ~/vtf-tasks/my-video
vtf --workdir . fetch "https://www.bilibili.com/video/BV1xxx" > meta.json
AUDIO=$(vtf --workdir . download --meta meta.json)
vtf --workdir . transcribe "$AUDIO" > transcript.json
vtf --workdir . merge < transcript.json > lines.json

# 生成 LLM prompt（交给你使用的 AI 填充 result）
vtf --workdir . analyze --meta meta.json --kind summary < lines.json > summary.json
vtf --workdir . analyze --meta meta.json --kind breakdown < lines.json > breakdown.json
vtf --workdir . analyze --meta meta.json --kind rewrite < lines.json > rewrite.json

# AI 填充 result 后，收尾
vtf --workdir . assemble > result.json
vtf --workdir . emit < result.json > report.md
```

或用快捷命令 `vtf run` 把前 5 步一口气跑完：

```bash
mkdir -p ~/vtf-tasks/my-video && cd ~/vtf-tasks/my-video
vtf --workdir . run "https://www.bilibili.com/video/BV1xxx"
# AI 填充 summary.json / breakdown.json / rewrite.json 的 result 字段
vtf --workdir . assemble > result.json
vtf --workdir . emit < result.json > report.md
```

---

## 前置依赖

| 工具 | 用途 | 安装 |
|------|------|------|
| **yt-dlp** | 视频/音频下载 | `pip install yt-dlp` 或 `brew install yt-dlp` |
| **FunASR** | 语音转录 | 在某个 Python 环境 `pip install funasr`，`vtf/scripts/setup.sh` 自动处理 |
| **lark-cli** | 飞书表格写入（可选） | 参考 [vtf/references/feishu.md](vtf/references/feishu.md) |

运行 `vtf doctor` 检查环境。

---

## 配置

环境变量（推荐）：

```bash
export VTF_TRANSCRIBE_FUNASR_PYTHON="~/.venv/funasr/bin/python"
export VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER="chrome"
export VTF_OUTPUT_SINK="markdown"  # 或 "feishu"
```

或写 `~/.config/vtf/config.toml`，参考 [vtf/assets/config.toml](vtf/assets/config.toml)。

---

## 支持平台

| 平台 | URL 格式 | 特殊要求 |
|------|----------|----------|
| B站 | bilibili.com / b23.tv | 浏览器 Cookie |
| YouTube | youtube.com / youtu.be | 无 |
| 其他 | yt-dlp 支持的任意 URL | 无 |

---

## 文档

- [vtf/SKILL.md](vtf/SKILL.md) — 智能体指令（Agent Skills 标准格式）
- [vtf/references/pipeline.md](vtf/references/pipeline.md) — 流水线详细说明
- [vtf/references/installation.md](vtf/references/installation.md) — 安装与自动配置
- [vtf/references/feishu.md](vtf/references/feishu.md) — 飞书 sink 接入
- [vtf/references/configuration.md](vtf/references/configuration.md) — 配置项参考
- [vtf/references/troubleshooting.md](vtf/references/troubleshooting.md) — 常见问题

---

## 开发

```bash
git clone https://github.com/richardwild426/v2f.git
cd v2f
uv sync --extra dev
uv run pytest
uv run ruff check src tests
uv run mypy
```
