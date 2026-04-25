---
name: vtf
description: Video content pipeline - transcribe videos (B站/YouTube), analyze with LLM, output to markdown or Feishu table. Use when user mentions video transcription, B站/YouTube analysis, or converting video content to text/notes.
license: MIT
compatibility: Requires Python 3.11+, yt-dlp, FunASR (auto-configured)
metadata:
  author: richardwild426
  version: "1.0"
---

# vtf - 视频内容流水线

视频 URL → 转录 → AI 分析 → markdown / 飞书表格的通用流水线 CLI。

## 安装

```bash
uvx --from git+https://github.com/richardwild426/v2f.git vtf doctor
```

**智能体自动配置 FunASR（若 doctor 报未找到）**：

```bash
# 1. 创建 FunASR 专用环境
python3 -m venv ~/.venv/funasr
~/.venv/funasr/bin/pip install funasr modelscope

# 2. 写入配置文件（永久生效）
mkdir -p ~/.config/vtf
cat > ~/.config/vtf/config.toml << 'EOF'
[transcribe]
funasr_python = "~/.venv/funasr/bin/python"
asr_model = "paraformer-zh"

[platform.bilibili]
cookies_from_browser = "chrome"
EOF

# 3. 验证
vtf doctor
```

详见 [references/INSTALL.md](references/INSTALL.md)。

---

## 命令

| 命令 | 说明 |
|------|------|
| `vtf run <url>` | 端到端流水线 |
| `vtf fetch <url>` | 抓取视频元数据 → meta.json |
| `vtf download --meta m.json` | 下载音频 |
| `vtf transcribe <audio>` | FunASR 转录 → transcript.json |
| `vtf merge` | 合并句子碎片(stdin → stdout) |
| `vtf analyze --kind X` | 生成 LLM prompt(stdin → stdout) |
| `vtf assemble` | 拼装 result.json |
| `vtf emit --sink X` | 输出到 sink(stdin) |
| `vtf doctor` | 环境自检 |

---

## analyze 契约（智能体必须遵守）

`vtf analyze --kind summary` 输出 JSON，`result` 字段为 null。

**智能体必须**：
1. 执行 `prompt` 字段内容（调用 LLM）
2. 将结果填入 `result` 字段
3. 传递给 `vtf assemble`

```json
{
  "kind": "summary",
  "prompt": "<完整渲染的 LLM prompt>",
  "result": {"text": "...", "points": [...], "tags": [...]}
}
```

---

## 分步流水线示例

```bash
vtf fetch "https://www.bilibili.com/video/BV1xxx" > meta.json
vtf download --meta meta.json
vtf transcribe audio.mp3 > transcript.json
vtf merge < transcript.json > lines.json
vtf analyze --kind summary < lines.json > summary.json
# Agent: 执行 summary.json 中的 prompt，填入 result
vtf assemble --meta meta.json --lines lines.json --analysis summary.json > result.json
vtf emit --sink markdown < result.json
```

---

## 支持平台

| 平台 | URL 格式 | 特殊要求 |
|------|----------|----------|
| B站 | bilibili.com / b23.tv | 需浏览器 Cookie（Chrome/Safari/Firefox） |
| YouTube | youtube.com / youtu.be | 无 |
| 其他 | yt-dlp 支持的任意 URL | 无（generic fallback） |

---

## 配置

环境变量（推荐）：

```bash
export VTF_TRANSCRIBE_FUNASR_PYTHON="~/.venv/funasr/bin/python"
export VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER="chrome"
export VTF_OUTPUT_SINK="markdown"  # 或 "feishu"
```

或配置文件 `~/.config/vtf/config.toml`：

```toml
[output]
sink = "markdown"

[transcribe]
funasr_python = "~/.venv/funasr/bin/python"
asr_model = "paraformer-zh"

[platform.bilibili]
cookies_from_browser = "chrome"

[sink.feishu]  # 可选
base_token = ""
table_id = ""
schema = "vtf/assets/examples/schemas/baokuan.toml"
```

---

## 详细文档

- [references/INSTALL.md](references/INSTALL.md) - 安装与自动配置
- [references/GUIDE.md](references/GUIDE.md) - 智能体使用指南
- [references/data-shapes.md](references/data-shapes.md) - 流水线数据格式