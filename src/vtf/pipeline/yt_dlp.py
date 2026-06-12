from __future__ import annotations

from vtf.platforms.base import Platform


def format_yt_dlp_error(*, action: str, returncode: int, stderr: str, platform: Platform) -> str:
    detail = stderr.strip()[:200]
    message = f"yt-dlp {action}失败({returncode}):{detail}"
    if platform.name == "bilibili" and _looks_like_http_412(stderr):
        message += (
            "\n  → B站返回 HTTP 412，通常是浏览器 Cookie 不可用或已过期。"
            "请确认已在浏览器登录 B站；如当前配置是 "
            "`platform.bilibili.cookies_from_browser = \"chrome\"`，"
            "但你实际使用 Safari/Firefox/Edge，请改成对应浏览器；"
            "也可以配置 `platform.bilibili.cookies_file` 指向导出的 cookies.txt。"
        )
    return message


def _looks_like_http_412(stderr: str) -> bool:
    normalized = stderr.lower()
    return "412" in normalized and (
        "precondition failed" in normalized or "http error 412" in normalized
    )
