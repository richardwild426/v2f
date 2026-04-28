# 配置项完整参考

vtf 支持三级配置，优先级从高到低：**环境变量 > 项目 vtf.toml > 用户 ~/.config/vtf/config.toml > 默认值**。

## 配置文件位置

| 级别 | 路径 | 说明 |
|------|------|------|
| 用户级 | `~/.config/vtf/config.toml` | 推荐，所有项目共用 |
| 项目级 | `./vtf.toml` | 项目根目录，临时覆盖 |
| CLI 参数 | `vtf --config <path>` | 指定配置文件路径 |

## 示例配置

```toml
# ~/.config/vtf/config.toml
[output]
sink = "markdown"  # "markdown" 或 "feishu"

[transcribe]
funasr_python = "~/.venv/funasr/bin/python"
asr_model = "paraformer-zh"
vad_model = "fsmn-vad"
punc_model = "ct-punc"
batch_size_s = 300
corrections_file = ""

[platform.bilibili]
cookies_from_browser = "chrome"  # chrome / safari / firefox / edge
cookies_file = ""

[platform.youtube]
cookies_from_browser = ""
cookies_file = ""

[download]
audio_format = "mp3"
audio_quality = "0"  # 0 = 最高质量
retries = 3

[sink.markdown]
template = ""  # 自定义模板路径，留空使用内置模板

[sink.feishu]
base_token = ""
table_id = ""
schema = "assets/schemas/baokuan.toml"
lark_cli = "lark-cli"
identity = "bot"  # bot 或 user

[analyze.prompts]
summary = ""    # 自定义 prompt 路径，留空使用内置模板
breakdown = ""
rewrite = ""
```

## 环境变量映射

| 环境变量 | 配置项 | 类型 |
|----------|--------|------|
| `VTF_OUTPUT_SINK` | output.sink | string |
| `VTF_TRANSCRIBE_FUNASR_PYTHON` | transcribe.funasr_python | string |
| `VTF_TRANSCRIBE_ASR_MODEL` | transcribe.asr_model | string |
| `VTF_TRANSCRIBE_VAD_MODEL` | transcribe.vad_model | string |
| `VTF_TRANSCRIBE_PUNC_MODEL` | transcribe.punc_model | string |
| `VTF_TRANSCRIBE_BATCH_SIZE_S` | transcribe.batch_size_s | int |
| `VTF_TRANSCRIBE_CORRECTIONS_FILE` | transcribe.corrections_file | string |
| `VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER` | platform.bilibili.cookies_from_browser | string |
| `VTF_PLATFORM_BILIBILI_COOKIES_FILE` | platform.bilibili.cookies_file | string |
| `VTF_PLATFORM_YOUTUBE_COOKIES_FROM_BROWSER` | platform.youtube.cookies_from_browser | string |
| `VTF_PLATFORM_YOUTUBE_COOKIES_FILE` | platform.youtube.cookies_file | string |
| `VTF_DOWNLOAD_AUDIO_FORMAT` | download.audio_format | string |
| `VTF_DOWNLOAD_AUDIO_QUALITY` | download.audio_quality | string |
| `VTF_DOWNLOAD_RETRIES` | download.retries | int |
| `VTF_SINK_MARKDOWN_TEMPLATE` | sink.markdown.template | string |
| `VTF_SINK_FEISHU_BASE_TOKEN` | sink.feishu.base_token | string |
| `VTF_SINK_FEISHU_TABLE_ID` | sink.feishu.table_id | string |
| `VTF_SINK_FEISHU_SCHEMA` | sink.feishu.schema | string |
| `VTF_SINK_FEISHU_LARK_CLI` | sink.feishu.lark_cli | string |
| `VTF_SINK_FEISHU_IDENTITY` | sink.feishu.identity | string |
| `VTF_ANALYZE_PROMPTS_SUMMARY` | analyze.prompts.summary | string |
| `VTF_ANALYZE_PROMPTS_BREAKDOWN` | analyze.prompts.breakdown | string |
| `VTF_ANALYZE_PROMPTS_REWRITE` | analyze.prompts.rewrite | string |

**Legacy 别名**（仍支持，不推荐）：

| 环境变量 | 等价配置 |
|----------|----------|
| `TABLE_TOKEN` | sink.feishu.base_token |
| `TABLE_ID` | sink.feishu.table_id |

## CLI 全局参数

| 参数 | 说明 |
|------|------|
| `--config <path>` | 覆盖配置文件路径 |
| `--workdir <path>` | 中间产物目录（默认 `~/.cache/vtf/`） |
| `--json` | 日志以 JSON Lines 输出到 stderr |
| `--quiet` | 仅输出错误 |
| `--version` | 显示版本号 |
| `--help` | 命令帮助 |

## 自定义 Prompt 模板

可在 `[analyze.prompts]` 中指定自定义模板路径。模板使用 Jinja2 语法，可用变量：

| 变量 | 说明 |
|------|------|
| `{{ title }}` | 视频标题 |
| `{{ author }}` | 作者 |
| `{{ platform }}` | 平台名 |
| `{{ lines }}` | 文本行（已用 `\n` 连接） |
