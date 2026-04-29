from click.testing import CliRunner

from vtf.cli import main


def test_help_lists_subcommands():
    r = CliRunner().invoke(main, ["--help"])
    assert r.exit_code == 0
    assert "run" in r.output
    assert "fetch" in r.output
    assert "emit" in r.output


def test_global_flags_recognized():
    r = CliRunner().invoke(main, ["--quiet", "--help"])
    assert r.exit_code == 0


def test_run_has_no_skip_option(tmp_path):
    r = CliRunner().invoke(
        main, ["--workdir", str(tmp_path), "run", "--skip", "rewrite", "https://example.com/v"]
    )
    assert r.exit_code != 0
    assert "No such option: --skip" in r.output
