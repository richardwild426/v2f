# Logging Guidelines

> How logging works in `vtf`. Reflects `src/vtf/logging.py` and its usage.

---

## Overview

Logging is done through a small project-local `Logger` class (`src/vtf/logging.py`).
**There is no `logging` stdlib usage and no third-party logging library** — do not add one.

The single most important rule:

> **stdout is for data, stderr is for logs.**

Every pipeline command writes its JSON result to **stdout** via `click.echo(...)`, and writes
all human/diagnostic messages to **stderr** via the `Logger`. This is what lets the pipeline be
piped (`vtf fetch ... > meta.json`) without log lines corrupting the data stream.

Get a logger inside a command via the factory, never by constructing `Logger()` directly:

```python
from vtf._ctx import get_logger

log = get_logger(ctx)        # reads --json / --quiet from click ctx.obj
log.error(str(e), step="fetch")
```

---

## Log Levels

`Logger` exposes exactly three levels — there is no `debug`:

| Level | Method | When |
|-------|--------|------|
| info  | `log.info(...)`  | Normal progress / step narration. Suppressed by `--quiet`. |
| warn  | `log.warn(...)`  | Recoverable / degraded conditions (e.g. a sink falling back). Always shown. |
| error | `log.error(...)` | A failure being reported before exit. Always shown. |

`--quiet` suppresses **info only**; warnings and errors always print.

---

## Structured Logging

Each log method takes an optional `step` and `data`:

```python
def info(self, msg: str, step: str | None = None, data: dict[str, Any] | None = None) -> None
```

- **`step`** — the pipeline stage name (`"fetch"`, `"download"`, `"transcribe"`, …). Always pass it;
  it becomes the `[step]` prefix in text mode and the `step` field in JSON mode.
- **`data`** — optional structured payload (a `dict`), included only in JSON mode.

Two output modes, selected by the global `--json` flag:

- Text mode (default): `[fetch] 抓取元数据失败` to stderr.
- JSON mode (`--json`): one JSON object per line (JSON Lines) to stderr, with
  `ts` (ISO timestamp), `level`, `msg`, and optionally `step` / `data`.

JSON records use `ensure_ascii=False` so Chinese messages stay readable.

---

## What to Log

- Step failures, right before raising `SystemExit` — this is the dominant pattern in `commands/`:

  ```python
  try:
      meta = fetch(url=url, cfg=cfg)
  except VtfError as e:
      log.error(str(e), step="fetch")
      raise SystemExit(e.exit_code) from e
  ```

- Degraded / fallback behavior (use `warn`, e.g. a sink that became unavailable).
- Always attach the `step=` for the current stage.

Log **messages are written in Chinese** (matching error messages and the CLI's user-facing
language). Keep new log strings consistent with that.

---

## What NOT to Log

- **Never log to stdout.** stdout is reserved for the JSON data payload. Logging there breaks pipes.
- Do not log secrets or credentials: Feishu `base_token` / `table_id`, `lark-cli` identity,
  cookie file contents, or any value pulled from `[sink.feishu]` config.
- Do not log full cookie data or browser session material from the platform cookie handling.
- Avoid dumping entire transcripts / large payloads at info level; reference counts or ids instead.
