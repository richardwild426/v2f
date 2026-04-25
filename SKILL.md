---
name: video-to-feishu
description: >
  通用视频分析流水线 — 支持 B站 + YouTube 视频 → FunASR转录 → 逐行文案提取 → AI分析 → 输出结果。
  自动识别视频平台，统一处理流程。产出结果以「爆款制造机」表格字段为基准（支持自定义映射）。
  如果配置了飞书表格则直接写入，否则输出 markdown 文档返回给使用者。
  支持环境变量配置，便于迁移到其他智能体或服务器。
tags: [video, transcription, funasr, feishu, bitable, content-analysis, bilibili, youtube]
category: media
---

# 通用视频分析流水线 v4.1

完整流程：识别平台 → 下载音频 → FunASR转录 → 逐行处理 → AI分析 → 输出结果（飞书表格 或 markdown）

**支持平台**：B站 (bilibili.com)、YouTube (youtube.com)

## 📚 技能选择指南

| 你的需求 | 使用技能 |
|---------|---------|
| **B站/YouTube 视频 → 转录 → AI分析 → 输出结果** | **本技能** ✅ |
| 批量处理多个视频 | 本技能 + 批量模式 |

---

## 🆕 首次使用：配置飞书表格（可选但推荐）

> 💡 如果不配置飞书表格，结果将以 markdown 格式直接输出到对话中。
> 配置后，每次分析结果自动写入表格，便于长期积累和对比。

### Step 1: 创建或选择一个多维表格

在飞书中新建一个多维表格（或选择一个已有的），记录其 **base token** 和 **table ID**。

- base token：从 URL 中提取，如 `https://my.feishu.cn/base/Lk2Fb3tgoaobGds2b9KcO7sinTd` → token 为 `Lk2Fb3tgoaobGds2b9KcO7sinTd`
- table ID：通过 lark-cli 查询得到

### Step 2: 查询现有表格字段

```bash
# 列出表格
lark-cli base +table-list --base-token "你的base_token"

# 列出字段
lark-cli base +field-list --base-token "你的base_token" --table-id "你的table_id"
```

### Step 3: 创建所需字段（如果表格中没有）

使用 lark-cli 创建以下 19 个字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 对标素材链接 | 文本 | 视频URL |
| 标题 | 文本 | 视频标题 |
| 作者名 | 文本 | UP主/频道名 |
| 文案提取 | 文本 | 逐行文案（换行分隔） |
| 二创改写 | 文本 | 逐行改写（换行分隔，可选） |
| 摘要 | 文本 | 一句话摘要+要点 |
| 视频拆解 | 文本 | Hook/Core/CTA分析 |
| 标签 | 文本 | #Tag1 #Tag2 格式 |
| 数据 | 文本 | 播放/点赞/收藏/分享/评论 |
| 视频时长 | 文本 | 格式: MM:SS |
| 播放数 | 文本 | 数字 |
| 点赞数 | 文本 | 数字 |
| 收藏数 | 文本 | 数字（YouTube为0） |
| 分享数 | 文本 | 数字（YouTube为0） |
| 评论数 | 文本 | 数字 |
| 下载链接 | 文本 | 视频URL（同对标素材链接） |
| 封面链接 | 文本 | 封面图片URL |
| 发布时间 | 日期时间 | 格式: YYYY-MM-DD HH:MM |
| 提取时间 | 日期时间 | 格式: YYYY-MM-DD HH:MM |

```bash
# 创建文本字段示例
lark-cli base +field-create \
  --base-token "你的base_token" \
  --table-id "你的table_id" \
  --json '{"field":{"type":"text","name":"对标素材链接"}}'

# 创建日期时间字段示例
lark-cli base +field-create \
  --base-token "你的base_token" \
  --table-id "你的table_id" \
  --json '{"field":{"type":"datetime","name":"发布时间"}}'
```

### Step 4: 配置环境变量

```bash
# 在 shell profile 中添加（如 ~/.zshrc 或 ~/.bashrc）
export TABLE_TOKEN="你的base_token"
export TABLE_ID="你的table_id"
```

> ✅ 配置完成后，后续使用无需再指定表格参数，结果自动写入。

---

## 🔧 前置条件检查

