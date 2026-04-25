# vtf - Agent 使用指南

通用视频内容流水线 CLI：URL → 转录 → AI 分析 → markdown / 飞书表格

---

## 安装与自动配置

**智能体应主动检测并配置 FunASR，不要让用户手动设置。**

详见 [AGENT_INSTALL.md](AGENT_INSTALL.md) - 包含自动检测脚本和配置写入流程。

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
schema = "examples/schemas/baokuan.toml"
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