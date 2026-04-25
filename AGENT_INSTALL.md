# AGENT_INSTALL.md - 智能体安装指南

本文件专供 AI 智能体（Claude Code、Codex 等）阅读，提供精确的安装命令。

## 一键安装命令

```bash
# 方式1: uvx（推荐，无需克隆）
uvx --from git+https://github.com/richardwild426/v2f.git vtf doctor

# 方式2: pip
pip install git+https://github.com/richardwild426/v2f.git
vtf doctor

# 方式3: 本地克隆开发
git clone https://github.com/richardwild426/v2f.git vtf
cd vtf
uv sync
uv run vtf doctor
```

## 前置依赖安装

vtf 需要以下外部工具：

```bash
# yt-dlp（必需）
pip install yt-dlp

# FunASR（必需）- 需要独立 Python 环境
python3 -m venv ~/.venv/funasr
~/.venv/funasr/bin/pip install funasr
export VTF_TRANSCRIBE_FUNASR_PYTHON=~/.venv/funasr/bin/python

# lark-cli（可选，仅飞书表格需要）
pip install lark-cli
lark-cli auth login
```

## 快速验证

```bash
# 1. 环境检查
vtf doctor

# 2. 测试元数据获取
vtf fetch "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# 3. 测试端到端（跳过 AI 分析）
vtf run "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --skip summary --skip breakdown --skip rewrite --sink markdown
```

## 环境变量配置

```bash
# 最小配置（markdown 输出）
export VTF_OUTPUT_SINK="markdown"
export VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER="chrome"

# 飞书表格配置
export VTF_SINK_FEISHU_BASE_TOKEN="your_token"
export VTF_SINK_FEISHU_TABLE_ID="your_table_id"
export VTF_SINK_FEISHU_SCHEMA="examples/schemas/baokuan.toml"
```

## 常见问题

### yt-dlp 412 错误（B站）

B站视频需要浏览器 Cookie：

```bash
# 确保 Chrome 已登录 B站，然后：
export VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER="chrome"
```

### FunASR 未找到

```bash
# 指定 FunASR Python 路径
export VTF_TRANSCRIBE_FUNASR_PYTHON=/path/to/python-with-funasr

# 或创建专用环境
python3 -m venv ~/.venv/funasr
~/.venv/funasr/bin/pip install funasr
export VTF_TRANSCRIBE_FUNASR_PYTHON=~/.venv/funasr/bin/python
```