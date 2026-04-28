# 流水线详细参考

7 步流水线的完整说明，包括命令细节、验证条件、常见错误。

## 工作目录约定

不指定 `--workdir` 时产物落在 `~/.cache/vtf/`，不会被 cwd 的 `ls` 看到。**强制做法**：先建任务目录，cd 进去，所有命令加 `vtf --workdir .`。

```bash
mkdir -p ~/vtf-tasks/<video_id> && cd ~/vtf-tasks/<video_id>
```

## 第 1 步：fetch（抓取元数据）

```bash
vtf --workdir . fetch <url> > meta.json
```

**产物**：`meta.json`

**验证**：`meta.json.title` 非空，`meta.json.thumbnail` 是封面 URL（必须保留，不要下载封面图）。

**支持的 URL**：B站 (bilibili.com / b23.tv)、YouTube (youtube.com / youtu.be)、yt-dlp 支持的任何 URL。

## 第 2 步：download（下载音频）

```bash
AUDIO=$(vtf --workdir . download --meta meta.json)
```

**产物**：`<video_id>.mp3`，路径回到 `$AUDIO` 变量。

**飞书 sink 特殊行为**：当 `output.sink = "feishu"` 时，同时下载原视频 `<video_id>.mp4` 并把路径回填到 `meta.json.video_path`（用于附件字段）。

**验证**：`$AUDIO` 文件存在且 size > 0；feishu sink 时 `meta.json.video_path` 也应非空。

## 第 3 步：transcribe（转录）

```bash
vtf --workdir . transcribe "$AUDIO" > transcript.json
```

**产物**：`transcript.json`

**验证**：`sentences` 数组长度 ≥ 1。

**前置**：需要 FunASR 安装到某 Python 环境。首次转录会下载模型（~1GB），耗时较长。

## 第 4 步：merge（合并句子）

```bash
vtf --workdir . merge < transcript.json > lines.json
```

**产物**：`lines.json`

**验证**：`lines` 数组长度 ≥ 1。

将转录的短句按语义合并为字幕行，处理标点、括号嵌套。

## 第 5 步：analyze ×3（生成 LLM prompt）

```bash
vtf --workdir . analyze --meta meta.json --kind summary < lines.json > summary.json
vtf --workdir . analyze --meta meta.json --kind breakdown < lines.json > breakdown.json
vtf --workdir . analyze --meta meta.json --kind rewrite < lines.json > rewrite.json
```

**产物**：`summary.json`, `breakdown.json`, `rewrite.json`

**三个 kind 都要跑**，缺一不可。仅当用户显式要求时才 skip。

**验证**：三个文件的 `result` 字段全部非 null。

### analyze 输出格式

```json
{
  "kind": "summary",
  "prompt": "<完整渲染的 LLM prompt>",
  "context": {"title": "...", "author": "...", "platform": "...", "lines_count": 42},
  "schema_hint": "expected: {text, points[], tags[]}",
  "result": null
}
```

**智能体职责**：
1. 执行 `prompt` 字段内容（调用 LLM）
2. 把 LLM 返回的 JSON 对象完整填入 `result` 字段
3. summary → `{text, points[], tags[]}`
4. breakdown → `{hook, core, cta, pros, suggestions, text}`
5. rewrite → `{text, _meta: {thinking, 原稿总字数, 改写总字数, 比值}}`

### rewrite 额外检查

rewrite prompt 要求改写稿字数 ≥ 原稿 × 0.95。LLM 返回后检查 `result._meta.比值` ≥ 0.95，未达标则**重新调用一次 LLM**。

## 第 6 步：assemble（装配）

```bash
vtf --workdir . assemble > result.json
```

assemble 自动从 workdir 收集 `meta.json`、`lines.json`、`{summary,breakdown,rewrite}.json`。也可显式传 `--meta` / `--lines` / `--analysis` 覆盖。

**产物**：`result.json`

**验证**：`result.analyses` 包含 summary、breakdown、rewrite 三个键，且 `result.meta.thumbnail` 已传递。

## 第 7 步：emit（输出）

```bash
# markdown sink
vtf --workdir . emit < result.json > report.md

# feishu sink（直接写飞书表格，无 stdout 产物）
vtf --workdir . emit < result.json
```

**产物**：`report.md`（markdown）或飞书行（feishu）

**验证**：sink 返回成功，输出中**包含封面 URL**。

## 快捷命令 `vtf run`

```bash
vtf --workdir . run <url>
```

把第 1-5 步一口气跑完，产物写到 workdir 后停下。stderr 会打印接下来的 assemble + emit 命令样例。然后由智能体填充 result 字段，再手工跑第 6、7 步。

`vtf run` 不调用 LLM，不会自动收尾。**不要期待一条命令出报告**。

仅当用户显式要求时使用 `vtf run <url> --skip rewrite`。

## 完成定义

工作目录必须同时存在以下文件，且最终输出含封面 URL：

```
meta.json          # 含 thumbnail URL
audio.*            # 音频文件
transcript.json    # 原始转录
lines.json         # 合并文本行
summary.json       # result 已填充
breakdown.json     # result 已填充
rewrite.json       # result 已填充
result.json        # meta.thumbnail 已透传
report.md          # （markdown sink）含封面 URL
```

## 封面 URL 规则

`fetch` 已把封面 URL 写进 `meta.json.thumbnail`。不要下载封面图，直接使用 URL。

- markdown sink：报告「基本信息」段必须含 `![封面](url)<br>url`
- 飞书 sink：schema 的 `封面链接` 字段已映射 `meta.thumbnail`，无需额外处理
- 自定义输出：从 `result.meta.thumbnail` 取值
