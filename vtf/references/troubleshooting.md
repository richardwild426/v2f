# 常见问题

## B站 412 错误

B站要求浏览器 Cookie 验证。

**解决**：
1. 确认浏览器（Chrome/Safari/Firefox）已登录 B站
2. 配置：`cookies_from_browser = "chrome"`（在 `~/.config/vtf/config.toml`）
3. 或尝试其他浏览器：safari, firefox, edge

## FunASR 找不到

`vtf doctor` 显示 `❌ FunASR: 未找到`。

**解决**：

```bash
# 创建专用环境
python3 -m venv ~/.venv/funasr
~/.venv/funasr/bin/pip install funasr modelscope

# 写入配置
mkdir -p ~/.config/vtf
cat > ~/.config/vtf/config.toml << 'EOF'
[transcribe]
funasr_python = "~/.venv/funasr/bin/python"
asr_model = "paraformer-zh"
EOF

# 验证
vtf doctor
```

或者设环境变量：`export VTF_TRANSCRIBE_FUNASR_PYTHON=~/.venv/funasr/bin/python`

## FunASR 首次运行慢

首次调用 `vtf transcribe` 会自动下载模型文件（~1GB），耗时较长。后续调用直接使用缓存。

## yt-dlp 下载失败

**常见原因**：
- 网络问题：重试或使用代理
- Cookie 过期（B站）：重新登录浏览器
- 视频已删除/私密：检查 URL

**重试机制**：`download.retries = 3`（默认重试 3 次）

## 飞书写入 Permission denied (99991672)

机器人对 base 没有写权限。

**解决**：
1. 浏览器打开 base URL
2. 右上角「···」→「更多」→「添加文档应用」
3. 搜机器人名称 → 选中 → 授予「可编辑」权限

如果 `identity = "user"`，确认已跑 `lark-cli auth login` 且用户对该 base 有可编辑权限。

## 飞书字段名不存在 (1254045)

表格中缺少 schema 定义的字段。

**解决**：运行 `vtf init feishu` 自动补齐缺失字段。

## lark-cli 未绑定应用

`vtf doctor` 显示 `⚠️ lark-cli: (未绑定应用)`。

**解决**：`lark-cli config init --new`，按提示创建/绑定飞书应用。

## analyze result not filled

`vtf assemble` 报 `analyze X result not filled`。

**原因**：智能体未填充某个 analysis 的 `result` 字段。

**解决**：确保三个 kind（summary, breakdown, rewrite）全部已调 LLM 并回填 result。

## rewrite 比值不达标

LLM 返回的改写稿字数比值 < 0.95。

**解决**：通知 LLM 比值不够，要求它**增加内容密度**（而非添加冗余词），重新生成。

## macOS mise Python

mise 管理的 Python 路径特殊：`~/.local/share/mise/installs/python/3.*/bin/python`

```bash
export VTF_TRANSCRIBE_FUNASR_PYTHON="$HOME/.local/share/mise/installs/python/3.11/bin/python"
```