执行前运行以下命令验证环境：

```bash
# 1. 验证 FunASR 环境
python3 -c "
import shutil, subprocess, sys, os
candidates = [
    os.environ.get('FUNASR_PYTHON'),
    shutil.which('funasr'),
    shutil.which('python3'),
]
for py in candidates:
    if not py: continue
    try:
        r = subprocess.run([py, '-c', 'import funasr; print(funasr.__version__)'],
                          capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            print(f'✅ FunASR OK: {py} (v{r.stdout.strip()})')
            break
    except: pass
else:
    print('❌ FunASR 未找到')
    sys.exit(1)
"

# 2. 验证 lark-cli（可选，仅在需要写入飞书表格时）
lark-cli auth status || echo "⚠️ lark-cli 未登录，将降级为 markdown 输出"

# 3. 验证 yt-dlp
yt-dlp --version || echo "⚠️ 需要安装: pip install yt-dlp"
```

---

## 🚀 Step 0: 平台识别 + 参数配置

### 自动识别平台

```python
import re

def detect_platform(url: str) -> str:
    """自动识别视频平台"""
    if re.search(r'bilibili\.com|b23\.tv', url):
        return 'bilibili'
    elif re.search(r'youtube\.com|youtu\.be', url):
        return 'youtube'
    return 'unknown'
```

### 参数配置

```bash
# === 必填参数 ===
VIDEO_URL=""          # 视频URL（B站或YouTube）

# === 飞书表格配置（可选） ===
# 如果配置了以下两个参数，结果将写入飞书表格
# 如果未配置，结果将以 markdown 格式输出
TABLE_TOKEN="your_table_token"        # 飞书表格token（留空则不写入表格）
TABLE_ID=""           # 飞书表格ID（留空则不写入表格）

# === 可选参数 ===
CORRECTIONS_FILE=""   # ASR纠错字典路径
```

### 输出模式判断

```bash
# 判断是否写入飞书表格
if [ -n "$TABLE_TOKEN" ] && [ -n "$TABLE_ID" ]; then
    OUTPUT_MODE="feishu"
    echo "📊 输出模式: 写入飞书表格"
else
    OUTPUT_MODE="markdown"
    echo "📄 输出模式: markdown 文档"
fi
```

---

## 🔍 Step 0.5: UP主发现（当只有 UP主名称时）

> 💡 如果用户只给了 UP主名称（如"AI红发魔女"），没有给具体视频 URL，按以下步骤找到最新视频。

### 方法1：B站搜索 API 找 UP主 UID

```bash
# URL 编码后的关键词
curl -s \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  "https://api.bilibili.com/x/web-interface/search/type?search_type=bili_user&keyword=$(python3 -c 'import urllib.parse; print(urllib.parse.quote("AI红发魔女"))')" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
if data.get('code') == 0 and data.get('data', {}).get('result'):
    for user in data['data']['result'][:3]:
        print(f\"UID: {user.get('mid')}, 名称: {user.get('uname')}, 粉丝: {user.get('fans')}, 视频数: {user.get('videos')}\")
"
```

### 方法2：yt-dlp 获取 UP主视频列表（推荐，绕过 B站 API 412）

> ⚠️ **B站空间搜索 API 412**：`x/web-interface/search/type` 和 `x/space/wbi/arc/search` 经常返回 412 错误。最可靠的方式是用 `yt-dlp --flat-playlist`。

```bash
# 获取 UP主最新视频列表（按投稿时间排序）
yt-dlp --flat-playlist --dump-json \
  "https://space.bilibili.com/{UID}/video" 2>/dev/null | \
  python3 -c "
import json, sys
for line in sys.stdin:
    data = json.loads(line)
    bvid = data.get('id')
    url = data.get('url')
    print(f'{bvid} → {url}')
    break  # 只取第一个（最新的）
"
```

### 方法3：浏览器搜索（当 API 全部 412 时）

> 💡 当 B站 API 全部返回 412 时，用浏览器直接搜索是最可靠的方式。
> 访问 `https://www.bilibili.com/search?keyword=UP主名称&order=pubdate`，从搜索结果中提取 UP主空间链接和最新视频。

### 方法4：获取视频元数据（当 B站 API 412 时）

