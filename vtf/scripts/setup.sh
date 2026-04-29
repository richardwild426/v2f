#!/usr/bin/env bash
# vtf 一键安装+配置脚本
# 用法: bash scripts/setup.sh
set -euo pipefail

echo "=== vtf 一键安装 ==="
echo ""

_try_python() {
    # $1 is a literal filesystem path or a command name in PATH.
    # For command names (no "/"), use "command -v" to locate.
    # For filesystem paths, use [ -x ] to check.
    local candidate="$1"
    case "$candidate" in
        */*)
            [ -x "$candidate" ] && "$candidate" -c "import funasr" 2>/dev/null
            ;;
        *)
            local resolved
            resolved="$(command -v "$candidate" 2>/dev/null || true)"
            [ -n "$resolved" ] && [ -x "$resolved" ] && "$resolved" -c "import funasr" 2>/dev/null
            ;;
    esac
}

# ---- yt-dlp ----
if command -v yt-dlp &>/dev/null; then
    echo "✅ yt-dlp: $(yt-dlp --version 2>&1 | head -1)"
else
    echo "📦 安装 yt-dlp..."
    if command -v pip &>/dev/null; then
        pip install yt-dlp
    elif command -v pip3 &>/dev/null; then
        pip3 install yt-dlp
    elif command -v brew &>/dev/null; then
        brew install yt-dlp
    else
        echo "❌ 无法自动安装 yt-dlp，请手动安装: pip install yt-dlp"
        exit 1
    fi
    echo "✅ yt-dlp 安装完成"
fi

# ---- vtf CLI ----
if command -v vtf &>/dev/null; then
    echo "✅ vtf: $(command -v vtf)"
else
    echo "📦 安装 vtf..."
    if command -v uv &>/dev/null; then
        uv tool install --from git+https://github.com/richardwild426/v2f.git vtf
    elif command -v pip &>/dev/null; then
        pip install "git+https://github.com/richardwild426/v2f.git"
    elif command -v pip3 &>/dev/null; then
        pip3 install "git+https://github.com/richardwild426/v2f.git"
    else
        echo "❌ 无法自动安装 vtf（需要 uv 或 pip），请手动安装:"
        echo "   uvx --from git+https://github.com/richardwild426/v2f.git vtf doctor"
        exit 1
    fi
    echo "✅ vtf 安装完成"
fi

# ---- FunASR ----
FUNASR_PY=""
for py in "$HOME/.venv/funasr/bin/python" python3 python; do
    if _try_python "$py"; then
        FUNASR_PY="$py"
        break
    fi
done

if [ -n "$FUNASR_PY" ]; then
    echo "✅ FunASR: $FUNASR_PY"
else
    echo "📦 创建 FunASR 专用环境..."
    python3 -m venv "$HOME/.venv/funasr"
    "$HOME/.venv/funasr/bin/pip" install funasr modelscope
    FUNASR_PY="$HOME/.venv/funasr/bin/python"
    echo "✅ FunASR 安装完成: $FUNASR_PY"
fi

# ---- 写配置 ----
CONFIG_DIR="$HOME/.config/vtf"
mkdir -p "$CONFIG_DIR"
CONFIG_FILE="$CONFIG_DIR/config.toml"

if [ -f "$CONFIG_FILE" ]; then
    echo "⚠️  配置文件已存在: $CONFIG_FILE（跳过写入）"
else
    cat > "$CONFIG_FILE" << EOF
[output]
sink = "markdown"

[transcribe]
funasr_python = "$FUNASR_PY"
asr_model = "paraformer-zh"
vad_model = "fsmn-vad"
punc_model = "ct-punc"
batch_size_s = 300

[platform.bilibili]
cookies_from_browser = "chrome"

[platform.youtube]

[download]
audio_format = "mp3"
audio_quality = "0"
retries = 3

[sink.feishu]
base_token = ""
table_id = ""
schema = "assets/schemas/baokuan.toml"
lark_cli = "lark-cli"
identity = "bot"
EOF
    echo "✅ 配置已写入: $CONFIG_FILE"
fi

# ---- 验证 ----
echo ""
echo "=== 环境验证 ==="
vtf doctor

echo ""
echo "=== 安装完成 ==="
echo "下一步: 跑 'vtf doctor' 确认环境全绿，然后参考 SKILL.md 或 README.md 开始使用。"
