# Database Guidelines

> Data persistence patterns for this project.

---

## Overview

**This project has no database, ORM, or migrations.** `vtf` is a stateless CLI pipeline.
Do not introduce SQLAlchemy, an ORM, a migration tool, or any DB dependency without an
explicit decision — it would be a major architectural change, not a routine addition.

State lives entirely on the filesystem as plain files. "Persistence" here means three things:

| Kind | Location | Format | Read/written by |
|------|----------|--------|-----------------|
| Pipeline intermediates | `--workdir` (default `$XDG_CACHE_HOME/vtf/`) | JSON files (`meta.json`, `transcript.json`, `lines.json`, `summary.json`, …) | each `commands/*.py` step |
| User / project config | `~/.config/vtf/config.toml`, `./vtf.toml` | TOML → dataclasses | `config.py` |
| Shipped assets | `vtf/assets/`, `vtf/prompts/` | TOML schemas, markdown prompts | `config.py`, `pipeline/analyze.py` |

---

## Query Patterns

Not applicable — there are no queries. Data flow is **stdin/stdout JSON piping** between
pipeline steps (see `README.md` for the canonical pipeline). Each step is a pure
transformation: read JSON in, write JSON out. Keep it that way.

When reading/writing files:

- Use `pathlib.Path` (never raw string paths or `os.path` joins).
- Read JSON with `json.loads(...)` / `path.read_text("utf-8")`; always pass `encoding="utf-8"`.
- Write JSON with `json.dumps(data, ensure_ascii=False)` so Chinese text stays readable.

---

## Migrations

Not applicable. The only "schema" concept is the **Feishu output schema** (TOML files under
`vtf/assets/schemas/`, default `assets/schemas/baokuan.toml`), resolved by
`config.py::resolve_feishu_schema_path`. See `feishu-schema-contract.md` for that contract.
These schemas are versioned as files in git, not via a migration system.

---

## Naming Conventions

- Config keys mirror the dataclass field names in `config.py` (e.g. `[sink.feishu] base_token`).
- Environment overrides follow `VTF_<SECTION>_<FIELD>` (uppercased dataclass path), handled by
  `config.py::_merge_env`. Legacy aliases (`TABLE_TOKEN`, `TABLE_ID`) are kept for
  backward compatibility — do not remove them.
- Intermediate files use lowercase, descriptive names matching the pipeline step.

---

## Common Mistakes

- **Reaching for a database.** The design is intentionally stateless and file-based. If you
  think you need persistence, you almost certainly need another JSON intermediate in `--workdir`.
- Hardcoding `~/.config` or `~/.cache` instead of using `config.py::default_user_path()` /
  `default_workdir()` (which respect `XDG_CONFIG_HOME` / `XDG_CACHE_HOME`).
- Dropping `ensure_ascii=False` on `json.dumps`, producing `\uXXXX`-escaped Chinese output.