> ⚠️ **B站元数据 API 412**：`api.bilibili.com/x/web-interface/view` 也可能返回 412。备用方案：用 `yt-dlp -J --cookies-from-browser chrome`。

```bash
yt-dlp -J --cookies-from-browser chrome \
  "https://www.bilibili.com/video/{BV号}" 2>/dev/null | \
  python3 -c "
import json, sys
raw = sys.stdin.read()
for line in raw.strip().split('\n'):
    line = line.strip()
    if line.startswith('{'):
        data = json.loads(line)
        if data:
            print(f\"标题: {data.get('title')}\")
            print(f\"UP主: {data.get('uploader')}\")
            print(f\"发布日期: {data.get('upload_date')}\")
            print(f\"时长: {data.get('duration')}秒\")
            print(f\"播放: {data.get('view_count')}\")
            print(f\"点赞: {data.get('like_count', 'N/A')}\")
            print(f\"标签: {data.get('tags', [])}\")
            break
"
```

---

## 📋 Step 1: 获取视频元数据

> ⚠️ **⚡ 统一推荐：全部用 yt-dlp -J**
> B站 API（`api.bilibili.com/x/web-interface/view`）几乎总是返回 412。
> **B站和 YouTube 统一用 `yt-dlp -J --cookies-from-browser chrome` 获取元数据，最可靠。**

### 1A: B站视频（⚡ 推荐：yt-dlp）

```bash
yt-dlp -J --cookies-from-browser chrome \
  "https://www.bilibili.com/video/{BV号}" 2>/dev/null | \
  python3 -c "
import json, sys
from datetime import datetime
data = json.loads(sys.stdin.read())
upload_date = data.get('upload_date', '')
if upload_date:
    try: upload_date = datetime.strptime(upload_date, '%Y%m%d').strftime('%Y-%m-%d %H:%M')
    except: pass
dur = data.get('duration', 0)
print(json.dumps({
    'platform': 'bilibili',
    'video_id': data.get('id', ''),
    'url': data.get('webpage_url', ''),
    'title': data.get('title', ''),
    'author': data.get('uploader', ''),
    'upload_date': upload_date,
    'duration': dur,
    'duration_str': f'{dur // 60}:{dur % 60:02d}',
    'thumbnail': data.get('thumbnail', ''),
    'description': (data.get('description', '') or '')[:500],
    'view': data.get('view_count', 0),
    'like': data.get('like_count', 0),
    'favorite': 0,
    'share': 0,
    'reply': 0,
}, ensure_ascii=False, indent=2))
"
```

> 💡 B站 API 已废弃为备用方案（412 率 >95%）。yt-dlp 提供 title、uploader、upload_date、duration、view_count、thumbnail、description 等完整元数据。

### 1B: YouTube 视频

```python
import json, sys, subprocess, re
from datetime import datetime

url = sys.argv[1]  # YouTube URL

result = subprocess.run(
    ["yt-dlp", "-J", url],
    capture_output=True, text=True, timeout=30
)

if result.returncode != 0:
    print(f"❌ yt-dlp 获取元数据失败: {result.stderr[:200]}", file=sys.stderr)
    sys.exit(1)

data = json.loads(result.stdout)

video_id = data.get("id", "")
if not video_id:
    m = re.search(r'v=([a-zA-Z0-9_-]{11})', url)
    video_id = m.group(1) if m else "unknown"

upload_date = data.get("upload_date", "")
if upload_date:
    try:
        upload_date = datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d %H:%M")
    except:
        pass

output = {
    "platform": "youtube",
    "video_id": video_id,
    "url": f"https://www.youtube.com/watch?v={video_id}",
    "title": data.get("title", ""),
    "author": data.get("uploader", ""),
    "upload_date": upload_date,
    "duration": data.get("duration", 0),
    "duration_str": f"{data.get('duration', 0) // 60}:{data.get('duration', 0) % 60:02d}",
    "thumbnail": data.get("thumbnail", ""),
    "description": (data.get("description", "") or "")[:500],
    "view": data.get("view_count", 0),
    "like": data.get("like_count", 0),
    "favorite": 0,
    "share": 0,
    "reply": data.get("comment_count", 0),
}

print(json.dumps(output, ensure_ascii=False, indent=2))
```

