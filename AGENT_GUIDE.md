# vtf - Agent 使用指南

通用视频内容流水线 CLI：URL → 转录 → AI 分析 → markdown / 飞书表格

## 安装

```bash
# 本地开发
git clone <repo> vtf && cd vtf && uv sync

# 或通过 uvx
uvx --from git+<repo> vtf doctor
```

## 命令清单

### 端到端

```bash
vtf run <url>                      # 用配置好的 sink
vtf run <url> --sink markdown      # 临时切 sink
vtf run <url> --skip rewrite       # 跳过某个 analyze kind
```

### 分步

```bash
vtf fetch <url>                    -> meta.json
vtf download --meta meta.json      -> audio path
vtf transcribe <audio>             -> transcript.json
vtf merge < transcript.json        -> lines.json
vtf analyze --kind summary < lines.json   -> summary.json
vtf analyze --kind breakdown < lines.json -> breakdown.json
vtf analyze --kind rewrite < lines.json   -> rewrite.json
vtf assemble --meta m.json --lines l.json --analysis a1.json ...
                                   -> result.json
vtf emit < result.json
vtf emit --sink markdown < result.json
```

## analyze 子命令契约（关键）

`vtf analyze --kind summary` 输出 JSON：

```json
{
  "kind": "summary",
  "prompt": "<完整渲染的 LLM prompt>",
  "context": {"title": "...", "author": "...", "lines_count": 42},
  "schema_hint": "expected: {text, points[], tags[]}",
  "result": null
}
```

**Agent 必须执行 prompt 并把结果回填到 result 字段**，再交给 `vtf assemble`。

示例：
```json
{
  "kind": "summary",
  "prompt": "...",
  "result": {
    "text": "一句话摘要",
    "points": ["要点1", "要点2"],
    "tags": ["#Tag1", "#Tag2"]
  }
}
```

## 飞书表格配置

环境变量：
```bash
export VTF_SINK_FEISHU_BASE_TOKEN="你的base_token"
export VTF_SINK_FEISHU_TABLE_ID="你的table_id"
export VTF_SINK_FEISHU_SCHEMA="examples/schemas/baokuan.toml"
```

Legacy 别名（兼容旧配置）：
```bash
export TABLE_TOKEN="你的base_token"
export TABLE_ID="你的table_id"
```

## 环境自检

```bash
vtf doctor
```

检查 yt-dlp、FunASR、lark-cli。

## 配置文件

用户级：`~/.config/vtf/config.toml`
项目级：`./vtf.toml`

示例：
```toml
[output]
sink = "markdown"

[transcribe]
asr_model = "paraformer-zh"

[platform.bilibili]
cookies_from_browser = "chrome"

[sink.feishu]
base_token = ""
table_id = ""
schema = ""
```

## 支持平台

- B站 (bilibili.com / b23.tv)：需要浏览器 cookie
- YouTube (youtube.com / youtu.be)
- 其他 yt-dlp 支持的站点（generic fallback）