from __future__ import annotations

from typing import Any

_OPEN = set("(《【〖「『〔｛")
_CLOSE_MAP = {
    "(": ")",
    "《": "》",
    "【": "】",
    "〖": "〗",
    "「": "」",
    "『": "』",
    "〔": "〕",
    "｛": "｝",
}
_COMMAS = set(",，")
_ENDERS = set("。!?…")
_NEW_THOUGHT_FIRSTS = set("第首先然后而且所以但是然而不过可是如果虽然")


def merge_into_lines(sentences: list[str]) -> list[str]:
    lines: list[str] = []
    buf = ""
    stack: list[str] = []
    for raw in sentences:
        s = raw.strip()
        if not s:
            continue
        for ch in s:
            if ch in _OPEN:
                stack.append(ch)
            elif stack and ch == _CLOSE_MAP.get(stack[-1]):
                stack.pop()
        in_bracket = bool(stack)
        split = False
        if buf:
            if in_bracket:
                split = False
            elif buf[-1] in _ENDERS or len(buf) > 15 and s[0] in _NEW_THOUGHT_FIRSTS:
                split = True
        if split:
            lines.append(buf)
            buf = s
        else:
            buf += s
    if buf:
        lines.append(buf)
    cleaned: list[str] = []
    for line in lines:
        ln = line.strip()
        while ln and ln[-1] in _COMMAS:
            ln = ln[:-1].strip()
        if ln:
            cleaned.append(ln)
    return cleaned


def merge_into_lines_with_timestamps(
    sentences: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """合并句子为字幕行，保留时间戳信息。

    接收 FunASR 转录输出的句子列表（每个句子包含 text, start_ms, end_ms），
    按语义合并为更长的字幕行，保留首句的 start_ms 和末句的 end_ms。

    Args:
        sentences: 句子列表，每项为 {"text": str, "start_ms": int, "end_ms": int}

    Returns:
        字幕行列表，每项为 {"text": str, "start_ms": int, "end_ms": int}
    """
    if not sentences:
        return []

    # 兼容：如果传入的是纯字符串列表，回退到无时间戳模式
    if sentences and isinstance(sentences[0], str):
        plain_lines = merge_into_lines(sentences)  # type: ignore[arg-type]
        return [{"text": t, "start_ms": 0, "end_ms": 0} for t in plain_lines]

    result: list[dict[str, Any]] = []
    buf_text = ""
    buf_start_ms = 0
    buf_end_ms = 0
    stack: list[str] = []

    for sent in sentences:
        text = sent.get("text", "").strip()
        if not text:
            continue

        start_ms = sent.get("start_ms", 0)
        end_ms = sent.get("end_ms", 0)

        for ch in text:
            if ch in _OPEN:
                stack.append(ch)
            elif stack and ch == _CLOSE_MAP.get(stack[-1]):
                stack.pop()
        in_bracket = bool(stack)

        split = False
        if buf_text:
            if in_bracket:
                split = False
            elif buf_text[-1] in _ENDERS or (len(buf_text) > 15 and text[0] in _NEW_THOUGHT_FIRSTS):
                split = True

        if split:
            # 清理尾部逗号
            cleaned = buf_text.strip()
            while cleaned and cleaned[-1] in _COMMAS:
                cleaned = cleaned[:-1].strip()
            if cleaned:
                result.append({
                    "text": cleaned,
                    "start_ms": buf_start_ms,
                    "end_ms": buf_end_ms,
                })
            buf_text = text
            buf_start_ms = start_ms
            buf_end_ms = end_ms
        else:
            if not buf_text:
                buf_start_ms = start_ms
            buf_text += text
            buf_end_ms = end_ms

    # 最后一段
    if buf_text:
        cleaned = buf_text.strip()
        while cleaned and cleaned[-1] in _COMMAS:
            cleaned = cleaned[:-1].strip()
        if cleaned:
            result.append({
                "text": cleaned,
                "start_ms": buf_start_ms,
                "end_ms": buf_end_ms,
            })

    return result


__all__ = ["merge_into_lines", "merge_into_lines_with_timestamps"]