---

## 📥 Step 2: 下载音频

### B站视频（⚠️ 重要：需要浏览器 Cookie）

> ⚠️ **B站 412 错误解决方案**：B站 API 需要登录态，直接使用 `yt-dlp` 会返回 `HTTP Error 412: Precondition Failed`。必须通过 `--cookies-from-browser` 参数读取浏览器 Cookie。

```bash
# ✅ 正确方式（读取 Chrome 浏览器 Cookie）
yt-dlp --cookies-from-browser chrome \
  --retries 3 --fragment-retries 3 \
  -f bestaudio -x --audio-format mp3 \
  --audio-quality 0 \
  -o "/tmp/${VIDEO_ID}.mp3" \
  "$VIDEO_URL"

# 如果 Chrome 不可用，尝试 Safari 或 Firefox
yt-dlp --cookies-from-browser safari ...
yt-dlp --cookies-from-browser firefox ...
```

> 💡 **前提条件**：确保 Chrome/Safari/Firefox 已登录 B站（访问过 bilibili.com 并登录）。

### YouTube 视频

```bash
yt-dlp --retries 3 --fragment-retries 3 \
  -f bestaudio -x --audio-format mp3 \
  --audio-quality 0 \
  -o "/tmp/${VIDEO_ID}.mp3" \
  "$VIDEO_URL"
```

> 💡 `--audio-quality 0` 确保最高音质，提升转录准确率。

---

## 🎙️ Step 3: FunASR 转录 + 纠错

**B站和 YouTube 完全相同**：

```python
import json, sys, subprocess, shutil, tempfile, os

audio_file = sys.argv[1]
corrections_file = sys.argv[2] if len(sys.argv) > 2 else ""

# 自动检测 FunASR Python（支持环境变量覆盖）
def find_funasr_python():
    # 1. 环境变量优先
    env_py = os.environ.get("FUNASR_PYTHON")
    if env_py:
        try:
            r = subprocess.run([env_py, "-c", "import funasr"], capture_output=True, timeout=5)
            if r.returncode == 0: return env_py
        except: pass
    # 2. 常见路径
    candidates = [
        shutil.which("funasr"),
        # mise 管理的 Python（macOS 上 FunASR 通常装在这里）
        "/Users/zvector/.local/share/mise/installs/python/3.12.12/bin/python",
        shutil.which("python3"),
        shutil.which("python"),
    ]
    for p in candidates:
        if not p: continue
        try:
            r = subprocess.run([p, "-c", "import funasr"], capture_output=True, timeout=5)
            if r.returncode == 0: return p
        except: pass
    return None

funasr_py = find_funasr_python()
if not funasr_py:
    print("❌ 未找到 FunASR 环境", file=sys.stderr)
    sys.exit(1)

# 加载纠错字典
corrections = {}
if corrections_file:
    try:
        with open(corrections_file) as f:
            corrections = json.load(f)
    except FileNotFoundError:
        pass

# 写入临时文件（避免 f-string 注入）
corr_tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
corr_tmp.write(json.dumps(corrections, ensure_ascii=False))
corr_tmp.close()

# 执行转录（⚠️ 重要：用标记包裹 JSON 输出，避免 FunASR 日志污染 stdout）
transcribe_code = f'''
import json
from funasr import AutoModel

with open("{corr_tmp.name}") as f:
    corrections = json.load(f)

model = AutoModel(model=os.environ.get("ASR_MODEL", "paraformer-zh"), vad_model="fsmn-vad", punc_model="ct-punc", disable_update=True)
result = model.generate(input="{audio_file}", batch_size_s=300, sentence_timestamp=True)

sentences = []
for res in result:
    if "sentence_info" in res:
        for s in res["sentence_info"]:
            text = s["text"].strip()
            if text:
                sentences.append(text)

for i, s in enumerate(sentences):
    for wrong, right in corrections.items():
        sentences[i] = sentences[i].replace(wrong, right)

# 用标记包裹 JSON，避免 FunASR 版本信息等日志污染 stdout
print("TRANSCRIPT_JSON_START")
print(json.dumps(sentences, ensure_ascii=False))
print("TRANSCRIPT_JSON_END")
'''

r = subprocess.run([funasr_py, "-c", transcribe_code], capture_output=True, text=True, timeout=600)
os.unlink(corr_tmp.name)

if r.returncode != 0:
    print(f"❌ FunASR 转录失败: {r.stderr}", file=sys.stderr)
    sys.exit(1)

# 从标记之间提取 JSON（FunASR 会向 stdout 输出版本信息等日志）
stdout = r.stdout
start = stdout.find("TRANSCRIPT_JSON_START")
end = stdout.find("TRANSCRIPT_JSON_END")
if start >= 0 and end >= 0:
    json_str = stdout[start + len("TRANSCRIPT_JSON_START"):end].strip()
    raw_sentences = json.loads(json_str)
else:
    # 降级：尝试直接解析整个 stdout
    raw_sentences = json.loads(stdout.strip())
print(f"✅ 转录完成: {len(raw_sentences)} 句")
print(json.dumps(raw_sentences, ensure_ascii=False))
```

