import json

from click.testing import CliRunner

from vtf.cli import main


def test_help_lists_subcommands():
    r = CliRunner().invoke(main, ["--help"])
    assert r.exit_code == 0
    assert "run" in r.output
    assert "fetch" in r.output
    assert "emit" in r.output
    assert "finish" in r.output


def test_finish_assembles_and_emits_markdown(tmp_path):
    """finish = assemble + emit：回填后一条命令从 workdir 收尾出报告。"""
    (tmp_path / "meta.json").write_text(
        json.dumps({"title": "T", "thumbnail": "https://example.com/c.jpg"}),
        encoding="utf-8",
    )
    (tmp_path / "lines.json").write_text(
        json.dumps({"lines": ["a", "b"]}), encoding="utf-8"
    )
    for kind, result in [
        ("summary", {"text": "S"}),
        ("breakdown", {"text": "B"}),
        ("rewrite", {"text": "R"}),
    ]:
        (tmp_path / f"{kind}.json").write_text(
            json.dumps({"kind": kind, "result": result}), encoding="utf-8"
        )

    r = CliRunner().invoke(
        main, ["--workdir", str(tmp_path), "finish", "--sink", "markdown"]
    )

    assert r.exit_code == 0, r.output
    # markdown sink 把报告写到 stdout，且含封面 URL
    assert "https://example.com/c.jpg" in r.output


def test_global_flags_recognized():
    r = CliRunner().invoke(main, ["--quiet", "--help"])
    assert r.exit_code == 0


def test_run_has_no_skip_option(tmp_path):
    r = CliRunner().invoke(
        main, ["--workdir", str(tmp_path), "run", "--skip", "rewrite", "https://example.com/v"]
    )
    assert r.exit_code != 0
    assert "No such option: --skip" in r.output
