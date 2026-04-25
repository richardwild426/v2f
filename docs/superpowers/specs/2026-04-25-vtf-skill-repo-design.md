# vtf 通用技能仓库 - 设计文档

- **日期**:2026-04-25
- **状态**:草案待 review
- **范围**:把当前的单文件 `SKILL.md` 改写为脚本驱动、平台无关的技能仓库,优先支持 Claude Code 与 Codex 两个智能体平台,扩展到其他平台只需新增 wrapper 模板。

## 1. 背景

当前项目 `/Users/zvector/ws/video-to-feishu/` 仅包含一份 30KB 的 `SKILL.md`,描述视频(B站 / YouTube)→ FunASR 转录 → AI 分析 → 飞书多维表格的流水线。它是文档驱动的"操作手册",依赖宿主智能体逐步执行其中的 shell/python 片段。

存在的问题:
- **硬编码严重**:macOS 个人 Python 路径、`--cookies-from-browser chrome`、`/tmp` 工作区、`lark-cli` 命令、19 个中文飞书字段名、`paraformer-zh` 模型等,全部写死。
- **平台耦合**:输出环节锁死飞书,markdown 仅作为降级。
- **不可分发**:智能体只能"读懂并照做",没有可执行入口,无法被其他智能体直接安装调用。
- **维护分散**:多个降级路径与备用方案散落在文档中,难以测试。

## 2. 目标与非目标

### 目标

1. 提供一个 `vtf` CLI,把流水线核心逻辑封装为标准命令(端到端 + 分步均可)。
2. 任何能运行 shell 的智能体都能调用,**无平台锁定**。
3. 优先适配 Claude Code、Codex 两个平台的 skill/agent 加载机制,提供开箱即用的 wrapper。
4. 用户可在飞书 sink 与 markdown sink 之间自由切换;有飞书配置时默认走飞书,失败自动降级 markdown 并提示。
5. 所有可变值(路径、模型、cookie 浏览器、CLI 名、字段 schema、prompts)走配置文件 / 环境变量 / CLI flag,**代码内零硬编码业务值**。
6. AI 分析步骤不绑定 LLM provider:CLI 仅生产 prompt + context,由宿主智能体调用其 LLM 完成。

### 非目标

- **不**内置 LLM 调用(YAGNI;有需要时再加)。
- **不**做 sink 插件市场(只需 markdown + feishu;后续按需扩展)。
- **不**强求支持 yt-dlp 之外的下载器。
- **不**支持非 Python 实现(FunASR / yt-dlp 都是 Python 生态)。

## 3. 架构

### 3.1 仓库结构

```
vtf/
├── pyproject.toml              # uv/uvx 入口,依赖
├── README.md                   # 用户视角:这是什么、怎么装
├── AGENT_GUIDE.md              # 智能体视角:平台无关的核心引导
├── src/vtf/
│   ├── __main__.py             # python -m vtf 入口
│   ├── cli.py                  # 子命令路由(Click 或 Typer)
│   ├── config.py               # 三级配置加载与合并
│   ├── platforms/
│   │   ├── base.py             # Platform protocol(detect/quirks)
│   │   ├── bilibili.py         # 需要 cookie 的提取器
│   │   ├── youtube.py
│   │   └── generic.py          # 任意 yt-dlp 支持的站点
│   ├── transcribe/
│   │   └── funasr.py           # FunASR 包装 + Python 路径自动探测
│   ├── pipeline/
│   │   ├── fetch.py            # yt-dlp -J 取元数据
│   │   ├── download.py         # 下载音频
│   │   ├── merge.py            # 句子碎片合并
│   │   ├── analyze.py          # 生成 prompt + context(不调 LLM)
│   │   └── assemble.py         # 拼装最终 result.json
│   ├── sinks/
│   │   ├── base.py             # Sink protocol(emit / available)
│   │   ├── markdown.py
│   │   └── feishu.py           # 调用 $VTF_LARK_CLI(可替换)
│   ├── prompts/
│   │   ├── summary.md          # 摘要 + 标签
│   │   ├── breakdown.md        # Hook/Core/CTA
│   │   └── rewrite.md          # 二创改写
│   └── doctor.py               # 环境自检 + 修复建议
├── wrappers/
│   ├── claude-code/
│   │   └── SKILL.md            # frontmatter + 引用 AGENT_GUIDE.md
│   ├── codex/
│   │   └── AGENTS.md           # Codex 格式 + 引用 AGENT_GUIDE.md
│   └── generic/
│       └── README.md           # "把 AGENT_GUIDE.md 给你的 agent 读"
├── examples/
│   └── schemas/
│       └── baokuan.toml        # 「爆款制造机」19 字段示例(非默认)
├── tests/
│   ├── test_pipeline.py
│   ├── test_sinks.py
│   ├── test_config.py
│   └── fixtures/
└── docs/
    ├── install.md              # Claude Code / Codex / 其他平台安装步骤
    ├── configuration.md        # 配置字段全表
    └── extending.md            # 加新 platform / sink 的契约
```