---

## 📝 Step 4: 文案行合并

**与平台无关**：

```python
import json, sys

raw = json.loads(sys.stdin.read())

def merge_into_lines(sentences):
    """将 FunASR 碎片合并为自然字幕行"""
    lines = []
    buffer = ""
    bracket_stack = []

    open_brackets = set('（《【〖「『〔｛')
    close_map = {'（': '）', '《': '》', '【': '】', '〖': '〗', '「': '」', '『': '』', '〔': '〕', '｛': '｝'}
    sentence_enders = '。！？…'
    new_thought_starts = '第首先然后而且所以但是然而不过可是如果虽然'

    for s in sentences:
        s = s.strip()
        if not s: continue
        for ch in s:
            if ch in open_brackets: bracket_stack.append(ch)
            elif ch in close_map.values() and bracket_stack:
                if close_map.get(bracket_stack[-1]) == ch: bracket_stack.pop()
        in_bracket = len(bracket_stack) > 0
        should_split = False
        if buffer:
            if in_bracket: should_split = False
            elif buffer[-1] in sentence_enders: should_split = True
            elif len(buffer) > 15 and s[0] in new_thought_starts: should_split = True
            elif len(buffer) <= 8: should_split = False
            else: should_split = False
        if should_split:
            lines.append(buffer)
            buffer = s
        else:
            buffer += s
    if buffer: lines.append(buffer)
    cleaned = []
    for line in lines:
        line = line.strip()
        if line:
            while line and line[-1] in '，': line = line[:-1].strip()
            if line: cleaned.append(line)
    return cleaned

wenan_lines = merge_into_lines(raw)
print(json.dumps(wenan_lines, ensure_ascii=False))
```

---

## 🤖 Step 5: AI 分析生成

**与平台无关**。使用以下 Prompt 生成结构化分析。

### 5.1 视频摘要 + 核心要点 + 标签

```
你是一个视频内容分析专家。请分析以下视频文案，生成结构化摘要。

视频标题：{title}
作者：{author}
平台：{platform}
文案：
{完整文案}

请生成：
1. 一句话摘要（50字以内）
2. 核心要点（3-5条，每条20字以内）
3. 亮点分析（2-3条）
4. 适用标签（5个，#Tag 格式）
```

### 5.2 视频拆解

```
分析以下视频的结构：

标题：{title}
作者：{author}
文案：
{完整文案}

请按以下格式输出：
- Hook（开头钩子）：如何吸引注意力的
- Core（核心内容）：主要讲了什么
- CTA（行动号召）：如何引导互动的
- 优点：做得好的地方
- 优化建议：可以改进的地方
```

### 5.3 逐行二创改写（可选）

