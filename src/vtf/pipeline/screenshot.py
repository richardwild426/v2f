from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Protocol


class ProgressCallback(Protocol):
    """进度回调协议。"""
    def __call__(self, current: int, total: int, message: str = "") -> None: ...


def _noop_progress(current: int, total: int, message: str = "") -> None:
    """空进度回调（默认）。"""
    pass

try:
    import imagehash
    from PIL import Image
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False

from vtf.pipeline.screenshot_describe import LlmCaller, generate_descriptions


def take_screenshots(
    *,
    video_path: Path,
    lines: list[dict[str, Any]],
    cfg: Any,
    progress_callback: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """
    根据字幕时间戳截取视频帧。

    Args:
        video_path: 视频文件路径
        lines: 字幕行列表，每行包含 text, start_ms, end_ms
        cfg: 配置对象
        progress_callback: 进度回调函数 (current, total, message)

    Returns:
        截图信息列表，每项包含：
        - index: 序号
        - timestamp_ms: 时间戳（毫秒）
        - timestamp_str: 可读时间戳
        - subtitle_text: 字幕文本
        - image_path: 截图文件路径
        - phash: 感知哈希
    """
    on_progress = progress_callback or _noop_progress

    output_dir = Path(cfg.screenshot.output_dir) if hasattr(cfg, "screenshot") else Path("screenshots")
    output_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = cfg.screenshot.ffmpeg_path if hasattr(cfg, "screenshot") else "ffmpeg"
    similarity_threshold = cfg.screenshot.similarity_threshold if hasattr(cfg, "screenshot") else 0.95
    quality = getattr(cfg.screenshot, "quality", 2) if hasattr(cfg, "screenshot") else 2
    width = getattr(cfg.screenshot, "width", 0) if hasattr(cfg, "screenshot") else 0
    height = getattr(cfg.screenshot, "height", 0) if hasattr(cfg, "screenshot") else 0
    scale = getattr(cfg.screenshot, "scale", 1.0) if hasattr(cfg, "screenshot") else 1.0

    # 构建视频滤镜
    vf_filters = []

    # 批量处理：使用单个 ffmpeg 命令截取所有帧
    screenshots: list[dict[str, Any]] = []
    seen_hashes: list[str] = []  # 存储哈希值用于相似度比较

    total_lines = len(lines)

    # 准备批量截图命令
    if lines:
        on_progress(0, total_lines, "准备批量截图...")

        # 使用 ffmpeg 的 select 滤镜批量截取
        timestamps = [line.get("start_ms", 0) / 1000.0 for line in lines]
        select_filter = "+".join([f"eq(t,{ts:.3f})" for ts in timestamps])
        vf_filters.append(f"select='{select_filter}'")

        # 添加缩放滤镜
        if scale != 1.0:
            vf_filters.append(f"scale=iw*{scale}:ih*{scale}")
        elif width > 0 or height > 0:
            w = width if width > 0 else -1
            h = height if height > 0 else -1
            vf_filters.append(f"scale={w}:{h}")

        vf_string = ",".join(vf_filters) if vf_filters else None

        cmd = [ffmpeg_path, "-i", str(video_path)]
        if vf_string:
            cmd.extend(["-vf", vf_string])
        cmd.extend([
            "-vsync", "vfr",
            "-q:v", str(quality),
            str(output_dir / "subtitle_%04d.jpg"),
        ])
        
        try:
            on_progress(0, total_lines, "执行 ffmpeg 批量截图...")
            subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            # 批量处理失败，回退到单帧处理
            on_progress(0, total_lines, "批量截图失败，回退到单帧处理...")
            return _take_screenshots_single(video_path, lines, cfg, output_dir, ffmpeg_path, similarity_threshold, progress_callback)
        
        # 处理生成的截图
        for i, line in enumerate(lines):
            on_progress(i + 1, total_lines, f"处理截图 {i + 1}/{total_lines}")
            start_ms = line.get("start_ms", 0)
            text = line.get("text", "")
            
            # 查找对应的截图文件
            image_path = output_dir / f"subtitle_{i+1:04d}.jpg"
            if not image_path.exists():
                continue
            
            # 计算感知哈希
            phash = _calculate_phash(image_path)
            
            # 检查相似度
            is_duplicate = False
            for existing_hash in seen_hashes:
                similarity = _calculate_similarity(phash, existing_hash)
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                # 删除重复截图
                image_path.unlink(missing_ok=True)
                continue
            
            seen_hashes.append(phash)
            
            # 格式化时间戳
            start_seconds = start_ms / 1000.0
            minutes = int(start_seconds // 60)
            seconds = int(start_seconds % 60)
            timestamp_str = f"{minutes:02d}:{seconds:02d}"
            
            screenshots.append({
                "index": i,
                "timestamp_ms": start_ms,
                "timestamp_str": timestamp_str,
                "subtitle_text": text,
                "image_path": str(image_path),
                "phash": phash,
            })
    
    on_progress(total_lines, total_lines, f"截图完成，共 {len(screenshots)} 张")
    return screenshots


def _take_screenshots_single(
    video_path: Path,
    lines: list[dict[str, Any]],
    cfg: Any,
    output_dir: Path,
    ffmpeg_path: str,
    similarity_threshold: float,
    progress_callback: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """单帧处理回退方案，支持并行处理。"""
    on_progress = progress_callback or _noop_progress

    # 检查是否启用并行处理
    max_workers = getattr(cfg.screenshot, "max_workers", 4) if hasattr(cfg, "screenshot") else 4
    quality = getattr(cfg.screenshot, "quality", 2) if hasattr(cfg, "screenshot") else 2
    width = getattr(cfg.screenshot, "width", 0) if hasattr(cfg, "screenshot") else 0
    height = getattr(cfg.screenshot, "height", 0) if hasattr(cfg, "screenshot") else 0
    scale = getattr(cfg.screenshot, "scale", 1.0) if hasattr(cfg, "screenshot") else 1.0

    # 准备截图任务
    tasks = []
    for i, line in enumerate(lines):
        start_ms = line.get("start_ms", 0)
        text = line.get("text", "")
        filename = f"subtitle_{i:04d}_{start_ms}.jpg"
        image_path = output_dir / filename
        tasks.append((i, start_ms, text, image_path))
    
    # 并行执行截图
    screenshot_results = {}
    total_tasks = len(tasks)
    completed_count = 0
    
    def take_single_screenshot(task):
        nonlocal completed_count
        i, start_ms, text, image_path = task
        start_seconds = start_ms / 1000.0

        # 构建视频滤镜
        vf_filters = []
        if scale != 1.0:
            vf_filters.append(f"scale=iw*{scale}:ih*{scale}")
        elif width > 0 or height > 0:
            w = width if width > 0 else -1
            h = height if height > 0 else -1
            vf_filters.append(f"scale={w}:{h}")

        cmd = [
            ffmpeg_path,
            "-ss", str(start_seconds),
            "-i", str(video_path),
            "-frames:v", "1",
        ]

        if vf_filters:
            cmd.extend(["-vf", ",".join(vf_filters)])

        cmd.extend([
            "-q:v", str(quality),
            "-y",
            str(image_path),
        ])
        
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None
        
        if not image_path.exists():
            return None
        
        # 计算感知哈希
        phash = _calculate_phash(image_path)
        
        return {
            "index": i,
            "timestamp_ms": start_ms,
            "timestamp_str": f"{int(start_seconds // 60):02d}:{int(start_seconds % 60):02d}",
            "subtitle_text": text,
            "image_path": str(image_path),
            "phash": phash,
        }
    
    # 使用线程池并行处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(take_single_screenshot, task): task for task in tasks}
        for future in as_completed(futures):
            completed_count += 1
            on_progress(completed_count, total_tasks, f"单帧截图 {completed_count}/{total_tasks}")
            result = future.result()
            if result:
                screenshot_results[result["index"]] = result
    
    # 按顺序排列结果并去重
    screenshots: list[dict[str, Any]] = []
    seen_hashes: list[str] = []
    
    for i in sorted(screenshot_results.keys()):
        result = screenshot_results[i]
        phash = result["phash"]
        
        # 检查相似度
        is_duplicate = False
        for existing_hash in seen_hashes:
            similarity = _calculate_similarity(phash, existing_hash)
            if similarity >= similarity_threshold:
                is_duplicate = True
                break
        
        if is_duplicate:
            # 删除重复截图
            Path(result["image_path"]).unlink(missing_ok=True)
            continue
        
        seen_hashes.append(phash)
        screenshots.append(result)
    
    return screenshots


def take_scene_screenshots(
    *,
    video_path: Path,
    cfg: Any,
    progress_callback: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """
    使用场景变化检测截取视频帧（降级方案）。

    Args:
        video_path: 视频文件路径
        cfg: 配置对象
        progress_callback: 进度回调函数 (current, total, message)

    Returns:
        截图信息列表
    """
    on_progress = progress_callback or _noop_progress

    output_dir = Path(cfg.screenshot.output_dir) if hasattr(cfg, "screenshot") else Path("screenshots")
    output_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = cfg.screenshot.ffmpeg_path if hasattr(cfg, "screenshot") else "ffmpeg"
    scene_threshold = cfg.screenshot.scene_threshold if hasattr(cfg, "screenshot") else 0.3
    min_interval = cfg.screenshot.min_interval_seconds if hasattr(cfg, "screenshot") else 2
    similarity_threshold = cfg.screenshot.similarity_threshold if hasattr(cfg, "screenshot") else 0.95
    quality = getattr(cfg.screenshot, "quality", 2) if hasattr(cfg, "screenshot") else 2
    width = getattr(cfg.screenshot, "width", 0) if hasattr(cfg, "screenshot") else 0
    height = getattr(cfg.screenshot, "height", 0) if hasattr(cfg, "screenshot") else 0
    scale = getattr(cfg.screenshot, "scale", 1.0) if hasattr(cfg, "screenshot") else 1.0

    on_progress(0, 1, "执行场景变化检测...")

    # 构建视频滤镜
    vf_filters = [f"select='gt(scene,{scene_threshold})'", "showinfo"]
    if scale != 1.0:
        vf_filters.append(f"scale=iw*{scale}:ih*{scale}")
    elif width > 0 or height > 0:
        w = width if width > 0 else -1
        h = height if height > 0 else -1
        vf_filters.append(f"scale={w}:{h}")

    # 使用 ffmpeg 场景变化检测
    cmd = [
        ffmpeg_path,
        "-i", str(video_path),
        "-vf", ",".join(vf_filters),
        "-vsync", "vfr",
        "-q:v", str(quality),
        str(output_dir / "scene_%04d.jpg"),
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        on_progress(1, 1, "场景检测失败")
        return []

    # 收集生成的截图
    screenshots: list[dict[str, Any]] = []
    seen_hashes: list[str] = []  # 存储哈希值用于相似度比较
    scene_files = sorted(output_dir.glob("scene_*.jpg"))
    total_files = len(scene_files)

    on_progress(0, total_files, f"发现 {total_files} 张场景截图")

    for i, image_path in enumerate(scene_files):
        on_progress(i + 1, total_files, f"处理场景截图 {i + 1}/{total_files}")

        if not image_path.exists():
            continue

        # 计算感知哈希
        phash = _calculate_phash(image_path)

        # 检查相似度
        is_duplicate = False
        for existing_hash in seen_hashes:
            similarity = _calculate_similarity(phash, existing_hash)
            if similarity >= similarity_threshold:
                is_duplicate = True
                break

        if is_duplicate:
            image_path.unlink(missing_ok=True)
            continue

        seen_hashes.append(phash)

        # 从文件名提取时间戳（简化处理）
        timestamp_ms = i * min_interval * 1000
        minutes = int(timestamp_ms // 60000)
        seconds = int((timestamp_ms % 60000) // 1000)
        timestamp_str = f"{minutes:02d}:{seconds:02d}"

        screenshots.append({
            "index": i,
            "timestamp_ms": timestamp_ms,
            "timestamp_str": timestamp_str,
            "subtitle_text": "",
            "image_path": str(image_path),
            "phash": phash,
            "type": "scene",
        })

    on_progress(total_files, total_files, f"场景截图完成，共 {len(screenshots)} 张")
    return screenshots


def take_screenshots_with_description(
    *,
    video_path: Path,
    lines: list[dict[str, Any]],
    cfg: Any,
    llm_caller: LlmCaller | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """截取视频帧并生成 AI 描述。

    整合截图和 AI 描述生成，根据配置自动启用描述生成。

    Args:
        video_path: 视频文件路径
        lines: 字幕行列表
        cfg: 配置对象
        llm_caller: 可选的 LLM 调用回调
        progress_callback: 进度回调函数 (current, total, message)

    Returns:
        截图信息列表（含 AI 描述字段）
    """
    screenshots = take_screenshots(video_path=video_path, lines=lines, cfg=cfg, progress_callback=progress_callback)

    # 检查是否启用 AI 描述
    ai_describe = getattr(cfg.screenshot, "ai_describe", False) if hasattr(cfg, "screenshot") else False
    if ai_describe or llm_caller is not None:
        if progress_callback:
            progress_callback(0, len(screenshots), "生成 AI 描述...")
        screenshots = generate_descriptions(
            screenshots=screenshots,
            cfg=cfg,
            llm_caller=llm_caller,
        )
        if progress_callback:
            progress_callback(len(screenshots), len(screenshots), "AI 描述生成完成")

    return screenshots


def _calculate_phash(image_path: Path) -> str:
    """
    计算图像的感知哈希。
    
    使用 imagehash 库计算 pHash，如果不可用则回退到 MD5。
    支持缓存机制避免重复计算。
    """
    from vtf.cache import get_global_cache
    
    cache = get_global_cache()
    
    # 检查缓存
    cached_hash = cache.get_hash(image_path)
    if cached_hash is not None:
        return cached_hash
    
    # 计算哈希
    hash_value = ""
    
    if HAS_IMAGEHASH:
        try:
            img = Image.open(image_path)
            phash = imagehash.phash(img)
            hash_value = str(phash)
        except Exception:
            pass
    
    # 回退到 MD5
    if not hash_value:
        try:
            with open(image_path, "rb") as f:
                content = f.read()
            hash_value = hashlib.md5(content).hexdigest()[:16]
        except Exception:
            hash_value = ""
    
    # 存储到缓存
    if hash_value:
        cache.set_hash(image_path, hash_value)
    
    return hash_value


def _calculate_similarity(hash1: str, hash2: str) -> float:
    """
    计算两个哈希的相似度（0-1）。
    
    对于 imagehash 的十六进制字符串，计算汉明距离并转换为相似度。
    对于 MD5 哈希，使用简单比较。
    """
    if not hash1 or not hash2:
        return 0.0
    
    # 如果是 imagehash 的十六进制字符串（长度通常为16）
    if len(hash1) == 16 and len(hash2) == 16:
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            # 汉明距离越小越相似，最大距离为64（对于64位哈希）
            distance = h1 - h2
            similarity = 1.0 - (distance / 64.0)
            return max(0.0, min(1.0, similarity))
        except Exception:
            pass
    
    # 对于其他哈希，使用简单比较
    return 1.0 if hash1 == hash2 else 0.0


__all__ = ["take_screenshots", "take_scene_screenshots", "take_screenshots_with_description"]
