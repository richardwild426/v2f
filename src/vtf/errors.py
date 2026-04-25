EXIT_OK = 0
EXIT_USER = 1
EXIT_ENV = 2
EXIT_REMOTE = 3
EXIT_BUG = 4


class VtfError(Exception):
    exit_code: int = EXIT_BUG


class UserError(VtfError):
    exit_code = EXIT_USER


class EnvironmentError(VtfError):  # noqa: A001 - intentional shadowing
    exit_code = EXIT_ENV


class RemoteError(VtfError):
    exit_code = EXIT_REMOTE