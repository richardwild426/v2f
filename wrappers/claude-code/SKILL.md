---
name: vtf
description: 视频 → 转录 → AI 分析 → markdown / 飞书表格的通用流水线
tags: [video, transcription, funasr, feishu, bitable, content-analysis, bilibili, youtube]
category: media
---

# 使用 vtf

通过 `uvx --from git+<repo> vtf <subcommand>` 调用。

## 命令清单

| 命令 | 说明 |
|------|------|
| `vtf run <url>` | 端到端流水线 |
| `vtf fetch <url>` | 抓取视频元数据 |
| `vtf download --meta m.json` | 下载音频 |
| `vtf transcribe <audio>` | FunASR 转录 |
| `vtf merge` | 合并句子为字幕行(stdin) |
| `vtf analyze --kind summary` | 生成 LLM prompt(stdin) |
| `vtf assemble` | 拼装最终 result.json |
| `vtf emit --sink markdown` | 输出到 sink(stdin) |
| `vtf doctor` | 环境自检 |

## analyze 子命令契约

`vtf analyze --kind summary` 输出 JSON：
```json
{
  "kind": "summary",
  "prompt": "<完整渲染的 prompt>",
  "context": {"title": "...", "lines_count": 42},
  "schema_hint": "expected: {text, points[], tags[]}",
  "result": null
}
```

**agent 必须执行 prompt 并把结果回填到 result 字段**，再交给 `vtf assemble`。

## 飞书配置

```bash
export VTF_SINK_FEISHU_BASE_TOKEN="你的base_token"
export VTF_SINK_FEISHU_TABLE_ID="你的table_id"
export VTF_SINK_FEISHU_SCHEMA="examples/schemas/baokuan.toml"
```

或使用 legacy 别名：`TABLE_TOKEN` / `TABLE_ID`。

## 环境自检

```bash
vtf doctor
```