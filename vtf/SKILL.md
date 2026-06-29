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

先建任务目录并 `cd` 进去，产物默认落在当前目录（无需给命令加 `--workdir` 前缀）：

```bash
mkdir -p ~/vtf-tasks/<video_id> && cd ~/vtf-tasks/<video_id>
```

> 需要把产物放到别处时再显式传 `--workdir <path>`。

## 快速流程（三动作）

整条流水线只有一处需要智能体（填 `result`），其余都是确定性命令：

```bash
# 1. 抓取 → 下载 → 转录 → 预处理 → 生成 3 个 analyze prompt（停在 LLM 接管点）
vtf run <url>

# 2. 填充 summary.json / breakdown.json / rewrite.json 的 result 字段（唯一的 LLM 工作，见下「analyze 契约」）

# 3. 装配 + 写出报告/飞书（= assemble + emit 一步收尾）
vtf finish
```

`vtf run` 不调用 LLM、不会自动收尾——它停在 analyze 是必然的，因为 `result` 要靠智能体填；
回填后才能 `vtf finish`。run 的 stderr 会打印回填后该跑的 finish 命令。

## 分步调试（可选）

需要单独排查某一步时，用下列原子命令（run/finish 就是它们的编排）。
完整命令、产物、验证条件见 [references/pipeline.md](references/pipeline.md)。

| 命令 | 作用 |
|------|------|
| `fetch <url>` | 抓元数据 → `meta.json`（含 `thumbnail`） |
| `download --meta meta.json` | 下载音频（feishu sink 时另存视频） |
| `transcribe <audio>` | 转录 → `transcript.json` |
| `merge` | 合并字幕行 → `lines.json` |
| `analyze --kind {summary,breakdown,rewrite}` | 生成 LLM prompt（`result` 待填） |
| `assemble` | 装配 → `result.json` |
| `emit` | 写当前 sink（markdown / 飞书） |

## analyze 契约

`vtf analyze --kind X` 输出 JSON，`result` 字段为 null。**智能体必须**：

1. 执行 `prompt` 字段的内容（调用 LLM）。`result` 的形状以 prompt 要求为准。
2. 把 LLM 返回的 JSON 对象完整填入 `result` 字段
3. 如果输出包含 `required_result_fields`，逐项确认这些 `result_path` 在 `result` 里都有非空值；
   breakdown 的分镜条目带 `row_fields` 时，确认每个 shot 都含其中 `required` 的子字段
4. 三个 kind（summary, breakdown, rewrite）**全部跑**，缺一不可

```json
{"kind": "summary", "prompt": "...", "required_result_fields": [{"result_path": "text"}], "result": null}
// 智能体调 LLM 后回填：
{"kind": "summary", "prompt": "...", "result": {"text": "...", "points": [...], "tags": [...]}}
```

`required_result_fields` 由 schema（`assets/schemas/baokuan.toml`）派生，是字段契约的单一权威，
不要凭记忆硬填。残缺的 `result` 在 `vtf assemble`/`vtf finish` 阶段就会就近报错（不必等到 emit）；
飞书 sink 写入前还会再次阻断缺失的必填字段，报错列出字段名和 source path。不要把缺失字段留空后继续。

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
