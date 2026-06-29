# Pipeline 数据形状参考

每个流水线步骤通过 stdin/stdout 传递 JSON。以下是契约，后续修改需更新本文档。

## meta.json (fetch 输出)

```json
{
  "platform": "bilibili",
  "video_id": "BV1xxx",
  "url": "https://www.bilibili.com/video/BV1xxx",
  "title": "...",
  "author": "...",
  "upload_date": "2026-04-01 12:30",
  "duration": 600,
  "duration_str": "10:00",
  "thumbnail": "https://...",
  "description": "...",
  "view": 12345,
  "like": 678,
  "favorite": 0,
  "share": 0,
  "reply": 90
}
```

## transcript.json (transcribe 输出)

```json
{
  "audio_path": "/path/to/audio.mp3",
  "asr_model": "paraformer-zh",
  "sentences": ["第一句", "第二句", "..."]
}
```

## lines.json (merge 输出)

```json
{
  "lines": ["合并后的第一行", "合并后的第二行", "..."]
}
```

## analysis.json (analyze 输出，result 由 agent 回填)

```json
{
  "kind": "summary",
  "prompt": "<完整渲染的 LLM prompt>",
  "context": {"title": "...", "author": "...", "lines_count": 42},
  "schema_hint": "required for Feishu: text, tags",
  "required_result_fields": [
    {
      "field": "摘要",
      "source": "analyses.summary.text",
      "result_path": "text"
    }
  ],
  "result": null
}
```

- `result` 的形状由 prompt 模板（`prompts/*.md`）权威定义，agent 按 prompt 要求输出。
- `schema_hint` 只列下游飞书必填的 `result_path`；无飞书 schema 时为空串。
- `required_result_fields` 由 schema（`assets/schemas/baokuan.toml`）动态派生，是机器可读契约。
  breakdown 的分镜条目还带 `row_fields`，逐项描述每个 shot 必须包含的子字段：

```json
{
  "field": "分镜明细",
  "source": "analyses.breakdown.shots",
  "result_path": "shots",
  "row_fields": [
    {"field": "镜头", "result_path": "shot", "required": true},
    {"field": "文案", "result_path": "script", "required": true}
  ]
}
```

agent 跑完 LLM 后把 `result` 填上对象，再交给 `vtf assemble`（或 `vtf finish` 一步收尾）。
存在 `required_result_fields` 时，这些 `result_path`（含 `row_fields` 子字段）必须在 `result`
中填非空值，否则 `vtf assemble` 阶段即报错。

## result.json (assemble 输出)

```json
{
  "meta": { ... },
  "lines": ["..."],
  "analyses": {
    "summary":   { "text": "...", "points": ["..."], "tags": ["..."] },
    "breakdown": {
      "text": "...",
      "hook": "...",
      "core": "...",
      "cta": "...",
      "pros": ["..."],
      "suggestions": ["..."],
      "shots": [
        {
          "shot": 1,
          "duration": "3s",
          "script": "...",
          "appearance": "人 / AI / 电脑 / 手机 / 屏幕录制",
          "materials": ["..."],
          "sound": "...",
          "motion": "...",
          "notes": "..."
        }
      ]
    },
    "rewrite":   { "text": "..." }
  }
}
```

未跑的 analyze kind 会导致 `vtf assemble` 报错。三个 kind（summary, breakdown, rewrite）**全部跑完** result 非 null 才算完成。
