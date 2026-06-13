# vtf 截图功能开发状态

## 当前状态

**Phase 8 已完成** - 截图功能增强与用户体验优化

### 完成的功能

1. **核心截图引擎** ✅
   - 字幕模式截图
   - 场景模式截图
   - 自动模式截图（优先字幕，失败回退场景检测）
   - 智能去重（pHash 感知哈希）
   - 并行处理（ThreadPoolExecutor）

2. **AI 描述生成** ✅
   - prompt 模式（生成 LLM prompt 供外部工具填充）
   - 直接 LLM 调用模式（支持 OpenAI/Anthropic provider）
   - 场景标签生成

3. **报告生成** ✅
   - HTML 报告（响应式画廊布局，支持图片嵌入）
   - JSON 报告（结构化输出）
   - 自定义标题和格式

4. **飞书集成** ✅
   - 批量写入飞书截图表
   - 支持附件上传
   - 配置化集成

5. **性能优化** ✅
   - 批量 ffmpeg 处理
   - 缓存机制（HashCache）
   - 并行处理

6. **Phase 8 新增功能** ✅
   - **进度条显示** - 实时显示截图进度（`--progress/--no-progress`）
   - **批量视频处理** - `vtf screenshot-batch` 命令处理多个视频
   - **截图质量配置** - `--quality` 参数控制 JPEG 质量（1-31）
   - **截图尺寸配置** - `--width`、`--height`、`--scale` 参数控制输出尺寸

### 测试状态

- **总测试数**: 168
- **通过**: 168 ✅
- **失败**: 0

### 代码质量

- ✅ 所有测试通过
- ✅ 代码符合项目规范
- ✅ 文档完整
- ✅ 配置示例完整

### 使用示例

```bash
# 基本截图
vtf screenshot --video video.mp4 --subtitles lines.json --mode subtitle

# 高质量截图（quality=1 最高质量）
vtf screenshot --video video.mp4 --subtitles lines.json --quality 1

# 缩小一半尺寸
vtf screenshot --video video.mp4 --subtitles lines.json --scale 0.5

# 指定输出尺寸
vtf screenshot --video video.mp4 --subtitles lines.json --width 1280 --height 720

# 禁用进度条
vtf screenshot --video video.mp4 --subtitles lines.json --no-progress

# 启用 AI 描述
vtf screenshot --video video.mp4 --subtitles lines.json --ai-describe

# 批量处理多个视频
vtf screenshot-batch -v video1.mp4 -v video2.mp4 --subtitles-dir ./subs

# 批量处理目录下所有视频
vtf screenshot-batch --videos-dir ./videos --subtitles-dir ./subs --output ./screenshots

# 生成报告
vtf screenshot-report --input screenshots.json --output report.html

# 飞书集成
vtf screenshot-emit --input screenshots.json --report report.html
```

### 配置示例

```toml
[screenshot]
enabled = true
ffmpeg_path = "ffmpeg"
scene_threshold = 0.3
min_interval_seconds = 2
similarity_threshold = 0.95
output_dir = "screenshots"
# 截图质量配置
quality = 2  # 1-31，越小质量越高
width = 0    # 输出宽度（0 表示保持原始比例）
height = 0   # 输出高度（0 表示保持原始比例）
scale = 1.0  # 缩放比例（0.5 表示缩小一半）
# AI 描述生成配置
ai_describe = false
llm_provider = ""
llm_model = ""
llm_api_key = ""
llm_base_url = ""
llm_max_tokens = 300
# 性能优化配置
max_workers = 4
cache_dir = ".cache/vtf"
use_cache = true
# 报告生成配置
report_title = "视频截图报告"
report_embed_images = false
report_format = "html"
```

### Phase 8 新增功能详情

#### 1. 进度条显示

实时显示截图处理进度，支持 TTY 终端自动检测：

```bash
# 启用进度条（默认）
vtf screenshot --video video.mp4 --subtitles lines.json --progress

# 禁用进度条（非 TTY 环境自动禁用）
vtf screenshot --video video.mp4 --subtitles lines.json --no-progress
```

#### 2. 批量视频处理

`vtf screenshot-batch` 命令支持：

- **多视频指定**：`-v video1.mp4 -v video2.mp4`
- **目录扫描**：`--videos-dir ./videos`
- **字幕目录**：`--subtitles-dir ./subs`（自动匹配同名 .json 文件）
- **输出结构**：每个视频创建独立子目录

```bash
# 处理指定视频
vtf screenshot-batch -v video1.mp4 -v video2.mp4 --subtitles-dir ./subs

# 处理目录下所有视频
vtf screenshot-batch --videos-dir ./videos --subtitles-dir ./subs --output ./screenshots

# 指定视频扩展名
vtf screenshot-batch --videos-dir ./videos --video-extensions mp4,mkv,avi
```

#### 3. 截图质量配置

通过 `--quality` 参数控制 JPEG 压缩质量：

```bash
# 最高质量（文件较大）
vtf screenshot --video video.mp4 --subtitles lines.json --quality 1

# 默认质量
vtf screenshot --video video.mp4 --subtitles lines.json --quality 2

# 较低质量（文件较小）
vtf screenshot --video video.mp4 --subtitles lines.json --quality 10
```

#### 4. 截图尺寸配置

支持三种尺寸调整方式：

```bash
# 指定宽度（高度自动按比例）
vtf screenshot --video video.mp4 --subtitles lines.json --width 1280

# 指定高度（宽度自动按比例）
vtf screenshot --video video.mp4 --subtitles lines.json --height 720

# 指定宽高
vtf screenshot --video video.mp4 --subtitles lines.json --width 1280 --height 720

# 缩放比例
vtf screenshot --video video.mp4 --subtitles lines.json --scale 0.5  # 缩小一半
vtf screenshot --video video.mp4 --subtitles lines.json --scale 2.0  # 放大一倍
```

### 文档

- [README.md](README.md) - 项目主文档
- [SKILL.md](vtf/SKILL.md) - 智能体指令
- [PHASE7_SUMMARY.md](PHASE7_SUMMARY.md) - Phase 7 完成总结
- [references/](vtf/references/) - 参考文档

### 最近提交

- Phase 8 功能开发中...
- `f3715d1` - feat: 截图功能优化与集成
- `bfd938b` - Improve Bilibili yt-dlp error guidance
- `b7770f2` - chore: 提交 trellis 工作流配置
- `39fcafd` - fix: 防止飞书写入遗漏分析字段
- `138aaa3` - update: skill.md
