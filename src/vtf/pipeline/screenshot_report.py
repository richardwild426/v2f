"""HTML 报告生成模块 - 为截图生成可浏览的 HTML 报告。"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

# 基础 HTML 模板
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            color: #666;
            font-size: 14px;
        }}
        .stat {{
            background: #f8f9fa;
            padding: 5px 10px;
            border-radius: 4px;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: #fff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        .card img {{
            width: 100%;
            height: 200px;
            object-fit: cover;
            cursor: pointer;
        }}
        .card-content {{
            padding: 15px;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .timestamp {{
            background: #3498db;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        .type {{
            background: #95a5a6;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
        }}
        .type.subtitle {{
            background: #27ae60;
        }}
        .type.scene {{
            background: #e67e22;
        }}
        .subtitle-text {{
            font-size: 14px;
            color: #555;
            margin-bottom: 10px;
            font-style: italic;
        }}
        .description {{
            font-size: 14px;
            color: #333;
            margin-bottom: 10px;
        }}
        .tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }}
        .tag {{
            background: #ecf0f1;
            color: #7f8c8d;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
        }}
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }}
        .modal.active {{
            display: flex;
        }}
        .modal img {{
            max-width: 90%;
            max-height: 90%;
            object-fit: contain;
        }}
        .modal-close {{
            position: absolute;
            top: 20px;
            right: 20px;
            color: white;
            font-size: 30px;
            cursor: pointer;
        }}
        footer {{
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{title}</h1>
            <div class="stats">
                <span class="stat">总截图数: {total_count}</span>
                <span class="stat">字幕截图: {subtitle_count}</span>
                <span class="stat">场景截图: {scene_count}</span>
                <span class="stat">生成时间: {generated_at}</span>
            </div>
        </header>
        
        <div class="gallery">
            {cards}
        </div>
        
        <footer>
            <p>由 vtf 截图功能生成</p>
        </footer>
    </div>
    
    <div class="modal" id="imageModal">
        <span class="modal-close" onclick="closeModal()">&times;</span>
        <img id="modalImage" src="" alt="放大查看">
    </div>
    
    <script>
        function openModal(src) {{
            document.getElementById('modalImage').src = src;
            document.getElementById('imageModal').classList.add('active');
        }}
        
        function closeModal() {{
            document.getElementById('imageModal').classList.remove('active');
        }}
        
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') closeModal();
        }});
    </script>
</body>
</html>
"""

CARD_TEMPLATE = """\
<div class="card">
    <img src="{image_src}" alt="截图 {index}" onclick="openModal('{image_src}')">
    <div class="card-content">
        <div class="card-header">
            <span class="timestamp">{timestamp_str}</span>
            <span class="type {type_class}">{type_label}</span>
        </div>
        {subtitle_html}
        {description_html}
        {tags_html}
    </div>
</div>
"""


def generate_html_report(
    *,
    screenshots: list[dict[str, Any]],
    title: str = "视频截图报告",
    embed_images: bool = False,
    output_path: Path | None = None,
) -> str:
    """生成 HTML 报告。

    Args:
        screenshots: 截图信息列表
        title: 报告标题
        embed_images: 是否将图片嵌入 HTML（base64）
        output_path: 输出文件路径（如果提供，自动保存）

    Returns:
        HTML 字符串
    """
    # 统计信息
    total_count = len(screenshots)
    subtitle_count = sum(1 for s in screenshots if s.get("type", "subtitle") == "subtitle")
    scene_count = total_count - subtitle_count
    
    from datetime import datetime
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 生成卡片 HTML
    cards_html = []
    for screenshot in screenshots:
        # 获取图片源
        image_path = screenshot.get("image_path", "")
        if embed_images and image_path and Path(image_path).exists():
            image_src = _image_to_base64(Path(image_path))
        else:
            # 使用相对路径或绝对路径
            if image_path:
                image_src = Path(image_path).name
            else:
                image_src = ""
        
        # 类型样式
        screenshot_type = screenshot.get("type", "subtitle")
        type_class = screenshot_type
        type_label = "字幕" if screenshot_type == "subtitle" else "场景"
        
        # 字幕文本
        subtitle_text = screenshot.get("subtitle_text", "")
        subtitle_html = f'<div class="subtitle-text">"{subtitle_text}"</div>' if subtitle_text else ""
        
        # 描述
        description = screenshot.get("description", "")
        description_html = f'<div class="description">{description}</div>' if description else ""
        
        # 标签
        scene_tags = screenshot.get("scene_tags", "")
        tags_html = ""
        if scene_tags:
            tags = [tag.strip() for tag in scene_tags.split(",") if tag.strip()]
            if tags:
                tags_items = "".join(f'<span class="tag">{tag}</span>' for tag in tags)
                tags_html = f'<div class="tags">{tags_items}</div>'
        
        card_html = CARD_TEMPLATE.format(
            image_src=image_src,
            index=screenshot.get("index", 0),
            timestamp_str=screenshot.get("timestamp_str", "00:00"),
            type_class=type_class,
            type_label=type_label,
            subtitle_html=subtitle_html,
            description_html=description_html,
            tags_html=tags_html,
        )
        cards_html.append(card_html)
    
    # 生成完整 HTML
    html = HTML_TEMPLATE.format(
        title=title,
        total_count=total_count,
        subtitle_count=subtitle_count,
        scene_count=scene_count,
        generated_at=generated_at,
        cards="\n".join(cards_html),
    )
    
    # 保存到文件
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
    
    return html


def _image_to_base64(image_path: Path) -> str:
    """将图片转换为 base64 数据 URI。"""
    import mimetypes
    
    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    with open(image_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def generate_json_report(
    *,
    screenshots: list[dict[str, Any]],
    output_path: Path | None = None,
) -> dict[str, Any]:
    """生成 JSON 报告。

    Args:
        screenshots: 截图信息列表
        output_path: 输出文件路径（如果提供，自动保存）

    Returns:
        报告数据字典
    """
    from datetime import datetime
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_count": len(screenshots),
        "screenshots": screenshots,
    }
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report


__all__ = ["generate_html_report", "generate_json_report"]