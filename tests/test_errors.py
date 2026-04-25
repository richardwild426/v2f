from vtf.errors import (
    EXIT_BUG,
    EXIT_ENV,
    EXIT_OK,
    EXIT_REMOTE,
    EXIT_USER,
    RemoteError,
    UserError,
)
from vtf.errors import (
    EnvironmentError as VtfEnvError,
)


def test_exit_codes_distinct():
    assert {EXIT_OK, EXIT_USER, EXIT_ENV, EXIT_REMOTE, EXIT_BUG} == {0, 1, 2, 3, 4}


def test_exception_carries_exit_code():
    e = UserError("bad arg")
    assert e.exit_code == EXIT_USER
    assert str(e) == "bad arg"
    assert VtfEnvError("missing").exit_code == EXIT_ENV
    assert RemoteError("412").exit_code == EXIT_REMOTE
