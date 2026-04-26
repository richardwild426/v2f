# vtf - 视频内容流水线 CLI

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**通用视频内容流水线：URL → 转录 → AI 分析 → markdown / 飞书表格**

专为智能体设计：CLI 驱动、JSON 输入输出、清晰的 agent 契约。

本项目遵循 [Agent Skills](https://agentskills.io) 标准格式，详见 [`vtf/SKILL.md`](vtf/SKILL.md)。

---

## 项目结构

```
vtf/
├── SKILL.md              # Agent Skills 标准格式（智能体指令）
├── references/           # 详细文档
│   ├── INSTALL.md        # 安装与自动配置
│   ├── GUIDE.md          # 智能体使用指南
│   └── data-shapes.md    # 流水线数据格式
├── assets/               # 资源文件
│   └── examples/         # 配置示例、schema
└── scripts/              # 辅助脚本（可选）

src/vtf/                  # Python CLI 包
tests/                    # 测试文件
```

---

## 快速开始

### 1. 安装（推荐 uvx）

```bash
# 从 GitHub 安装
uvx --from git+https://github.com/richardwild426/v2f.git vtf doctor

# 或本地开发安装
git clone https://github.com/richardwild426/v2f.git
cd v2f
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

> 💡 智能体提示：先运行 `vtf doctor` 检查环境，根据输出安装缺失依赖。详见 [`vtf/SKILL.md`](vtf/SKILL.md)。

### 3. 基本使用

vtf 采用 **CLI 边界 = LLM 调用前一步** 的设计，不会自动调用 LLM。推荐分步执行，让智能体在 analyze 阶段接管。

```bash
# 分步流水线（推荐）
mkdir -p ~/vtf-tasks/my-video && cd ~/vtf-tasks/my-video

# 1. 抓取元数据
vtf --workdir . fetch "https://www.bilibili.com/video/BV1xxx" > meta.json

# 2. 下载音频
AUDIO=$(vtf --workdir . download --meta meta.json)

# 3. 转录
vtf --workdir . transcribe "$AUDIO" > transcript.json

# 4. 合并句子
vtf --workdir . merge < transcript.json > lines.json

# 5. 生成 LLM prompt（智能体接管点）
vtf --workdir . analyze --meta meta.json --kind summary < lines.json > summary.json
vtf --workdir . analyze --meta meta.json --kind breakdown < lines.json > breakdown.json
vtf --workdir . analyze --meta meta.json --kind rewrite < lines.json > rewrite.json

# 智能体：执行每个 *.json 的 prompt 字段，把结果填入 result 字段

# 6. 装配
vtf --workdir . assemble > result.json

# 7. 输出
vtf --workdir . emit < result.json > report.md
```

#### 快捷命令 `vtf run`

`vtf run` 把第 1–5 步一口气跑完，产物写到工作目录后停下，由智能体填充 result：

```bash
mkdir -p ~/vtf-tasks/my-video && cd ~/vtf-tasks/my-video
vtf --workdir . run "https://www.bilibili.com/video/BV1xxx"
# stderr 会打印接下来的 assemble + emit 命令
```

**不要期待 vtf run 一条命令出报告** —— 它不会调用 LLM，也不会自动 assemble/emit。

#### 常用命令

```bash
vtf --help                 # 查看帮助
vtf doctor                 # 环境自检
vtf run --help             # 查看快捷命令说明
vtf assemble --help        # assemble 支持自动收集 workdir 内文件
```

---

## 智能体集成

本项目遵循 [Agent Skills](https://agentskills.io) 标准。

智能体加载 [`vtf/SKILL.md`](vtf/SKILL.md) 后可：
- 自动安装配置 FunASR
- 执行视频转录流水线
- 处理 analyze 契约（调用 LLM）

详见 [`vtf/references/GUIDE.md`](vtf/references/GUIDE.md)。

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
export VTF_SINK_FEISHU_SCHEMA="vtf/assets/examples/schemas/baokuan.toml"
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

- [`vtf/SKILL.md`](vtf/SKILL.md) - Agent Skills 标准格式
- [`vtf/references/INSTALL.md`](vtf/references/INSTALL.md) - 安装与自动配置
- [`vtf/references/GUIDE.md`](vtf/references/GUIDE.md) - 智能体使用指南
- [`vtf/references/data-shapes.md`](vtf/references/data-shapes.md) - 流水线数据格式
- [`vtf/assets/examples/schemas/baokuan.toml`](vtf/assets/examples/schemas/baokuan.toml) - 飞书表格字段示例

---

## 开发

```bash
# 克隆并安装开发依赖
git clone https://github.com/richardwild426/v2f.git
cd v2f
uv sync --extra dev

# 运行测试
uv run pytest

# 代码检查
uv run ruff check src tests
uv run mypy
```