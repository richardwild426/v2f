from vtf.pipeline.merge import merge_into_lines


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
