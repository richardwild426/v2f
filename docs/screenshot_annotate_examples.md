# 截图标注功能使用示例

## 基本用法

### 1. 生成截图

首先使用 `vtf screenshot` 命令生成截图：

```bash
vtf screenshot --video video.mp4 --subtitles lines.json --output screenshots.json
```

### 2. 创建标注配置

创建 `annotations.json` 文件，定义标注内容：

```json
{
  "0": [
    {
      "type": "text",
      "position": [10, 10],
      "content": "重要信息",
      "color": "#FF0000",
      "size": 24
    },
    {
      "type": "arrow",
      "position": [50, 50],
      "end_position": [200, 200],
      "color": "#00FF00"
    }
  ],
  "1": [
    {
      "type": "rectangle",
      "position": [100, 100],
      "end_position": [300, 250],
      "color": "#0000FF",
      "size": 3
    },
    {
      "type": "highlight",
      "position": [50, 50],
      "end_position": [200, 150],
      "color": "#FFFF00"
    }
  ]
}
```

### 3. 添加标注

运行标注命令：

```bash
vtf screenshot-annotate --input screenshots.json --annotations annotations.json
```

## 高级用法

### 自定义字体

```bash
vtf screenshot-annotate \
  --input screenshots.json \
  --annotations annotations.json \
  --font /path/to/font.ttf \
  --font-size 24
```

### 调整透明度

```bash
vtf screenshot-annotate \
  --input screenshots.json \
  --annotations annotations.json \
  --opacity 0.7
```

### 无背景文字

```bash
vtf screenshot-annotate \
  --input screenshots.json \
  --annotations annotations.json \
  --no-background
```

### 自定义背景颜色

```bash
vtf screenshot-annotate \
  --input screenshots.json \
  --annotations annotations.json \
  --background-color "#FFFFFF80"
```

## 标注类型详解

### 文字标注 (text)

```json
{
  "type": "text",
  "position": [10, 10],
  "content": "这是文字标注",
  "color": "#FF0000",
  "size": 20
}
```

- `position`: 文字左上角坐标 [x, y]
- `content`: 文字内容
- `color`: 颜色（十六进制）
- `size`: 字体大小

### 箭头标注 (arrow)

```json
{
  "type": "arrow",
  "position": [50, 50],
  "end_position": [200, 200],
  "color": "#00FF00"
}
```

- `position`: 箭头起点坐标
- `end_position`: 箭头终点坐标
- `color`: 颜色

### 矩形标注 (rectangle)

```json
{
  "type": "rectangle",
  "position": [100, 100],
  "end_position": [300, 250],
  "color": "#0000FF",
  "size": 3
}
```

- `position`: 左上角坐标
- `end_position`: 右下角坐标
- `color`: 颜色
- `size`: 线宽

### 高亮标注 (highlight)

```json
{
  "type": "highlight",
  "position": [50, 50],
  "end_position": [200, 150],
  "color": "#FFFF00"
}
```

- `position`: 左上角坐标
- `end_position`: 右下角坐标
- `color`: 高亮颜色（自动添加透明度）

### 时间戳标注 (timestamp)

```json
{
  "type": "timestamp",
  "position": [10, 10],
  "content": "00:01:30",
  "color": "#FFFFFF"
}
```

- `position`: 时间戳位置
- `content`: 时间戳文字（空则使用当前时间）
- `color`: 颜色

## 批量处理示例

### 多截图批量标注

```json
{
  "0": [
    {"type": "text", "position": [10, 10], "content": "截图1", "color": "#FF0000"},
    {"type": "arrow", "position": [50, 50], "end_position": [200, 200], "color": "#00FF00"}
  ],
  "1": [
    {"type": "text", "position": [10, 10], "content": "截图2", "color": "#0000FF"},
    {"type": "highlight", "position": [100, 100], "end_position": [300, 250], "color": "#FFFF00"}
  ],
  "2": [
    {"type": "rectangle", "position": [50, 50], "end_position": [350, 250], "color": "#FF00FF", "size": 5}
  ]
}
```

### 保存到新文件

```bash
vtf screenshot-annotate \
  --input screenshots.json \
  --annotations annotations.json \
  --output annotated_screenshots.json
```

## 配置选项参考

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--font` | 系统字体 | 自定义字体文件路径 |
| `--font-size` | 20 | 默认字体大小 |
| `--color` | #FF0000 | 默认标注颜色 |
| `--opacity` | 1.0 | 默认透明度 (0-1) |
| `--padding` | 10 | 文字内边距 |
| `--no-background` | false | 不显示文字背景 |
| `--background-color` | #00000080 | 文字背景颜色 |

## 最佳实践

1. **标注位置**: 使用相对坐标，避免在不同分辨率下错位
2. **颜色选择**: 使用高对比度颜色，确保在各种背景下可见
3. **字体大小**: 根据截图尺寸调整，确保文字清晰可读
4. **透明度**: 对于高亮标注，使用较低透明度避免遮挡内容
5. **批量处理**: 对于多张截图，使用统一的标注风格保持一致性
