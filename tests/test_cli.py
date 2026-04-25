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
