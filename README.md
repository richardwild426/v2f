# vtf - 视频内容流水线 CLI

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**通用视频内容流水线：URL → 转录 → AI 分析 → markdown / 飞书表格**

专为智能体设计：CLI 驱动、JSON 输入输出、清晰的 agent 契约。

---

## 快速开始

### 1. 安装（推荐 uvx）

```bash
# 从 GitHub 安装
uvx --from git+https://github.com/richardwild426/v2f.git vtf doctor

# 或本地开发安装
git clone https://github.com/richardwild426/v2f.git vtf
cd vtf
uv sync
uv run vtf doctor
```

### 2. 前置依赖

vtf 需要以下外部工具（运行时检测，缺失会提示）：

| 工具 | 用途 | 安装命令 |
|------|------|----------|
| **yt-dlp** | 视频/音频下载 | `pip install yt-dlp` 或 `brew install yt-dlp` |
| **FunASR** | 语音转录 | 在某个 Python 环境中 `pip install funasr` |
| **lark-cli** | 飞书表格写入（可选） | `pip install lark-cli` |

> 💡 智能体提示：先运行 `vtf doctor` 检查环境，根据输出安装缺失依赖。

### 3. 基本使用

```bash
# 端到端流水线（默认输出 markdown）
vtf run "https://www.bilibili.com/video/BV1xxx"

# 查看帮助
vtf --help
vtf run --help

# 环境自检
vtf doctor
```

---

## 智能体集成

### 安装命令

```bash
# uvx 一键安装
uvx --from git+https://github.com/richardwild426/v2f.git vtf --help

# 或 pip 安装
pip install git+https://github.com/richardwild426/v2f.git
vtf --help
```

### 命令清单

| 命令 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `vtf run <url>` | URL | markdown/飞书 | 端到端流水线 |
| `vtf fetch <url>` | URL | meta.json | 获取视频元数据 |
| `vtf download --meta m.json` | meta.json | audio.mp3 | 下载音频 |
| `vtf transcribe <audio>` | audio.mp3 | transcript.json | FunASR 转录 |
| `vtf merge` | transcript.json | lines.json | 合并句子碎片 |
| `vtf analyze --kind X` | lines.json | analysis.json | 生成 LLM prompt |
| `vtf assemble` | meta+lines+analyses | result.json | 拼装结果 |
| `vtf emit --sink X` | result.json | stdout/飞书 | 输出结果 |
| `vtf doctor` | 无 | 检查报告 | 环境自检 |

### analyze 契约（智能体必须遵守）

`vtf analyze --kind summary` 输出：

```json
{
  "kind": "summary",
  "prompt": "你是一个视频内容分析专家...",
  "context": {"title": "...", "lines_count": 42},
  "schema_hint": "expected: {text, points[], tags[]}",
  "result": null
}
```

**智能体职责**：
1. 读取 `prompt` 字段，调用 LLM 执行
2. 将结果填入 `result` 字段
3. 传递给 `vtf assemble`

```json
{
  "kind": "summary",
  "result": {
    "text": "一句话摘要",
    "points": ["要点1", "要点2"],
    "tags": ["#Tag1", "#Tag2"]
  }
}
```

---

## 配置

### 环境变量（推荐）

```bash
# 输出目标
export VTF_OUTPUT_SINK="markdown"  # 或 "feishu"

# FunASR 配置
export VTF_TRANSCRIBE_FUNASR_PYTHON="/path/to/python-with-funasr"
export VTF_TRANSCRIBE_ASR_MODEL="paraformer-zh"

# B站 Cookie（必需）
export VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER="chrome"

# 飞书表格配置（可选）
export VTF_SINK_FEISHU_BASE_TOKEN="your_token"
export VTF_SINK_FEISHU_TABLE_ID="your_table_id"
export VTF_SINK_FEISHU_SCHEMA="examples/schemas/baokuan.toml"

# Legacy 别名（兼容旧配置）
export TABLE_TOKEN="your_token"
export TABLE_ID="your_table_id"
```

### 配置文件

```bash
# 用户级配置
mkdir -p ~/.config/vtf
cat > ~/.config/vtf/config.toml << 'EOF'
[output]
sink = "markdown"

[transcribe]
asr_model = "paraformer-zh"

[platform.bilibili]
cookies_from_browser = "chrome"
EOF

# 项目级配置（当前目录）
./vtf.toml
```

---

## 支持平台

| 平台 | URL 格式 | 特殊要求 |
|------|----------|----------|
| B站 | `bilibili.com/video/BVxxx` 或 `b23.tv/xxx` | 需浏览器 Cookie（Chrome/Safari/Firefox） |
| YouTube | `youtube.com/watch?v=xxx` 或 `youtu.be/xxx` | 无 |
| 其他 | 任意 yt-dlp 支持的 URL | 无（generic fallback） |

---

## 详细文档

- [AGENT_GUIDE.md](AGENT_GUIDE.md) - 智能体使用指南
- [docs/data-shapes.md](docs/data-shapes.md) - 流水线数据格式
- [examples/schemas/baokuan.toml](examples/schemas/baokuan.toml) - 飞书表格字段示例

---

## 开发

```bash
# 克隆并安装开发依赖
git clone https://github.com/richardwild426/v2f.git vtf
cd vtf
uv sync --extra dev

# 运行测试
uv run pytest

# 代码检查
uv run ruff check src tests
uv run mypy
```