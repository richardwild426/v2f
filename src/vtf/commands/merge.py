from __future__ import annotations

import json
import sys

import click

from vtf.pipeline.merge import merge_into_lines


@click.command(name="merge", help="合并 transcript 句子为字幕行(stdin → stdout)")
def cmd() -> None:
    data = json.load(sys.stdin)
    sentences = data.get("sentences", [])
    lines = merge_into_lines(sentences)
    click.echo(json.dumps({"lines": lines}, ensure_ascii=False))
