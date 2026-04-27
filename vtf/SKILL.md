---
name: vtf
description: Video content pipeline - transcribe videos (B站/YouTube), analyze with LLM, output to markdown or Feishu table. Use when user mentions video transcription, B站/YouTube analysis, or converting video content to text/notes.
license: MIT
compatibility: Requires Python 3.11+, yt-dlp, FunASR (auto-configured)
metadata:
  author: richardwild426
  version: "1.2"
---

# vtf - 视频内容流水线

视频 URL → 转录 → AI 分析 → markdown / 飞书表格的通用流水线 CLI。

---

## 工作目录约定（智能体必读）

vtf 的"工作目录"默认是 `~/.cache/vtf/`，意味着不显式指定时所有中间产物落在缓存目录，**当前 shell `ls` 看不到**，智能体会困惑、用户会迷失。

**强制约定**：跑流水线前先建任务目录、cd 进去，所有命令统一前缀 `vtf --workdir .`：

```bash
mkdir -p ~/vtf-tasks/<video_id> && cd ~/vtf-tasks/<video_id>
vtf --workdir . fetch <url> > meta.json     # 后续每条命令同样加 --workdir .
```

下表的命令省略了前缀以保持可读，**实际执行时必须加 `vtf --workdir .`**。

## 流水线强制顺序（智能体必须按序完成全部 7 步）

> 任意一步未完成或验证未通过，**禁止**进入下一步。

| # | 步骤 | 命令 | 产物（落到 cwd） | 验证条件 |
|---|------|------|------------------|----------|
| 1 | **fetch** | `vtf --workdir . fetch <url> > meta.json` | `meta.json` | `meta.json.title` 非空，**`meta.json.thumbnail` 是封面 URL，必须保留** |
| 2 | **download** | `AUDIO=$(vtf --workdir . download --meta meta.json)` | `<video_id>.mp3` 等，路径回到 `$AUDIO` 变量 | `$AUDIO` 文件存在且 `size > 0` |
| 3 | **transcribe** | `vtf --workdir . transcribe "$AUDIO" > transcript.json` | `transcript.json` | `sentences` 数组长度 ≥ 1 |
| 4 | **merge** | `vtf --workdir . merge < transcript.json > lines.json` | `lines.json` | `lines` 数组长度 ≥ 1 |
| 5 | **analyze ×3** | `vtf --workdir . analyze --meta meta.json --kind {summary,breakdown,rewrite} < lines.json > <kind>.json` | `summary.json` `breakdown.json` `rewrite.json` | 三个文件的 `result` 字段**全部**非 null |
| 6 | **assemble** | `vtf --workdir . assemble > result.json` | `result.json` | `result.analyses` 包含 3 个键，且 `result.meta.thumbnail` 已传递 |
| 7 | **emit** | `vtf --workdir . emit < result.json > report.md` | `report.md` 或飞书行 | sink 返回成功，**输出中包含封面 URL** |

> **assemble 简化用法**：`vtf --workdir . assemble` 会自动从 workdir 收集 meta.json、lines.json、{summary,breakdown,rewrite}.json。无需再写五个参数，除非你要覆盖默认路径。

> **飞书 sink 前置（第 7 步走 feishu 才需要）**：智能体在跑 emit 之前必须确认已经完成 INSTALL.md 第 3 节的两件事：(a) `lark-cli config init --new` 绑定了飞书应用；(b) **目标 base 已添加该应用为协作者并授予可编辑权限**。否则 emit 会拿到 `99991672 NoPermission`。`vtf doctor` 在飞书未配置时会主动打印这段引导。

### 封面 URL 必须呈现给用户（关键）

**不要下载封面图**。`fetch` 已经把封面 URL 写进 `meta.json.thumbnail`，这是**必须保留并呈现给用户的数据**。

智能体最常见错误：跑完整条流水线后输出报告时**遗漏 thumbnail 字段**，让用户拿不到封面链接。

- markdown sink：报告"基本信息"段必须含**封面**字段（值为 `![](url)`，既预览又保留 URL）
- 飞书 sink：`baokuan.toml` 已映射 `封面链接 = meta.thumbnail`，无需额外处理
- 自定义输出：从 `result.meta.thumbnail` 取值，**不要丢**

如果用户问"封面在哪里"，说明流水线没把它呈现出来——立即检查 sink 渲染逻辑。

### 第 5 步"3 个 kind 都要跑"的强制规则

`vtf assemble` 会校验每个传入的 analysis 的 `result` 是否非 null，缺失会报 `analyze X result not filled`。**跑 summary 就停**是当前最常见的错误模式。

仅当用户**显式**要求时才使用 `vtf run --skip rewrite`（或 skip 其他 kind）跳过。

---

## 完成定义（智能体自查清单）

走完全部 7 步后，工作目录**必须同时存在**以下文件：

