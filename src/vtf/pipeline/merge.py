from __future__ import annotations

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
            elif buf[-1] in _ENDERS:
                split = True
            elif len(buf) > 15 and s[0] in _NEW_THOUGHT_FIRSTS:
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


__all__ = ["merge_into_lines"]