### 3.2 数据流

```
URL ──fetch──> meta.json ──download──> audio.mp3
                                          │
                                       transcribe
                                          │
                                          v
                                     transcript.json (sentences[])
                                          │
                                        merge
                                          │
                                          v
                                      lines.json
                                          │
                          ┌───────────────┼───────────────┐
                          v               v               v
                       analyze          analyze         analyze
                       (summary)       (breakdown)     (rewrite)
                          │               │               │
                          └───────────────┼───────────────┘
                                          v
                       agent 跑 LLM,把每个 analysis.result 填回
                                          │
                                          v
                                       assemble (+ meta + lines)
                                          │
                                          v
                                       result.json
                                          │
                                         emit
                                          │
                                          v
                                  当前 sink (md / feishu)
```

每步以 JSON 通过 stdin/stdout 流转,中间产物可缓存到 `--workdir`,支持 `vtf run --resume`。

## 4. CLI 命令面

### 4.1 端到端

```
vtf run <url>                      # 用配置好的 sink
vtf run <url> --sink markdown      # 临时切 sink
vtf run <url> --sink feishu
vtf run <url> --resume             # 复用 workdir 中已有的中间产物
vtf run <url> --skip rewrite       # 跳过某个 analyze kind
```

### 4.2 分步

```
vtf fetch <url>                    -> meta.json
vtf download --meta meta.json      -> audio path on stdout
vtf transcribe <audio>             -> transcript.json
vtf merge < transcript.json        -> lines.json
vtf analyze --kind summary    < lines.json   -> summary.json
vtf analyze --kind breakdown  < lines.json   -> breakdown.json
vtf analyze --kind rewrite    < lines.json   -> rewrite.json
vtf assemble --meta m.json --lines l.json --analysis a1.json --analysis a2.json ...
                                   -> result.json
vtf emit < result.json
vtf emit --sink markdown < result.json
```

`vtf analyze` 输出:
```json
{
  "kind": "summary",
  "prompt": "<填好上下文的 prompt 文本>",
  "context": {"title": "...", "author": "...", "lines": [...]},
  "schema_hint": "expected output: {summary, points[], tags[]}",
  "result": null
}
```
宿主智能体调 LLM 后把 `result` 填上,再交给 `vtf assemble`。

### 4.3 配置与管理

```
vtf init feishu                    # 交互式向导:base_token / table_id / schema 路径
vtf config list
vtf config get <key>
vtf config set <key> <value>
vtf config unset <key>
vtf install <platform>             # 复制 wrappers/<platform>/* 到目标 skill 目录
vtf doctor                         # 检查 funasr / yt-dlp / lark-cli + 给出修复建议
vtf version
```

### 4.4 全局 flags

- `--config <path>`:覆盖配置文件位置
- `--workdir <path>`:中间产物目录(默认 `${XDG_CACHE_HOME:-~/.cache}/vtf/<job-id>/`)
- `--json`:所有日志走 JSON Lines 到 stderr,便于 agent 解析
- `--quiet`:仅输出错误
- `--dry-run`:打印计划动作,不执行

## 5. 配置模型

### 5.1 三级覆盖优先级(高 → 低)

