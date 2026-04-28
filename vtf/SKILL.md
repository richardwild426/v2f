---
name: vtf
description: Video content pipeline - transcribe videos (Bilibili/YouTube), analyze with LLM, output to markdown or Feishu table. Use when user mentions video transcription, B站/YouTube analysis, converting video to text/notes, 视频分析, or 爆款拆解.
license: MIT
compatibility: Requires Python 3.11+, yt-dlp, FunASR (auto-configurable), lark-cli (optional for Feishu)
metadata:
  author: richardwild426
  version: "1.2"
---

# vtf - 视频内容流水线

URL → 转录 → AI 分析 → markdown / 飞书表格。CLI 跑下载+转录+预处理，智能体接管 LLM 调用，再 CLI 收尾拼装输出。

## 快速开始

```bash
# 一键安装+配置
bash scripts/setup.sh

# 验证环境
vtf doctor
```

首次使用会引导安装 yt-dlp 和 FunASR。详细见 [references/installation.md](references/installation.md)。

## 工作目录

不指定 `--workdir` 时产物落在 `~/.cache/vtf/`，cwd 不可见。**强制约定**：先建任务目录，所有命令带 `--workdir .`：

```bash
mkdir -p ~/vtf-tasks/<video_id> && cd ~/vtf-tasks/<video_id>
# 后续所有 vtf 命令前加 --workdir .
```

## 7 步流水线

> 任意一步未完成 → 禁止进入下一步。详细参考 [references/pipeline.md](references/pipeline.md)。

| # | 步骤 | 命令 | 产物 | 验证 |
|---|------|------|------|------|
| 1 | **fetch** | `vtf --workdir . fetch <url> > meta.json` | `meta.json` | `title` 非空，`thumbnail` 保留 |
| 2 | **download** | `AUDIO=$(vtf --workdir . download --meta meta.json)` | `<id>.mp3`（feishu sink 时 + `<id>.mp4`） | 文件存在且 size > 0 |
| 3 | **transcribe** | `vtf --workdir . transcribe "$AUDIO" > transcript.json` | `transcript.json` | `sentences` 长度 ≥ 1 |
| 4 | **merge** | `vtf --workdir . merge < transcript.json > lines.json` | `lines.json` | `lines` 长度 ≥ 1 |
| 5 | **analyze ×3** | `vtf --workdir . analyze --meta meta.json --kind {summary,breakdown,rewrite} < lines.json > {kind}.json` | `summary.json` `breakdown.json` `rewrite.json` | 三个文件 `result` 全部非 null |
| 6 | **assemble** | `vtf --workdir . assemble > result.json` | `result.json` | `analyses` 含 3 个 key |
| 7 | **emit** | `vtf --workdir . emit < result.json > report.md` | `report.md` 或飞书行 | 输出含封面 URL |

### 快捷命令 `vtf run`

把第 1-5 步一口气跑完，产物写到 workdir 后停下。然后智能体填充三个 `result` 字段，再手工跑 assemble + emit。

```bash
vtf --workdir . run <url>
# stderr 会打印接下来的 assemble + emit 命令样例
```

`vtf run` 不调用 LLM，不会自动收尾。不要期待一条命令出报告。

## analyze 契约

`vtf analyze --kind X` 输出 JSON，`result` 字段为 null。**智能体必须**：

1. 执行 `prompt` 字段的内容（调用 LLM）
2. 把 LLM 返回的 JSON 对象完整填入 `result` 字段
3. 三个 kind（summary, breakdown, rewrite）**全部跑**，缺一不可

```json
{"kind": "summary", "prompt": "...", "result": null}
// 智能体调 LLM 后回填：
{"kind": "summary", "prompt": "...", "result": {"text": "...", "points": [...], "tags": [...]}}
```

rewrite 的 LLM 返回后检查 `result._meta.比值` ≥ 0.95，未达标则重调一次。

## 封面 URL 规则

**不放缩略图**。`fetch` 已把封面 URL 写进 `meta.json.thumbnail`，这是必须呈现给用户的数据。markdown sink 在报告里用 `![封面](url)<br>url` 呈现；飞书 sink 通过 schema 映射 `meta.thumbnail` 到封面链接列。**不要遗漏**。

## 飞书 sink 前置条件

走 `feishu` sink 前必须：

1. `lark-cli config init --new` 绑定飞书应用（一次性）
2. `vtf init feishu` 自动建表+字段并回写配置
3. 把机器人加为 base 协作者并授予「可编辑」权限（飞书未开放该 OpenAPI，需人工）

跳过第 2 步直接 emit 会报 `1254045 字段名不存在`。详见 [references/feishu.md](references/feishu.md)。

## 完成定义

工作目录必须同时存在以下文件，且最终输出含封面 URL：

```
meta.json  transcript.json  lines.json
summary.json  breakdown.json  rewrite.json
result.json  report.md
```

任一缺失视为未完成。

## 支持平台

| 平台 | URL 格式 | 特殊要求 |
|------|----------|----------|
| B站 | bilibili.com / b23.tv | 浏览器 Cookie（Chrome/Safari/Firefox） |
| YouTube | youtube.com / youtu.be | 无 |
| 其他 | yt-dlp 支持的任意 URL | 无 |

## 参考文档

- [references/pipeline.md](references/pipeline.md) — 7 步流水线详细说明
- [references/installation.md](references/installation.md) — 安装与自动配置
- [references/feishu.md](references/feishu.md) — 飞书 sink 配置
- [references/data-shapes.md](references/data-shapes.md) — 数据格式契约
- [references/configuration.md](references/configuration.md) — 配置项完整参考
- [references/troubleshooting.md](references/troubleshooting.md) — 常见问题