```
# AI 科技自媒体博主 - 文案创造性重构提示词
## Role
你是一位拥有百万粉丝的 AI 科技自媒体博主。你的风格特征是：**睿智、松弛、有见解**。
你像是一位懂技术的朋友在咖啡馆里分享最前沿的干货，既专业体面，又通俗易懂。
---
## Core Task
对原始文案进行【创造性重构】，而非简单删减或同义词替换。
保持核心信息不变，但**表达方式、句式结构、叙述角度**要彻底改造。
---
## Writing Standards
### 【黄金三秒开篇】
- 第一行必须是"钩子"：反直觉结论 / 痛点打击 / 悬念设置
- 禁止平铺直叙
- 前 3 行内必须抛出核心利益点
### 【表达重构策略】
- **视角转换**：把"我做了 X"改成"你也能 X"或"想象一下 X"
- **悬念前置**：把后文的关键信息提前
- **对比强化**：用"以前...现在..."、"别人...我们..."制造张力
- **句式重组**：打散原句结构，重新组织语言
### 【字数与节奏】
- **行数**：必须与原稿一致
- **字数**：每行与原稿±30% 浮动，**禁止过度压缩**
- **口播感**：保持可朗读的流畅感
### 【去口语化规则】
- **删除**：啊、呢、吧、哒、哦、啥的、就是说、其实、那么
- **替换**：太麻烦了→劝退、搞不定→没戏、很简单→零门槛
### 【差异化要求】
- **文字重合度**：每行与原稿的文字重合度不超过 40%
- **句式变化**：不要保持原稿的主谓宾结构
### 【调性约束】
- **高级感**：严禁"震惊、全网最强、炸裂"等低俗营销词
- **专业性**：核心专有名词准确保留
---
## Output Format
- 逐行输出改写结果
- 每行独立成句，富有张力
- 不要任何额外说明，只要改写内容
---

原文：
{逐行文案，每行用换行分隔}
```

---

## 📊 Step 6: 输出结果

### 6.0 自定义输出字段（可选）

> 💡 默认使用 19 个标准字段。如果你的飞书表格字段不同，可通过环境变量自定义映射：
> ```bash
> # 自定义字段映射（JSON 格式，键为标准字段名，值为你的表格字段名）
> export FIELD_MAPPING='{
>   "对标素材链接": "视频链接",
>   "作者名": "UP主",
>   "文案提取": "原始文案",
>   "二创改写": "改写文案"
> }'
> ```
> 未映射的字段将使用默认名称。留空 `FIELD_MAPPING` 则全部使用默认字段。

### 6.1 标准输出字段（以「爆款制造机」表格为基准）

所有产出结果统一使用以下 19 个字段：

| 字段名 | 类型 | 说明 | 数据来源 |
|--------|------|------|----------|
| 对标素材链接 | text | 视频URL | Step 1 元数据 |
| 标题 | text | 视频标题 | Step 1 元数据 |
| 作者名 | text | UP主/频道名 | Step 1 元数据 |
| 文案提取 | text | 逐行文案（换行分隔） | Step 4 合并结果 |
| 二创改写 | text | 逐行改写（换行分隔） | Step 5.3 AI生成（可选） |
| 摘要 | text | 一句话摘要+要点 | Step 5.1 AI生成 |
| 视频拆解 | text | Hook/Core/CTA分析 | Step 5.2 AI生成 |
| 标签 | text | #Tag1 #Tag2 格式 | Step 5.1 AI生成 |
| 数据 | text | 播放/点赞/收藏/分享/评论 | Step 1 元数据拼接 |
| 视频时长 | text | 格式: MM:SS | Step 1 元数据 |
| 播放数 | text | 数字 | Step 1 元数据 |
| 点赞数 | text | 数字 | Step 1 元数据 |
| 收藏数 | text | 数字（YouTube为0） | Step 1 元数据 |
| 分享数 | text | 数字（YouTube为0） | Step 1 元数据 |
| 评论数 | text | 数字 | Step 1 元数据 |
| 下载链接 | text | 视频URL（同对标素材链接） | Step 1 元数据 |
| 封面链接 | text | 封面图片URL | Step 1 元数据 |
| 发布时间 | datetime | 格式: YYYY-MM-DD HH:MM | Step 1 元数据 |
| 提取时间 | datetime | 格式: YYYY-MM-DD HH:MM | 当前时间 |

### 6.2 组装结果数据

