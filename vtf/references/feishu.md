# 飞书 Sink 接入

将分析结果写入飞书多维表格（Base）。vtf 默认以**机器人**身份（`identity=bot`）调用 lark-cli，无需 OAuth 用户登录。

## 前置条件

1. 安装 lark-cli 并绑定飞书应用
2. 运行 `vtf init feishu` 自动建表+字段
3. 人工把机器人加为 base 协作者

## 步骤 1：绑定飞书应用（一次性）

```bash
# 安装 lark-cli
npm i -g @larksuite/lark-cli

# 绑定飞书应用（创建新机器人或填入已有 app 凭据）
lark-cli config init --new

# 验证
lark-cli config show   # 输出含 "appId": "cli_xxx" 即成功
```

## 步骤 2：自动建表

```bash
vtf init feishu
```

会自动创建 base + table，按 schema 建好全部字段，并回写 `~/.config/vtf/config.toml`。

输出示例：

```
✅ base_token = bascn...
   URL: https://feishu.cn/base/...
✅ table_id = tbl...
✅ 已写入 ~/.config/vtf/config.toml

⚠️  下一步（必须人工完成）：把机器人加为 base 协作者并授予「可编辑」权限
```

**已有 base_token 但字段不全？** 同样跑 `vtf init feishu`，会自动检测缺失字段并补齐（追加在表末尾）。

## 步骤 3：人工授权（飞书未开放该 OpenAPI）

1. 浏览器打开 `vtf init feishu` 输出的 base URL
2. 右上角「···」→「更多」→「添加文档应用」
3. 搜机器人名称 → 选中 → 授予「可编辑」权限

不完成这一步，写入会返回 `99991672 NoPermission`。

## 步骤 4：验证

```bash
vtf doctor
```

应输出：

```
✅ lark-cli: /path/to/lark-cli (appId=cli_xxx, identity=bot)
   ℹ️  机器人身份：请确认目标 base 已添加该应用为协作者并授予可编辑权限
```

## 配置说明

```toml
[sink.feishu]
base_token = "bascn..."    # 飞书多维表格 token
table_id = "tbl..."        # 数据表 ID
schema = "assets/schemas/baokuan.toml"  # 字段映射文件
identity = "bot"           # bot（推荐）或 user
```

### identity 模式

| 模式 | 说明 | 登录方式 |
|------|------|----------|
| `bot` (默认) | 机器人身份，写入飞书表格 | `lark-cli config init --new` |
| `user` | OAuth 用户身份 | `lark-cli auth login` |

默认用 `bot` 模式。如需切到 user 模式，在 `[sink.feishu]` 中设 `identity = "user"` 并跑 `lark-cli auth login`。

## 自定义 Schema

Schema 是 TOML 文件，定义飞书表字段到 result.json 的数据路径映射。参考 [assets/schemas/baokuan.toml](../assets/schemas/baokuan.toml)。

### 字段格式

```toml
[[fields]]
name = "标题"        # 飞书列名
type = "text"        # 字段类型：text, number, datetime, attachment
source = "meta.title"  # 数据路径（点号分隔）
```

### 支持的类型

| type | 说明 |
|------|------|
| `text` | 文本（默认） |
| `datetime` | 日期时间 |
| `attachment` | 附件文件（单独上传，不参与 batch_create） |

### source 表达式

- `meta.title` — 直接取值
- `lines | joined` — 数组用 `\n` 连接
- `analyses.summary.tags | tags_hashtag` — 数组用空格连接
- `meta | stats_compact` — 统计数据格式化

## 附件字段

类型为 `attachment` 的字段，source 指向的是本地文件路径（通常是 `meta.video_path`，由 download 命令自动保存）。

- 文件 > 1900MB 自动跳过并告警
- 空文件跳过
- 其它字段正常写入，不受附件上传失败影响

## 常见错误

| 错误码 | 原因 | 解决 |
|--------|------|------|
| `99991672` | 机器人无权限 | 把机器人加为 base 协作者并授予「可编辑」 |
| `1254045` | 字段名不存在 | 跑 `vtf init feishu` 补齐字段 |
| lark-cli 未找到 | 未安装 | `npm i -g @larksuite/lark-cli` |
