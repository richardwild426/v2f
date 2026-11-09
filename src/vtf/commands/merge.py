from __future__ import annotations

import json
import sys

import click

from vtf.pipeline.merge import merge_into_lines, merge_into_lines_with_timestamps


@click.command(name="merge", help="合并 transcript 句子为字幕行(stdin → stdout)")
def cmd() -> None:
    data = json.load(sys.stdin)
    sentences = data.get("sentences", [])

    if not sentences:
        click.echo(json.dumps({"lines": []}, ensure_ascii=False))
        return

    # 检测输入格式：dict（带时间戳）还是纯字符串
    has_timestamps = isinstance(sentences[0], dict) and "start_ms" in sentences[0]

    if has_timestamps:
        lines = merge_into_lines_with_timestamps(sentences)
        click.echo(json.dumps({"lines": lines}, ensure_ascii=False))
    else:
        lines = merge_into_lines(sentences)
        click.echo(json.dumps({"lines": lines}, ensure_ascii=False))
