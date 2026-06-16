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
  "schema_hint": "expected: {text, points[], tags[]}; required for Feishu: text, tags",
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

agent 跑完 LLM 后，把 `result` 字段填上对象，再交给 `vtf assemble`。如果存在 `required_result_fields`，这些 `result_path` 是下游飞书 schema 需要的字段，必须在 `result` 中填充非空值。

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
