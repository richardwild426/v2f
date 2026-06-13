"""AI 描述生成模块 - 为截图生成描述和场景标签。

支持三种模式：
1. 独立运行：生成 LLM prompt 供外部工具填充
2. 集成模式：通过 llm_caller 回调自动生成描述
3. 直接LLM调用：使用配置的LLM provider自动生成描述
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Protocol

# Type alias for the LLM caller callback
# Signature: (image_path: Path, prompt: str) -> str | dict
LlmCaller = Callable[[Path, str], str | dict[str, Any]]

DESCRIPTION_PROMPT_TEMPLATE = """\
你是一个图像分析专家。请分析这张视频截图，并生成简洁的描述和场景标签。

## 截图信息
- 时间点: {timestamp_str}
- 字幕文本: {subtitle_text}
- 截图类型: {screenshot_type}

## 要求
1. **描述** (description): 用一句简洁的中文描述截图内容，不超过 50 字
2. **场景标签** (scene_tags): 用逗号分隔的标签列表，描述场景的关键元素

## 输出格式
```json
{{
  "description": "截图描述",
  "scene_tags": "标签1,标签2,标签3"
}}
```"""


def generate_description_prompt(screenshot: dict[str, Any]) -> str:
    """为单张截图生成 LLM prompt。

    Args:
        screenshot: 截图信息字典

    Returns:
        格式化后的 prompt 字符串
    """
    return DESCRIPTION_PROMPT_TEMPLATE.format(
        timestamp_str=screenshot.get("timestamp_str", "00:00"),
        subtitle_text=screenshot.get("subtitle_text", "") or "（无字幕）",
        screenshot_type=screenshot.get("type", "subtitle"),
    )


def generate_descriptions(
    *,
    screenshots: list[dict[str, Any]],
    cfg: Any,
    llm_caller: LlmCaller | None = None,
) -> list[dict[str, Any]]:
    """为截图列表生成 AI 描述和场景标签。

    支持三种模式：
    1. llm_caller 回调模式
    2. 直接 LLM 调用模式（从 cfg.screenshot 读取 LLM 配置）
    3. 仅生成 prompt 模式

    Args:
        screenshots: 截图信息列表
        cfg: 配置对象
        llm_caller: 可选的 LLM 调用回调

    Returns:
        增强后的截图列表（添加了 prompt/description/scene_tags 字段）
    """
    # 尝试创建 LLM provider（如果配置了）
    llm_provider = None
    if llm_caller is None and hasattr(cfg, "screenshot"):
        screenshot_cfg = cfg.screenshot
        if hasattr(screenshot_cfg, "llm_provider") and screenshot_cfg.llm_provider:
            try:
                from vtf.llm import create_llm_provider
                llm_provider = create_llm_provider(
                    provider=screenshot_cfg.llm_provider,
                    api_key=screenshot_cfg.llm_api_key,
                    model=screenshot_cfg.llm_model,
                    base_url=screenshot_cfg.llm_base_url,
                    max_tokens=screenshot_cfg.llm_max_tokens,
                )
            except Exception:
                pass  # Fall back to prompt-only mode

    enhanced_screenshots: list[dict[str, Any]] = []

    for screenshot in screenshots:
        enhanced = dict(screenshot)
        prompt = generate_description_prompt(screenshot)
        enhanced["prompt"] = prompt

        # 确定是否使用 LLM
        use_llm = llm_caller is not None or llm_provider is not None

        # 如果没有 LLM，只保留 prompt
        if not use_llm:
            enhanced.setdefault("description", "")
            enhanced.setdefault("scene_tags", "")
            enhanced_screenshots.append(enhanced)
            continue

        # 尝试调用 LLM 生成描述
        image_path_str = screenshot.get("image_path", "")
        image_path = Path(image_path_str) if image_path_str else None

        if not image_path or not image_path.exists():
            enhanced["description"] = ""
            enhanced["scene_tags"] = ""
            enhanced_screenshots.append(enhanced)
            continue

        try:
            if llm_caller is not None:
                result = llm_caller(image_path, prompt)
            elif llm_provider is not None:
                result = llm_provider.generate(image_path, prompt)
            else:
                result = ""
            
            parsed = _parse_llm_result(result)
            enhanced["description"] = parsed.get("description", "")
            enhanced["scene_tags"] = parsed.get("scene_tags", "")
        except Exception:
            enhanced["description"] = ""
            enhanced["scene_tags"] = ""

        enhanced_screenshots.append(enhanced)

    return enhanced_screenshots


def _parse_llm_result(result: str | dict[str, Any]) -> dict[str, Any]:
    """解析 LLM 返回结果为 dict。

    支持直接返回 dict 或返回 JSON 字符串（含 markdown code block）。
    """
    if isinstance(result, dict):
        return result

    if not isinstance(result, str):
        return {}

    # 尝试直接解析
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        pass

    # 尝试从 ```json ... ``` 中提取
    if "```json" in result:
        start = result.index("```json") + 7
        end = result.index("```", start)
        json_str = result[start:end].strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # 尝试提取第一个 JSON 对象
    start = result.find("{")
    end = result.rfind("}")
    if start != -1 and end != -1 and end > start:
        json_str = result[start : end + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    return {}


__all__ = [
    "generate_description_prompt",
    "generate_descriptions",
    "LlmCaller",
]