```python
from datetime import datetime

now = datetime.now().strftime("%Y-%m-%d %H:%M")

result = {
    "对标素材链接": meta["url"],
    "标题": meta["title"],
    "作者名": meta["author"],
    "文案提取": "\n".join(wenan_lines),
    "二创改写": rewrite_text or "",
    "摘要": summary_text,
    "视频拆解": breakdown_text,
    "标签": " ".join(tags),
    "数据": f"播放{meta['view']} | 点赞{meta['like']} | 收藏{meta['favorite']} | 分享{meta['share']} | 评论{meta['reply']}",
    "视频时长": meta["duration_str"],
    "播放数": str(meta["view"]),
    "点赞数": str(meta["like"]),
    "收藏数": str(meta["favorite"]),
    "分享数": str(meta["share"]),
    "评论数": str(meta["reply"]),
    "下载链接": meta["url"],
    "封面链接": meta["thumbnail"],
    "发布时间": meta["upload_date"],
    "提取时间": now,
}
```

### 6.3 模式A：写入飞书表格（当 TABLE_TOKEN 和 TABLE_ID 已配置）

```bash
lark-cli base +record-batch-create \
  --base-token "$TABLE_TOKEN" \
  --table-id "$TABLE_ID" \
  --json '{"fields":["对标素材链接","标题","作者名","文案提取","二创改写","摘要","视频拆解","标签","数据","视频时长","播放数","点赞数","收藏数","分享数","评论数","下载链接","封面链接","发布时间","提取时间"],"rows":[["值1","值2",...]]}'
```

> ⚠️ 关键要点：
> - 使用 `--json` 参数（不是 `--data`）
> - `rows` 必须是**数组的数组** `[[val1, val2, ...]]`
> - 字段名必须**完全匹配**表格中的字段名
> - 跳过 READONLY 字段（由公式自动生成的）

### 6.4 模式B：输出 Markdown 文档（当 TABLE_TOKEN 或 TABLE_ID 未配置）

直接输出以下格式的 Markdown 文档：

```markdown
# 🎬 视频分析报告

## 基本信息

| 字段 | 内容 |
|------|------|
| **标题** | {标题} |
| **作者** | {作者名} |
| **平台** | {platform} |
| **时长** | {视频时长} |
| **发布时间** | {发布时间} |
| **链接** | {对标素材链接} |

## 数据

- 播放数：{播放数}
- 点赞数：{点赞数}
- 收藏数：{收藏数}
- 分享数：{分享数}
- 评论数：{评论数}

---

## 📝 文案提取（{行数}行）

{逐行文案，每行用换行分隔}

---

## ✍️ 二创改写（可选）

{逐行改写，每行用换行分隔}

---

## 📊 摘要

{摘要内容}

---

## 🔍 视频拆解

{视频拆解内容}

---

## 🏷️ 标签

{标签}
```

---

## 📦 批量处理模式

### 输入格式

支持混合平台：

```
# B站
https://www.bilibili.com/video/BV1xx4y1Q7Ef
BV1EfXfBaEz5

# YouTube
https://www.youtube.com/watch?v=xPiOChWNnDw
https://youtu.be/VIDEO_ID
```

### 批量执行

```bash
# 1. 准备视频列表
cat > /tmp/batch_videos.txt << 'EOF'
https://www.bilibili.com/video/BV1xx4y1Q7Ef
https://www.youtube.com/watch?v=xPiOChWNnDw
EOF

# 2. 设置环境变量
export TABLE_TOKEN="your_table_token"       # 留空则全部输出 markdown
export TABLE_ID=""
export BATCH_FILE="/tmp/batch_videos.txt"
export BATCH_DELAY=5

# 3. 执行批量处理
# 逐个处理，每个视频输出独立 markdown 或写入表格
```

---

## 🛠️ 关键经验总结

### 平台差异处理
- **B站**：元数据统一用 `yt-dlp -J --cookies-from-browser chrome`（B站 API 412 率 >95%，不推荐）
- **YouTube**：元数据用 yt-dlp，无收藏/分享数（设为 0）
- **转录**：完全相同，都是 FunASR 处理音频文件
- **分析**：完全相同，AI Prompt 不区分平台
- **下载**：yt-dlp 统一支持，`--audio-quality 0` 确保最高音质
- **B站 Cookie（⚠️ 关键！）**：B站下载必须加 `--cookies-from-browser chrome`，否则返回 412 错误。前提：Chrome 已登录 B站。
- **B站 API 412 问题**：几乎所有 B站 API（`x/web-interface/view`、`x/web-interface/search/type`、`x/space/wbi/arc/search`）都频繁返回 412。
  - 找 UP主 UID：用浏览器搜索 `https://www.bilibili.com/search?keyword=UP主名称`（最可靠）
  - 获取视频列表：用 `yt-dlp --flat-playlist --dump-json "https://space.bilibili.com/{UID}/video"`（最可靠）
  - 获取视频元数据：用 `yt-dlp -J --cookies-from-browser chrome URL`（统一方法，B站和 YouTube 通用）

