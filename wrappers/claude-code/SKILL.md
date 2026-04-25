---
name: vtf
description: 视频 → 转录 → AI 分析 → markdown / 飞书表格的通用流水线 CLI
tags: [video, transcription, funasr, feishu, bitable, content-analysis, bilibili, youtube]
category: media
---

# vtf - 视频内容流水线

## 安装

```bash
uvx --from git+https://github.com/richardwild426/v2f.git vtf doctor
```

## 智能体自动配置 FunASR

**若 doctor 报 FunASR 未找到，智能体应主动创建环境并配置：**

```bash
# 1. 创建 FunASR 专用环境
python3 -m venv ~/.venv/funasr
~/.venv/funasr/bin/pip install funasr

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

详见 [AGENT_INSTALL.md](../../AGENT_INSTALL.md)。

---

## 命令

| 命令 | 说明 |
|------|------|
| `vtf run <url>` | 端到端 |
| `vtf fetch <url>` | 元数据 |
| `vtf transcribe <audio>` | 转录 |
| `vtf analyze --kind X` | LLM prompt |
| `vtf emit --sink X` | 输出 |
| `vtf doctor` | 环境检查 |

---

## analyze 契约（智能体必须遵守）

`vtf analyze --kind summary` 输出 JSON，`result` 字段为 null。

**智能体必须**：
1. 执行 `prompt` 字段内容（调用 LLM）
2. 将结果填入 `result` 字段
3. 传递给 `vtf assemble`

```json
{
  "kind": "summary",
  "result": {"text": "...", "points": [...], "tags": [...]}
}
```