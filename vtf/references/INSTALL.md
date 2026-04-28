# AGENT_INSTALL.md - 智能体安装与配置指南

本文件专供 AI 智能体（Claude Code、Codex 等）阅读。

**核心原则：智能体应主动检测并自动配置，不要让用户手动设置。**

---

## 1. 安装 vtf

```bash
# uvx 一键安装（推荐）
uvx --from git+https://github.com/richardwild426/v2f.git vtf doctor

# 或 pip 安装
pip install git+https://github.com/richardwild426/v2f.git
vtf doctor
```

---

## 2. 智能体自动配置流程

### 2.1 检测 FunASR 环境

**智能体必须执行以下检测**，找出用户系统上哪个 Python 有 FunASR：

```bash
# 检测命令 - 按优先级尝试
for py in python3 python ~/.venv/funasr/bin/python ~/.local/share/mise/installs/python/*/bin/python; do
  if [ -x "$py" ]; then
    "$py" -c "import funasr; print(funasr.__version__)" 2>/dev/null && echo "✅ FOUND: $py"
  fi
done
```

或用 Python 一行检测：

```bash
python3 -c "
import shutil, subprocess, sys
candidates = [
  shutil.which('python3'),
  shutil.which('python'),
  '~/.venv/funasr/bin/python',
  '~/.local/share/mise/installs/python/3.*/bin/python',
]
for c in candidates:
  if not c: continue
  c = c.replace('~', '$HOME')
  try:
    r = subprocess.run([c, '-c', 'import funasr'], capture_output=True, timeout=5)
    if r.returncode == 0:
      print(f'FUNASR_PYTHON={c}')
      sys.exit(0)
  except: pass
print('FUNASR_PYTHON=NOT_FOUND')
"
```

### 2.2 自动配置 FunASR

**如果检测到 FunASR**：

写入用户级配置文件（永久生效）：

```bash
# 创建配置目录
mkdir -p ~/.config/vtf

# 写入配置
cat > ~/.config/vtf/config.toml << EOF
[transcribe]
funasr_python = "$FUNASR_PYTHON"
asr_model = "paraformer-zh"

[platform.bilibili]
cookies_from_browser = "chrome"
EOF
```

**如果未检测到 FunASR**：

智能体应主动创建专用环境：

```bash
# 创建 FunASR 专用虚拟环境
python3 -m venv ~/.venv/funasr
~/.venv/funasr/bin/pip install funasr modelscope

# 验证安装
~/.venv/funasr/bin/python -c "import funasr; print('OK')"

# 写入配置
mkdir -p ~/.config/vtf
cat > ~/.config/vtf/config.toml << EOF
[transcribe]
funasr_python = "~/.venv/funasr/bin/python"
asr_model = "paraformer-zh"
EOF
```

### 2.3 验证配置

```bash
vtf doctor
```

预期输出：
```
✅ yt-dlp: /usr/local/bin/yt-dlp
✅ FunASR: ~/.venv/funasr/bin/python (配置: funasr_python = ~/.venv/funasr/bin/python)
```

---

## 3. 安装其他依赖

### yt-dlp

```bash
pip install yt-dlp
# 或
brew install yt-dlp
```

### lark-cli（可选，飞书表格 — 机器人身份）

vtf 默认以**飞书机器人**身份写入表格（`identity = "bot"`），不需要 OAuth 用户登录。智能体配置流程：

```bash
# 1. 安装 lark-cli
npm i -g @larksuite/lark-cli      # 或 pip install lark-cli（视分发方式）

# 2. 绑定飞书应用（创建新机器人或填入已有 app 凭据）
lark-cli config init --new
# 命令会阻塞等待浏览器完成创建/授权；按提示拿到 app_id 与 app_secret 后回到终端粘贴

# 3. 验证已绑定
lark-cli config show          # 输出含 "appId": "cli_xxx" 即成功

# 4. 让 vtf 自动建好 base + table + 全部字段并回写配置
vtf init feishu
# 输出形如：
#   ✅ base_token = bascn...
#      URL: https://feishu.cn/base/...
#   ✅ table_id = tbl...
#   ✅ 已写入 ~/.config/vtf/config.toml
#
#   ⚠️  下一步（必须人工完成）：把机器人加为 base 协作者并授予「可编辑」权限
```

**最后人工步骤（飞书未开放该 OpenAPI）**：把机器人加为新 base 的协作者：

1. 浏览器打开 `vtf init feishu` 输出的 base URL
2. 右上角「···」→「更多」→「添加文档应用」
3. 搜机器人名称 → 选中 → 授予「可编辑」权限

不做这一步，写入会返回 `99991672 NoPermission`。

**已有飞书表格但字段不全**：在 `~/.config/vtf/config.toml` 填好 `base_token` / `table_id`，再跑 `vtf init feishu`，会自动 `+field-list` 检查并补齐 `baokuan.toml` 中缺失的字段（追加在表末尾，可在飞书 UI 拖动调整顺序）。

**仍想用 OAuth 用户身份**：在 `~/.config/vtf/config.toml` 加 `[sink.feishu] identity = "user"`，然后 `lark-cli auth login`。

---

## 4. 完整配置示例

智能体应生成并写入 `~/.config/vtf/config.toml`：

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

[sink.feishu]  # 可选
base_token = ""
table_id = ""
schema = "vtf/assets/examples/schemas/baokuan.toml"
identity = "bot"  # bot=机器人身份（默认，需把 app 加为 base 协作者）；user=OAuth 用户身份
```

---

## 5. 智能体配置检查清单

安装完成后，智能体应确认：

| 检查项 | 命令 | 预期结果 |
|--------|------|----------|
| vtf 已安装 | `vtf --version` | 输出版本号 |
| yt-dlp 已安装 | `yt-dlp --version` | 输出版本号 |
| FunASR 已配置 | `vtf doctor` | ✅ FunASR: ... |
| 配置文件存在 | `cat ~/.config/vtf/config.toml` | 包含 funasr_python |
| 测试转录 | `vtf fetch "https://youtu.be/dQw4w9WgXcQ"` | 输出 JSON 元数据 |

---

## 6. 快速验证流水线

```bash
# 端到端测试（跳过 AI 分析）
vtf run "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --skip summary --skip breakdown --skip rewrite \
  --sink markdown
```

---

## 7. 常见问题（智能体处理）

### B站 412 错误

**智能体操作**：
1. 确认用户 Chrome 已登录 B站
2. 写入配置：`cookies_from_browser = "chrome"`
3. 或尝试 Safari/Firefox

### FunASR 首次运行慢

首次转录会下载模型（~1GB），告知用户等待。

### macOS mise Python

mise 管理的 Python 路径：`~/.local/share/mise/installs/python/3.*/bin/python`

---

## 附录：环境变量优先级

智能体可使用环境变量临时覆盖：

| 环境变量 | 配置项 | 示例 |
|----------|--------|------|
| `VTF_TRANSCRIBE_FUNASR_PYTHON` | transcribe.funasr_python | `~/.venv/funasr/bin/python` |
| `VTF_OUTPUT_SINK` | output.sink | `markdown` / `feishu` |
| `VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER` | platform.bilibili.cookies_from_browser | `chrome` |
| `VTF_SINK_FEISHU_BASE_TOKEN` | sink.feishu.base_token | 飞书 token |
| `VTF_SINK_FEISHU_IDENTITY` | sink.feishu.identity | `bot` / `user` |

配置优先级：`环境变量 > 项目 vtf.toml > 用户 ~/.config/vtf/config.toml > 默认值`