### FunASR 转录要点
- 使用 `sentence_timestamp=True` 获取逐句输出
- Python 路径自动检测（支持 `FUNASR_PYTHON` 环境变量覆盖）
- **⚠️ stdout 日志污染**：FunASR 会向 stdout 输出版本信息等。必须用 `TRANSCRIPT_JSON_START`/`TRANSCRIPT_JSON_END` 标记包裹 JSON 输出，然后从标记之间提取。
- **macOS FunASR Python 路径**：通常安装在 mise 管理的 Python 3.12 中（`/Users/zvector/.local/share/mise/installs/python/3.12.12/bin/python`），而非默认 uv venv。
- **⚠️ FunASR 必须在 terminal 中运行**：Python sandbox（execute_code）使用独立的 uv venv 环境，无法检测到 FunASR。FunASR 转录命令必须通过 `terminal` 工具执行，不能通过 `execute_code` 执行。
- 纠错字典通过临时文件传递，避免 f-string 注入
- 碎片合并需跟踪括号配对（`（《【` 等）
- ASR 模型可通过 `ASR_MODEL` 环境变量切换（默认 `paraformer-zh`）
- 使用 `disable_update=True` 避免每次启动检查更新

### 输出模式
- **已配置表格**（TABLE_TOKEN + TABLE_ID 非空）→ 写入飞书多维表格
- **未配置表格**（任一为空）→ 输出 markdown 文档到对话中
- 两种模式共用同一套 19 字段标准结构
- Markdown 输出时，完整展示所有字段内容

### 飞书表格操作（仅模式A）
- 命令用 `+` 号分隔（`base +record-batch-create`）
- 使用 `--json` 参数，`rows` 是数组的数组
- 字段名完全匹配，跳过 READONLY 字段
- **写入新记录**：
  ```bash
  lark-cli base +record-batch-create \
    --base-token "$TABLE_TOKEN" \
    --table-id "$TABLE_ID" \
    --json '{"fields":["字段1","字段2",...],"rows":[[值1,值2,...]]}'
  ```
- **更新已有记录**（⚠️ 格式与 create 不同）：
  ```bash
  lark-cli base +record-batch-update \
    --base-token "$TABLE_TOKEN" \
    --table-id "$TABLE_ID" \
    --json '{"record_id_list":["recXXX"],"patch":{"字段名":"新值"}}'
  ```
  > ⚠️ 关键区别：update 用 `record_id_list` + `patch`，不是 `fields` + `rows`。`patch` 是对象，只传需要更新的字段。
- **Python subprocess 传参**：用 `json.dumps()` 生成 JSON 字符串传入 `--json`，不要用 `--json ./file.json`（会报错）。

---

## 🔗 相关技能

| 技能 | 与本技能的关系 |
|------|--------------|
| `feishu-bitable-query` | 飞书表格基础操作（写入表格时依赖） |

---

## ⚙️ 环境变量（可选）

```bash
# 可在 shell profile 中设置
export TABLE_TOKEN="your_table_token"               # 默认表格token（留空则输出 markdown）
export TABLE_ID=""                  # 默认表格ID（留空则输出 markdown）
export CORRECTIONS_FILE=""          # 默认纠错字典路径
export FUNASR_PYTHON=""             # FunASR Python 路径（留空则自动检测）
export ASR_MODEL="paraformer-zh"    # ASR 模型（默认 paraformer-zh）
export FIELD_MAPPING=""             # 自定义字段映射 JSON（可选）
```

> 💡 设置 TABLE_TOKEN 和 TABLE_ID 后，结果自动写入飞书表格。
> 不设置则结果以 markdown 格式直接输出到对话中。
