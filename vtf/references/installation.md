# 安装与自动配置

本文件专供 AI 智能体阅读，包含完整的自动检测和配置流程。

## 1. 安装 vtf

```bash
uvx --from git+https://github.com/richardwild426/v2f.git vtf doctor
```

或本地开发安装：

```bash
git clone https://github.com/richardwild426/v2f.git
cd v2f
uv sync
uv run vtf doctor
```

## 2. 智能体自动配置流程

### 2.1 检测 FunASR 环境

```bash
for py in "$HOME/.venv/funasr/bin/python" python3 python; do
  case "$py" in
    */*) [ -x "$py" ] && "$py" -c "import funasr; print(funasr.__version__)" 2>/dev/null && echo "FOUND: $py" ;;
    *)   resolved="$(command -v "$py" 2>/dev/null || true)"
         [ -n "$resolved" ] && [ -x "$resolved" ] && "$resolved" -c "import funasr; print(funasr.__version__)" 2>/dev/null && echo "FOUND: $py" ;;
  esac
done
```

### 2.2 自动配置

**检测到 FunASR**：写入配置文件（永久生效）

```bash
mkdir -p ~/.config/vtf
cat > ~/.config/vtf/config.toml << EOF
[transcribe]
funasr_python = "$FUNASR_PYTHON"
asr_model = "paraformer-zh"

[platform.bilibili]
cookies_from_browser = "chrome"
EOF
```

**未检测到 FunASR**：创建专用环境

```bash
python3 -m venv ~/.venv/funasr
~/.venv/funasr/bin/pip install funasr modelscope

mkdir -p ~/.config/vtf
cat > ~/.config/vtf/config.toml << EOF
[transcribe]
funasr_python = "~/.venv/funasr/bin/python"
asr_model = "paraformer-zh"
EOF
```

### 2.3 验证

```bash
vtf doctor
```

预期输出：

```
✅ yt-dlp: /usr/local/bin/yt-dlp
✅ FunASR: ~/.venv/funasr/bin/python
```

## 3. 安装其他依赖

### yt-dlp

```bash
pip install yt-dlp
# 或
brew install yt-dlp
```

### lark-cli（可选，飞书表格）

```bash
npm i -g @larksuite/lark-cli
lark-cli config init --new   # 绑定飞书应用
lark-cli config show         # 验证：含 appId 即成功
```

然后跑 `vtf init feishu` 自动建表+字段并回写配置。详见 [feishu.md](feishu.md)。

## 4. 完整配置示例

写入 `~/.config/vtf/config.toml`：

```toml
[output]
sink = "markdown"

[transcribe]
funasr_python = "~/.venv/funasr/bin/python"
asr_model = "paraformer-zh"
vad_model = "fsmn-vad"
punc_model = "ct-punc"

[platform.bilibili]
cookies_from_browser = "chrome"

[sink.feishu]
base_token = ""
table_id = ""
schema = "assets/schemas/baokuan.toml"
identity = "bot"
```

## 5. 环境变量优先级

智能体可用环境变量临时覆盖：

| 环境变量 | 配置项 |
|----------|--------|
| `VTF_TRANSCRIBE_FUNASR_PYTHON` | transcribe.funasr_python |
| `VTF_OUTPUT_SINK` | output.sink |
| `VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER` | platform.bilibili.cookies_from_browser |
| `VTF_SINK_FEISHU_BASE_TOKEN` | sink.feishu.base_token |
| `VTF_SINK_FEISHU_IDENTITY` | sink.feishu.identity |

配置优先级：`环境变量 > 项目 vtf.toml > ~/.config/vtf/config.toml > 默认值`

## 6. 快速验证

```bash
vtf run "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

跑通 download + transcribe + merge + analyze（三个 kind 全部生成 prompt）。`vtf run` 停在 analyze 阶段等待 LLM 回填，不调用 LLM。

## 7. 常见问题

### B站 412 错误

1. 确认 Chrome 已登录 B站
2. 写入配置：`cookies_from_browser = "chrome"`
3. 或尝试 Safari/Firefox

### FunASR 首次运行慢

首次转录会下载模型（~1GB），正常现象。

### macOS mise Python

mise 管理的 Python 路径：`~/.local/share/mise/installs/python/3.*/bin/python`
