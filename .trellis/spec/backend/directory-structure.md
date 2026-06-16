# Directory Structure

> How `vtf` backend code is organized. Reflects the actual layout under `src/vtf/`.

---

## Overview

`vtf` is a single Python package (`src/vtf/`) exposing a `click` CLI (`vtf = "vtf.cli:main"`).
It is a **stateless pipeline tool**: each step reads JSON from stdin / files and writes
JSON to stdout. There is no server, no database, no long-lived process.

The code is split into three concentric layers plus shared infrastructure:

```
CLI layer        commands/   →  thin click adapters (one module per subcommand)
Core layer       pipeline/   →  pure business logic, no click dependency
Adapter layer    platforms/  →  pluggable backends behind a Protocol
                 sinks/
                 transcribe/
Infrastructure   config.py errors.py logging.py _ctx.py
```

**Dependency direction is one-way**: `cli.py` → `commands/` → `pipeline/` → `platforms|sinks|transcribe` → infra.
`pipeline/` and the adapters must never import `click` or anything from `commands/`.

---

## Directory Layout

```
src/vtf/
├── __init__.py
├── __main__.py            # `python -m vtf` entry
├── cli.py                 # click group `main`; global options; registers all subcommands
├── _ctx.py                # get_config / get_workdir / get_logger factories from click ctx
├── config.py              # dataclass config tree + multi-source load_config()
├── errors.py              # VtfError hierarchy + exit codes
├── logging.py             # Logger class (stderr, text/json)
├── commands/              # CLI adapter layer — one file per subcommand, each exports `cmd`
│   ├── fetch.py download.py transcribe.py merge.py analyze.py
│   ├── assemble.py emit.py run.py init.py config_cmd.py install.py doctor.py
│   └── _stub.py           # shared helper (underscore = private)
├── pipeline/              # core logic — pure functions, keyword-only args, raise VtfError
│   ├── fetch.py download.py merge.py analyze.py assemble.py
│   └── yt_dlp.py          # yt-dlp subprocess + error formatting
├── platforms/             # URL platform adapters behind Platform Protocol
│   ├── base.py            # Platform Protocol
│   ├── bilibili.py youtube.py generic.py
│   ├── _normalize.py      # shared metadata normalization helper
│   └── __init__.py        # REGISTRY + detect(url)
├── sinks/                 # output adapters behind Sink Protocol
│   ├── base.py            # Sink Protocol + EmitOutcome
│   ├── feishu.py markdown.py schema.py
│   └── __init__.py
├── transcribe/            # transcription backends
│   └── funasr.py
└── prompts/               # LLM prompt templates (jinja2-rendered markdown)
    └── summary.md breakdown.md rewrite.md

tests/                     # one test_<module>.py per source module
├── conftest.py            # shared pytest fixtures
├── fixtures/              # JSON fixtures (e.g. raw_yt_dlp_bilibili.json)
└── test_*.py
```

---

## Module Organization

When adding a new feature, place code by responsibility:

- **New CLI subcommand** → add `commands/<name>.py` exporting a `cmd` (a `@click.command`),
  then register it in `cli.py` via `main.add_command(_<name>.cmd, name="<name>")`.
  The command module stays thin: parse args → `get_config`/`get_logger` from `_ctx` →
  call into `pipeline/` → catch `VtfError` → write result JSON to stdout.
- **New pipeline step / business logic** → add `pipeline/<name>.py` as a pure function with
  keyword-only args (`def step(*, ...) -> ...`). No `click`, no stdout writes, no `sys.exit`.
  Signal failure by raising a `VtfError` subclass.
- **New platform** → add `platforms/<name>.py` implementing the `Platform` Protocol
  (`matches`, `cookie_args`, `normalize_metadata`), then register the instance in
  `platforms/__init__.py::REGISTRY`.
- **New output target** → add `sinks/<name>.py` implementing the `Sink` Protocol
  (`available`, `emit`).
- **New transcription backend** → add under `transcribe/`.

---

## Naming Conventions

- Modules: lowercase, no separators or `snake_case` (`yt_dlp.py`, `config_cmd.py`).
- **Underscore prefix = private / internal helper** not meant for outside import:
  `_ctx.py`, `_stub.py`, `_normalize.py`, and private functions like `_merge_dict`, `_coerce`.
- Every `commands/*.py` module exports its command object as `cmd` (registered with an explicit
  `name=` in `cli.py`, so the module name and CLI name can differ — e.g. `config_cmd.py` → `config`).
- Protocol interfaces live in each package's `base.py`; the registry / factory lives in `__init__.py`.
- `from __future__ import annotations` is the first line of every module.

---

## Examples

- Clean CLI-vs-core split: `src/vtf/commands/fetch.py` (adapter) calls
  `src/vtf/pipeline/fetch.py::fetch` (logic). Copy this pattern for new commands.
- Protocol + registry pattern: `src/vtf/platforms/base.py` + `src/vtf/platforms/__init__.py`.
- Multi-source config tree: `src/vtf/config.py`.