1. CLI flag(`--sink`、`--workdir`、…)
2. 环境变量(`VTF_*`)
3. 项目级 `./vtf.toml`(若存在)
4. 用户级 `${XDG_CONFIG_HOME:-~/.config}/vtf/config.toml`
5. 内置默认

### 5.2 配置字段

```toml
# ~/.config/vtf/config.toml(示例)

[output]
sink = "markdown"                    # 或 "feishu"

[transcribe]
funasr_python = ""                   # 留空则自动探测
asr_model = "paraformer-zh"          # 任意 FunASR 兼容模型
vad_model = "fsmn-vad"
punc_model = "ct-punc"
batch_size_s = 300

[transcribe.corrections]
file = ""                            # 纠错字典 JSON 路径

[platform.bilibili]
cookies_from_browser = "chrome"      # chrome | safari | firefox | edge | ""(不带 cookie)
cookies_file = ""                    # 二选一:直接给 cookie 文件路径

[platform.youtube]
cookies_from_browser = ""

[download]
audio_format = "mp3"
audio_quality = "0"
retries = 3

[sink.markdown]
template = ""                        # 留空使用内置模板;否则指向自定义 .md.j2

[sink.feishu]
base_token = ""                      # 由 `vtf init feishu` 写入
table_id = ""
schema = ""                          # 必填,指向 fields schema toml
lark_cli = "lark-cli"                # 可替换为 oapi、自封装命令等
```

### 5.3 环境变量映射

每个配置键都有对应的 `VTF_<SECTION>_<KEY>` 环境变量,例如:
- `VTF_OUTPUT_SINK=feishu`
- `VTF_TRANSCRIBE_FUNASR_PYTHON=/path/to/python`
- `VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER=safari`
- `VTF_SINK_FEISHU_BASE_TOKEN=...`
- `VTF_SINK_FEISHU_LARK_CLI=oapi`

为兼容 Step 0 中已有的引导,**保留** `TABLE_TOKEN` / `TABLE_ID` 作为别名,但内部转换为 `VTF_SINK_FEISHU_*`。

## 6. 平台模型(视频源)

### 6.1 检测

```python
class Platform(Protocol):
    name: str
    def matches(url: str) -> bool: ...
    def cookie_args(cfg) -> list[str]: ...   # 给 yt-dlp 的额外 args
    def metadata_normalize(raw: dict) -> dict: ...
```

内置:
- `bilibili`:`bilibili.com|b23.tv` → 强制 cookie(默认 chrome,可改);favorite/share 设 0。
- `youtube`:`youtube.com|youtu.be` → cookie 默认关闭;favorite/share 设 0,reply 取 comment_count。
- `generic`:fallback,任何 yt-dlp 能识别的 URL 都走通用路径,不带 cookie。

### 6.2 关键经验编码到代码

- B站 `view` API 的 412 问题在原文档里多处提及。新版**仅**使用 `yt-dlp -J`,代码不再保留备用 API 路径(降低维护面)。
- 浏览器搜索找 UID、yt-dlp `--flat-playlist` 找最新视频等"发现"逻辑作为 `vtf find` 后续命令(本期非目标,文档中标记为 future work)。

## 7. Sink 模型

### 7.1 接口

```python
class Sink(Protocol):
    name: str
    def available(cfg) -> tuple[bool, str]: ...  # (是否可用, 原因)
    def emit(result: dict, cfg) -> EmitOutcome: ...
```

### 7.2 markdown sink

- 模板默认内置(对应原 6.4 的格式)。
- 通过 `[sink.markdown] template = "..."` 指向自定义 Jinja2 文件覆盖。
- 输出到 stdout,智能体决定怎么落盘 / 转发。

### 7.3 feishu sink

- 必需 `base_token` + `table_id` + `schema`(三者缺一拒绝运行,明确报错"请跑 `vtf init feishu`")。
- `schema` 是一个独立 toml,描述 N 个字段(name/type/source),示例见 `examples/schemas/baokuan.toml`。代码不内置任何字段名。
- 写入命令模板:`{lark_cli} base +record-batch-create --base-token {tok} --table-id {tid} --json {payload}` —— `lark_cli` 名字与参数 schema 都来自配置/schema 文件,可替换。
- 失败时:stderr 打印诊断(命令、退出码、stderr 摘要)+ 修复建议,**自动降级 markdown 到 stdout**。退出码仍为 0(数据没丢),但在 `--json` 模式下会输出一条 `{"level":"warn","step":"emit","msg":"feishu degraded","data":{...}}` 日志,供 agent 编程感知。

