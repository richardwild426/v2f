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
vtf fetch "https://www.bilibili.com/video/BV1xxx" > meta.json
AUDIO=$(vtf download --meta meta.json)
vtf transcribe "$AUDIO" > transcript.json
vtf merge < transcript.json > lines.json

# 生成 LLM prompt（交给你使用的 AI 填充 result）
vtf analyze --meta meta.json --kind summary < lines.json > summary.json
vtf analyze --meta meta.json --kind breakdown < lines.json > breakdown.json
vtf analyze --meta meta.json --kind rewrite < lines.json > rewrite.json

# AI 填充 result 后，收尾
vtf assemble > result.json
vtf emit < result.json > report.md
```

或用快捷命令 `vtf run` 把前 5 步一口气跑完：

```bash
mkdir -p ~/vtf-tasks/my-video && cd ~/vtf-tasks/my-video
vtf run "https://www.bilibili.com/video/BV1xxx"
# AI 填充 summary.json / breakdown.json / rewrite.json 的 result 字段
vtf assemble > result.json
vtf emit < result.json > report.md
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

## 截图功能

vtf 支持根据字幕时间戳自动截取视频帧，用于内容分析和可视化。

### 截图标注

支持在截图上添加文字、箭头、高亮等标注，增强可读性。

#### 标注使用流程

```bash
# 1. 先生成截图
vtf screenshot --video video.mp4 --subtitles lines.json --output screenshots.json

# 2. 创建标注配置文件 annotations.json
cat > annotations.json << 'EOF'
{
  "0": [
    {"type": "text", "position": [10, 10], "content": "重要信息", "color": "#FF0000", "size": 24},
    {"type": "arrow", "position": [50, 50], "end_position": [200, 200], "color": "#00FF00"},
    {"type": "rectangle", "position": [100, 100], "end_position": [300, 250], "color": "#0000FF"}
  ],
  "1": [
    {"type": "highlight", "position": [50, 50], "end_position": [200, 150], "color": "#FFFF00"}
  ]
}
EOF

# 3. 添加标注
vtf screenshot-annotate --input screenshots.json --annotations annotations.json
```

#### 标注类型

| 类型 | 说明 | 必需参数 |
|------|------|----------|
| `text` | 文字标注 | `position`, `content` |
| `arrow` | 箭头标注 | `position`, `end_position` |
| `rectangle` | 矩形框 | `position`, `end_position` |
| `highlight` | 高亮区域 | `position`, `end_position` |
| `timestamp` | 时间戳 | `position` |

#### 标注配置选项

```bash
vtf screenshot-annotate \
  --input screenshots.json \
  --annotations annotations.json \
  --font /path/to/font.ttf \      # 自定义字体
  --font-size 24 \                 # 字体大小
  --color "#FF0000" \              # 默认颜色
  --opacity 0.8 \                  # 透明度 (0-1)
  --padding 15 \                   # 文字内边距
  --no-background                  # 不显示文字背景
```

### 使用方式

```bash
# 字幕模式：根据字幕时间戳截图
vtf screenshot --video video.mp4 --subtitles lines.json --mode subtitle

# 场景模式：检测场景变化自动截图
vtf screenshot --video video.mp4 --subtitles lines.json --mode scene

# 自动模式（默认）：优先使用字幕，失败时回退到场景检测
vtf screenshot --video video.mp4 --subtitles lines.json --mode auto
```

### 配置选项

在 `config.toml` 中配置截图参数：

```toml
[screenshot]
enabled = true
ffmpeg_path = "ffmpeg"
scene_threshold = 0.3      # 场景变化检测阈值（0-1）
min_interval_seconds = 2   # 最小截图间隔
similarity_threshold = 0.95 # 图像相似度阈值（去重）
output_dir = "screenshots"
```

### 功能特性

- **智能去重**：使用感知哈希 (pHash) 自动过滤相似截图
- **多模式支持**：字幕模式、场景检测模式、自动回退模式
- **时间戳关联**：每张截图关联字幕文本和时间点
- **批量处理**：支持长视频批量截图

### 输出格式

截图结果以 JSON 格式输出：

```json
{
  "video_path": "video.mp4",
  "screenshots": [
    {
      "index": 0,
      "timestamp_ms": 1000,
      "timestamp_str": "00:01",
      "subtitle_text": "字幕内容",
      "image_path": "screenshots/subtitle_0000_1000.jpg",
      "phash": "a1b2c3d4e5f6g7h8"
    }
  ],
  "total": 1
}
```

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
