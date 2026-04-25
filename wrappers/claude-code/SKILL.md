---
name: vtf
description: 视频 → 转录 → AI 分析 → markdown / 飞书表格的通用流水线 CLI
tags: [video, transcription, funasr, feishu, bitable, content-analysis, bilibili, youtube]
category: media
---

# vtf - 视频内容流水线

## 安装

```bash
uvx --from git+https://github.com/richardwild426/v2f.git vtf doctor

详见 [AGENT_INSTALL.md](../../AGENT_INSTALL.md)。

## 命令

| 命令 | 说明 |
|------|------|
| `vtf run <url>` | 端到端 |
| `vtf fetch <url>` | 元数据 |
| `vtf transcribe <audio>` | 转录 |
| `vtf analyze --kind X` | LLM prompt |
| `vtf emit --sink X` | 输出 |
| `vtf doctor` | 环境检查 |

## 智能体契约

`vtf analyze --kind summary` 输出 JSON，`result` 字段为 null。

**智能体必须**：
1. 执行 `prompt` 字段内容
2. 填充 `result` 字段
3. 传递给 `vtf assemble`

## 配置

```bash
export VTF_OUTPUT_SINK="markdown"
export VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER="chrome"
export VTF_TRANSCRIBE_FUNASR_PYTHON="/path/to/funasr-python"
```

飞书表格：
```bash
export VTF_SINK_FEISHU_BASE_TOKEN="token"
export VTF_SINK_FEISHU_TABLE_ID="table_id"
export VTF_SINK_FEISHU_SCHEMA="examples/schemas/baokuan.toml"
```