### 7.4 schema 文件契约

```toml
# examples/schemas/baokuan.toml
[[fields]]
name = "对标素材链接"
type = "text"
source = "meta.url"

[[fields]]
name = "标题"
type = "text"
source = "meta.title"

[[fields]]
name = "文案提取"
type = "text"
source = "lines.joined"        # 内置 transformer

[[fields]]
name = "摘要"
type = "text"
source = "analyses.summary.text"

[[fields]]
name = "标签"
type = "text"
source = "analyses.summary.tags | tags_hashtag"

[[fields]]
name = "发布时间"
type = "datetime"
source = "meta.upload_date"

# ... 用户自由增删
```

`source` 支持点路径表达 + 管道形式的内置 transformer(`joined`、`tags_hashtag`、`stats_compact`)。`assemble` 步骤产出的 `result.json` 结构固定为:

```json
{
  "meta": { "url": "...", "title": "...", ... },
  "lines": ["...", "..."],
  "analyses": {
    "summary":   { "text": "...", "points": [...], "tags": [...] },
    "breakdown": { "text": "...", "hook": "...", ... },
    "rewrite":   { "text": "..." }
  }
}
```

完整 schema 渲染规范在 `docs/extending.md`。

## 8. Prompts

三个 markdown 文件,放在 `src/vtf/prompts/`:
- `summary.md`:对应原 5.1
- `breakdown.md`:对应原 5.2
- `rewrite.md`:对应原 5.3(AI 红发魔女风格,但**不是默认**,仅作示例;config 可换路径)

每个 prompt 文件用 `{{ title }}`、`{{ author }}`、`{{ lines }}` 等占位符,由 `vtf analyze` 渲染后输出到 `analysis.json` 的 `prompt` 字段。

用户覆盖方式:
```toml
[analyze.prompts]
summary = "/path/to/my-summary.md"
rewrite = ""                         # 留空 = 跳过这一类
```

## 9. 错误处理与可观测性

- 所有错误走 `stderr`,stdout 只放结构化数据,保证 stdin/stdout 管道不被污染。
- 每个外部命令调用前先 `vtf doctor` 子检查;失败时打印**完整修复指南**(文档锚点 + 推荐命令)。
- 关键日志:`{"ts": "...", "step": "transcribe", "level": "info", "msg": "...", "data": {...}}`(--json 模式)。
- 退出码:0 = 成功;1 = 用户错误(配置/参数);2 = 环境错误(缺依赖);3 = 远程错误(网络/API);4 = 内部 bug。

## 10. 安装与平台 wrapper

### 10.1 安装方式

主推 `uvx`:
```
uvx --from git+<repo-url> vtf init
uvx --from git+<repo-url> vtf doctor
```

> `<repo-url>` 是仓库发布后才确定的占位符(本仓库目前无远端)。文档在仓库初始化时由 `make docs` 替换为真实 URL,或保留 `<repo-url>` 让用户填写自己的 fork。

也支持本地开发:
```
git clone <repo-url> vtf && cd vtf && uv sync && uv run vtf doctor
```

### 10.2 wrapper 模板(原则:薄壳 + 引用核心)

`wrappers/claude-code/SKILL.md`(frontmatter 走 Claude Code 约定):
```markdown
---
name: vtf
description: 视频 → 转录 → AI 分析 → markdown / 飞书表格的通用流水线
---

# 使用 vtf

通过 `uvx --from <repo> vtf <subcommand>` 调用。

@AGENT_GUIDE.md
```

`wrappers/codex/AGENTS.md`(Codex 约定的精简形式):
```markdown
# vtf - 视频内容流水线

调用方式:`uvx --from <repo> vtf <subcommand>`

详见 AGENT_GUIDE.md 的命令清单与 workflow。

<!-- AGENT_GUIDE.md 内容追加在此或独立放置 -->
```

