from vtf.pipeline.merge import merge_into_lines, merge_into_lines_with_timestamps


def test_simple_concat():
    out = merge_into_lines(["你好", "世界"])
    assert out == ["你好世界"]


def test_split_on_period():
    out = merge_into_lines(["你好。", "世界"])
    assert out == ["你好。", "世界"]


def test_does_not_split_inside_brackets():
    out = merge_into_lines(["他说（这", "是括号）。", "结束"])
    assert out == ["他说（这是括号）。", "结束"]


def test_strips_trailing_comma():
    out = merge_into_lines(["你好，"])
    assert out == ["你好"]


def test_skips_empty():
    out = merge_into_lines(["", " ", "正文"])
    assert out == ["正文"]


# ---- merge_into_lines_with_timestamps tests ----


def test_ts_simple_concat():
    sentences = [
        {"text": "你好", "start_ms": 1000, "end_ms": 2000},
        {"text": "世界", "start_ms": 3000, "end_ms": 4000},
    ]
    out = merge_into_lines_with_timestamps(sentences)
    assert len(out) == 1
    assert out[0]["text"] == "你好世界"
    assert out[0]["start_ms"] == 1000
    assert out[0]["end_ms"] == 4000


def test_ts_split_on_period():
    sentences = [
        {"text": "你好。", "start_ms": 1000, "end_ms": 2000},
        {"text": "世界", "start_ms": 3000, "end_ms": 4000},
    ]
    out = merge_into_lines_with_timestamps(sentences)
    assert len(out) == 2
    assert out[0]["text"] == "你好。"
    assert out[0]["start_ms"] == 1000
    assert out[0]["end_ms"] == 2000
    assert out[1]["text"] == "世界"
    assert out[1]["start_ms"] == 3000
    assert out[1]["end_ms"] == 4000


def test_ts_preserves_first_and_last_timestamp():
    """合并行的 start_ms 取首句，end_ms 取末句。"""
    sentences = [
        {"text": "第一句", "start_ms": 100, "end_ms": 200},
        {"text": "第二句", "start_ms": 300, "end_ms": 400},
        {"text": "第三句", "start_ms": 500, "end_ms": 600},
    ]
    out = merge_into_lines_with_timestamps(sentences)
    assert len(out) == 1
    assert out[0]["text"] == "第一句第二句第三句"
    assert out[0]["start_ms"] == 100
    assert out[0]["end_ms"] == 600


def test_ts_skips_empty():
    sentences = [
        {"text": "", "start_ms": 0, "end_ms": 0},
        {"text": "正文", "start_ms": 1000, "end_ms": 2000},
    ]
    out = merge_into_lines_with_timestamps(sentences)
    assert len(out) == 1
    assert out[0]["text"] == "正文"


def test_ts_empty_input():
    out = merge_into_lines_with_timestamps([])
    assert out == []


def test_ts_compatible_with_plain_strings():
    """兼容纯字符串输入。"""
    out = merge_into_lines_with_timestamps(["你好", "世界"])  # type: ignore[arg-type]
    assert len(out) == 1
    assert out[0]["text"] == "你好世界"
    assert out[0]["start_ms"] == 0
