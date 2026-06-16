# Quality Guidelines

> Code quality standards for `vtf`. Reflects `pyproject.toml` tooling and real patterns.

---

## Overview

Quality is enforced by three tools, all configured in `pyproject.toml`. Code must pass all three
before commit:

```bash
uv run ruff check src tests     # lint + import sort
uv run mypy                      # strict type checking (files = ["src/vtf"])
uv run pytest                    # tests
```

Targets: Python **3.11+**, line length **100**.

---

## Required Patterns

- **`from __future__ import annotations`** as the first import line of every module.
- **Full type annotations everywhere.** `mypy` runs in `strict` mode over `src/vtf`; untyped
  defs, implicit `Any`, and missing return types will fail. Use modern syntax: `str | None`,
  `list[str]`, `dict[str, Any]`.
- **Keyword-only arguments for pipeline functions**: `def fetch(*, url: str, cfg: Any) -> dict[str, Any]`.
  This is the established calling convention in `pipeline/`.
- **Protocols for pluggable interfaces** (`typing.Protocol`), not ABCs or inheritance. See
  `platforms/base.py::Platform` and `sinks/base.py::Sink`. Register concrete implementations in
  the package `__init__.py`.
- **`pathlib.Path`** for all filesystem paths; `json` for serialization with `ensure_ascii=False`.
- Ruff rule sets in effect: `E, F, W, I, B, UP, SIM`. In particular `I` (isort) means imports
  are auto-sorted — run `ruff check --fix` rather than hand-ordering. `UP` pushes modern syntax,
  `SIM` flags needless complexity, `B` catches bugbears.

---

## Forbidden Patterns

- **No `print()` for diagnostics.** Use the `Logger` (stderr); reserve stdout (`click.echo`) for
  the JSON data payload only. See `logging-guidelines.md`.
- **No `click` / CLI concerns in `pipeline/` or adapter packages.** Business logic stays free of
  `click`, `sys.exit`, and stdout writes; it raises `VtfError` subclasses instead.
- **No bare `except:` / `except Exception` that swallows errors.** Catch `VtfError` at the command
  boundary and convert to `SystemExit(e.exit_code)`; let real bugs surface.
- **No new logging / DB / heavy dependencies.** Runtime deps are intentionally minimal
  (`click`, `jinja2`). Adding to `dependencies` needs a deliberate decision.
- **Do not silence type errors with `# type: ignore`** unless unavoidable and commented; strict
  mypy is a feature, not an obstacle. (The one sanctioned exception-style suppression in the repo
  is `# noqa: A001` on the intentional `EnvironmentError` shadow in `errors.py`.)

---

## Testing Requirements

- Tests use **pytest** + **pytest-mock**; layout is one `tests/test_<module>.py` per source module.
- Shared fixtures go in `tests/conftest.py`; sample data goes in `tests/fixtures/` as JSON
  (e.g. `raw_yt_dlp_bilibili.json`) loaded by a fixture.
- **Every behavioral contract gets a test.** External processes (`yt-dlp`, `lark-cli`, FunASR)
  are mocked — tests must not hit the network or invoke real binaries.
- Error contracts are regression-tested explicitly (see `error-handling.md` and
  `tests/test_yt_dlp_errors.py`, `tests/test_errors.py`).
- When you add a `commands/` + `pipeline/` pair, test the pipeline logic directly and the command's
  error-to-exit-code translation.

---

## Code Review Checklist

- [ ] `from __future__ import annotations` present; fully typed; passes `mypy` strict.
- [ ] `ruff check src tests` clean (imports sorted, no `B`/`SIM`/`UP` violations).
- [ ] Layer boundaries respected: no `click`/stdout/`sys.exit` in `pipeline/` or adapters.
- [ ] Failures raise the right `VtfError` subclass (correct exit-code semantics).
- [ ] Logs go to stderr with a `step=`; no secrets logged; stdout carries only JSON.
- [ ] New behavior has tests; external tools are mocked; `uv run pytest` passes.
- [ ] User-facing strings (errors, logs) are in Chinese, consistent with the codebase.
