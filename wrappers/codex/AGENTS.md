# vtf - 视频内容流水线

调用方式：`uvx --from git+<repo> vtf <subcommand>`

## 命令清单

| 命令 | 说明 |
|------|------|
| `run <url>` | 端到端流水线 |
| `fetch <url>` | 抓取视频元数据 |
| `download --meta m.json` | 下载音频 |
| `transcribe <audio>` | FunASR 转录 |
| `merge` | 合并句子(stdin) |
| `analyze --kind X` | 生成 LLM prompt(stdin) |
| `assemble` | 拼装 result.json |
| `emit --sink X` | 输出到 sink(stdin) |
| `doctor` | 环境自检 |

## analyze 契约

agent 必须执行 analyze 输出的 prompt，把结果回填到 `result` 字段，再交给 assemble。

## 飞书配置

环境变量：`VTF_SINK_FEISHU_BASE_TOKEN`、`VTF_SINK_FEISHU_TABLE_ID`、`VTF_SINK_FEISHU_SCHEMA`