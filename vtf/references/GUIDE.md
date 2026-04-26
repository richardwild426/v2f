# vtf - Agent 使用指南

通用视频内容流水线 CLI：URL → 转录 → AI 分析 → markdown / 飞书表格

---

## 安装与自动配置

**智能体应主动检测并配置 FunASR，不要让用户手动设置。**

详见 [INSTALL.md](INSTALL.md) - 包含自动检测脚本和配置写入流程。

快速安装：

```bash
uvx --from git+https://github.com/richardwild426/v2f.git vtf doctor
```

若 `doctor` 报 FunASR 未找到，智能体执行：

```bash
# 1. 创建专用环境
python3 -m venv ~/.venv/funasr
~/.venv/funasr/bin/pip install funasr

# 2. 写入配置
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

---

## 工作目录约定

不指定 `--workdir` 时产物落在 `~/.cache/vtf/`，cwd 看不到。**强制做法**：先建任务目录，cd 进去，所有命令加 `vtf --workdir .`。

```bash
mkdir -p ~/vtf-tasks/<video_id> && cd ~/vtf-tasks/<video_id>
```

## 命令清单

### 快捷端到端 `vtf run`（跑到 analyze 阶段停下）

```bash
vtf --workdir . run <url>             # 跑 fetch→download→transcribe→merge→analyze×3 后停下
vtf --workdir . run <url> --skip rewrite  # 跳过某个 analyze kind
```

`vtf run` 不会调用 LLM、不会自动 assemble/emit。stderr 会打印接下来的命令样例。**不要期待 vtf run 一条命令出报告**——CLI 边界 = LLM 调用前一步。

### 完整分步

```bash
vtf --workdir . fetch <url> > meta.json
AUDIO=$(vtf --workdir . download --meta meta.json)
vtf --workdir . transcribe "$AUDIO" > transcript.json
vtf --workdir . merge < transcript.json > lines.json
vtf --workdir . analyze --meta meta.json --kind summary < lines.json > summary.json
vtf --workdir . analyze --meta meta.json --kind breakdown < lines.json > breakdown.json
vtf --workdir . analyze --meta meta.json --kind rewrite < lines.json > rewrite.json
# 智能体调 LLM 填充三个 *.json 的 result 字段（参考 prompt 字段）
vtf --workdir . assemble --meta meta.json --lines lines.json \
    --analysis summary.json --analysis breakdown.json --analysis rewrite.json > result.json
vtf --workdir . emit < result.json > report.md
```

---

## analyze 子命令契约（关键）

`vtf analyze --kind summary` 输出 JSON：

```json
{
  "kind": "summary",
  "prompt": "<完整渲染的 LLM prompt>",
  "context": {"title": "...", "lines_count": 42},
  "schema_hint": "expected: {text, points[], tags[]}",
  "result": null
}
```

**Agent 必须执行 prompt 并把结果回填到 result 字段**，再交给 `vtf assemble`。

示例：
```json
{
  "kind": "summary",
  "result": {
    "text": "一句话摘要",
    "points": ["要点1", "要点2"],
    "tags": ["#Tag1", "#Tag2"]
  }
}
```

---

## 飞书表格配置

智能体应写入配置文件，而非让用户手动设置环境变量：

```bash
cat > ~/.config/vtf/config.toml << 'EOF'
[sink.feishu]
base_token = "your_token"
table_id = "your_table_id"
schema = "vtf/assets/examples/schemas/baokuan.toml"
EOF
```

---

## 环境自检

```bash
vtf doctor
```

检查 yt-dlp、FunASR、lark-cli。

---

## 支持平台

| 平台 | URL 格式 | 特殊要求 |
|------|----------|----------|
| B站 | bilibili.com / b23.tv | 需浏览器 Cookie（Chrome/Safari/Firefox） |
| YouTube | youtube.com / youtu.be | 无 |
| 其他 | yt-dlp 支持的任意 URL | 无（generic fallback） |