```
meta.json          # 元数据（含 thumbnail URL，封面链接来源）
audio.*            # 音频文件
transcript.json    # 原始转录
lines.json         # 合并后文本行
summary.json       # 一句话摘要 + 要点 + 标签
breakdown.json     # hook / core / cta / pros / suggestions
rewrite.json       # 二创改写文案（含 _meta.比值 自检）
result.json        # 装配产物（meta.thumbnail 已透传）
report.md          # （markdown sink）最终报告，必须含封面 URL
```

并且最终输出（report.md / 飞书行）**必须含封面 URL**。任一缺失或封面丢失说明流水线**未完成**。

---

## 安装

```bash
uvx --from git+https://github.com/richardwild426/v2f.git vtf doctor
```

**智能体自动配置 FunASR（若 doctor 报未找到）**：

```bash
# 1. 创建 FunASR 专用环境
python3 -m venv ~/.venv/funasr
~/.venv/funasr/bin/pip install funasr modelscope

# 2. 写入配置文件（永久生效）
mkdir -p ~/.config/vtf
cat > ~/.config/vtf/config.toml << 'EOF'
[transcribe]
funasr_python = "~/.venv/funasr/bin/python"
asr_model = "paraformer-zh"

[platform.bilibili]
cookies_from_browser = "chrome"
EOF

# 3. 验证
vtf doctor
```

详见 [references/INSTALL.md](references/INSTALL.md)。

---

## analyze 契约（智能体必须遵守）

`vtf analyze --kind X` 输出 JSON，`result` 字段为 null。

**智能体必须**：
1. 执行 `prompt` 字段内容（调用 LLM）
2. 把 LLM 返回的 JSON 对象**完整**填入 `result` 字段
3. 传递给 `vtf assemble`

```json
{
  "kind": "rewrite",
  "prompt": "<完整渲染的 LLM prompt>",
  "result": {"_meta": {"比值": "1.08", ...}, "text": "..."}
}
```

**rewrite 二创特别提醒**：rewrite prompt 要求改写稿字数 ≥ 原稿 × 0.95、行数严格一致。LLM 返回后请检查 `result._meta.比值` ≥ 0.95，未达标则**重新调用一次 LLM**，不要直接交付。

---

## 端到端快捷命令 `vtf run`

`vtf run <url>` 把第 1–5 步（fetch → analyze）一口气跑完，把所有产物写到 workdir 后**停下**。然后由智能体填充 `summary.json` / `breakdown.json` / `rewrite.json` 的 `result` 字段，再手工跑第 6（assemble）和第 7（emit）步。

```bash
mkdir -p ~/vtf-tasks/<video_id> && cd ~/vtf-tasks/<video_id>
vtf --workdir . run <url>
# stderr 会打印接下来的 assemble + emit 命令样例
```

`vtf run` 不调用 LLM，也不会自动收尾——这是**故意设计**：CLI 边界 = LLM 调用前一步。曾经的端到端版本会用占位符填充 result 直接交付，导致最终报告全是 `[summary placeholder]` 字面量。**不要再期待 vtf run 一条命令出报告**。

仅当用户**显式**要求时使用 `vtf run <url> --skip rewrite`（或 skip 其他 kind）。

---

## 支持平台

| 平台 | URL 格式 | 特殊要求 |
|------|----------|----------|
| B站 | bilibili.com / b23.tv | 需浏览器 Cookie（Chrome/Safari/Firefox） |
| YouTube | youtube.com / youtu.be | 无 |
| 其他 | yt-dlp 支持的任意 URL | 无（generic fallback） |

---

## 配置

环境变量（推荐）：

```bash
export VTF_TRANSCRIBE_FUNASR_PYTHON="~/.venv/funasr/bin/python"
export VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER="chrome"
export VTF_OUTPUT_SINK="markdown"  # 或 "feishu"
```

或配置文件 `~/.config/vtf/config.toml`：

```toml
[output]
sink = "markdown"

[transcribe]
funasr_python = "~/.venv/funasr/bin/python"
asr_model = "paraformer-zh"

[platform.bilibili]
cookies_from_browser = "chrome"

[sink.feishu]  # 可选
base_token = ""
table_id = ""
schema = "vtf/assets/examples/schemas/baokuan.toml"
identity = "bot"  # bot（默认）或 user
```

### 飞书 sink 走机器人身份（默认）

vtf 默认以**飞书机器人**身份调 lark-cli 写表格（`--as bot`）。智能体首次启用飞书 sink 时：

1. 跑 `lark-cli config init --new` 创建/绑定飞书应用（无需 OAuth `auth login`）
2. **在目标 Bitable 把机器人加为协作者并授予可编辑权限**（不做这步会拿到 `99991672 NoPermission`）
3. `vtf doctor` 应输出 `lark-cli: ... (appId=cli_xxx, identity=bot)`

如需切回 OAuth 用户身份：在 `[sink.feishu]` 设 `identity = "user"`，再跑 `lark-cli auth login`。

---

## 详细文档

- [references/INSTALL.md](references/INSTALL.md) - 安装与自动配置
- [references/GUIDE.md](references/GUIDE.md) - 智能体使用指南
- [references/data-shapes.md](references/data-shapes.md) - 流水线数据格式