`vtf install <platform>` 行为:

1. **目标目录优先级**(先选可写的第一个):
   - Claude Code:`--target` flag > `$CLAUDE_PROJECT_DIR/.claude/skills/vtf/` > `~/.claude/skills/vtf/`
   - Codex:`--target` flag > 工程根目录的 `AGENTS.md`(追加而非覆盖) > `~/.codex/agents/vtf/`(若存在)
2. 复制 `wrappers/<platform>/*` + `AGENT_GUIDE.md` 到目标位置。Codex 模式下,把 wrapper 内容**追加**到工程根 `AGENTS.md`,加节标题 `## vtf` 防止覆盖既有内容。
3. 任何路径不存在或不可写时,**不创建任何文件**,而是打印"请手动 cp `<source>` 到 `<dest>`"指引,退出码 0。
4. `--dry-run` 仅打印将做的动作。
5. 仅写入声明清单内的文件,绝不修改其他配置。

### 10.3 AGENT_GUIDE.md 内容大纲

- 何时用本技能(triggers)
- 命令清单(table)
- 典型 workflow:`run` 一条龙、分步重跑分析、初次配置飞书
- 飞书写入失败如何感知与处理
- analyze 子命令的 prompt + result 回填契约(对 agent 强调:**你需要执行 prompt 并把结果回填**)
- 环境自检入口(`vtf doctor`)

## 11. 测试策略

- **单元**:平台 metadata 归一化、merge 算法、schema 渲染、配置三级合并。
- **契约**:`vtf analyze --kind X` 的输出 JSON shape;sink 接口实现。
- **集成**:fixture 化的元数据 / transcript,跑完整 `vtf run --offline` 链路(不真实下载、不真实转录,通过插桩)。
- **smoke**:`vtf doctor` 在缺依赖时给出正确建议。
- **不**做:真实 yt-dlp 下载、真实 FunASR 转录、真实飞书 API(在 CI 中跳过,提供本地 `make e2e` 入口)。

## 12. 向后兼容与迁移

- 当前的 `SKILL.md` 在新仓库中保留为 `docs/legacy/SKILL.md.archive.md`,作为历史参考。
- `TABLE_TOKEN` / `TABLE_ID` 环境变量保留为 `VTF_SINK_FEISHU_*` 的别名一个版本周期,deprecation 警告打到 stderr。
- 「爆款制造机」字段 schema 完整迁移为 `examples/schemas/baokuan.toml`,**不是**默认值,文档明确指出"想复用原行为请 `--schema examples/schemas/baokuan.toml`"。

## 13. 风险与未决项

- **uv 不可用环境**:fallback 到 `pip install -e .` 路径,文档提供两种安装方式。
- **FunASR 体积**:首次运行下载模型,文档提示用户。`vtf doctor` 显示模型缓存位置。
- **Codex skill 加载机制不稳定**:Codex 的 `AGENTS.md` 约定可能随版本变化,wrapper 设计要保证手动 cp 也能工作,不依赖 `vtf install` 自动化。
- **lark-cli 不是该仓库一部分**:用户需自己装并登录;`vtf doctor` 检查 `--version` + `auth status`(命令名走配置)。

## 14. 交付物清单

按实施计划拆解(下一步由 writing-plans 技能产出):

1. `pyproject.toml` + 项目骨架
2. `config.py` 三级合并
3. `pipeline/` 五个步骤的最小可运行版本
4. `platforms/` 三个内置实现
5. `transcribe/funasr.py` + Python 路径自动探测
6. `sinks/markdown.py` + `sinks/feishu.py` + schema renderer
7. `prompts/` 三个模板 + analyze 输出契约
8. `cli.py` + 全部子命令
9. `doctor.py` + 修复建议
10. `wrappers/claude-code/` + `wrappers/codex/`
11. `examples/schemas/baokuan.toml`
12. `tests/` 覆盖单元 + 契约 + 集成
13. `README.md` + `AGENT_GUIDE.md` + `docs/install.md` + `docs/configuration.md` + `docs/extending.md`
14. 把当前 `SKILL.md` 归档到 `docs/legacy/`
