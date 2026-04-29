# Claude Code Remediation Brief

This document records the current audit findings for the `vtf` project, based on the principles in the Agent Skills specification.

The goal is not to restate the audit in prose. The goal is to give Claude Code a concrete, verifiable repair plan.

## Scope

Audit target:

- `vtf/SKILL.md`
- `vtf/scripts/`
- `vtf/references/`
- `vtf/assets/`
- Python CLI implementation under `src/vtf/`
- packaging in `pyproject.toml`

Validation already run:

- `uvx --from skills-ref agentskills validate ./vtf` ✅
- `uv run pytest` ✅ (`63 passed`)
- `uv run ruff check src tests` ❌
- `uv run mypy` ❌
- `uv build` ✅, but packaging output is incomplete for skill distribution

## Executive Summary

The project is structurally valid as an Agent Skill, but it is not operationally complete.

The main problem is a mismatch between:

- what the skill and docs promise,
- what the packaged artifact actually ships,
- what the CLI actually enforces,
- and what the tests currently protect.

In short: the skill validates, but the end-to-end delivery contract is inconsistent.

## Required Repair Order

Fix in this order:

1. Repair packaging and distribution of the skill bundle.
2. Repair installer and path-resolution bugs.
3. Remove or implement dead configuration paths.
4. Align workflow contracts across skill/docs/code/tests.
5. Restore static quality gates (`ruff`, `mypy`).
6. Add tests for the broken contracts above.

Do not stop after documentation-only changes. The acceptance criteria require code, docs, and tests to agree.

## Findings

### 1. Skill bundle is not shipped with the package

Severity: high

Problem:

- The wheel contains Python code and prompt files, but does not ship the skill bundle itself.
- `vtf/SKILL.md`, `vtf/references/*`, `vtf/scripts/setup.sh`, and `vtf/assets/*` are not part of the built wheel.
- This breaks the practical delivery model implied by the README and skill docs.

Evidence:

- `pyproject.toml` only packages `src/vtf`
- `pyproject.toml` only declares shared-data for `src/vtf/prompts`
- `README.md` says agents can load `vtf/SKILL.md`
- `vtf/references/installation.md` recommends `uvx --from ... vtf doctor`

Why this matters:

- An Agent Skill is not just Python code. The `SKILL.md`, references, scripts, and assets are part of the product.
- A user can install the CLI and still not receive the skill materials that the agent is expected to load.

Required fix:

- Decide the supported distribution model explicitly.
- Then make packaging match that model.

Acceptable directions:

1. Ship the skill bundle with the Python package.
2. Or clearly separate "CLI package" and "skill bundle" as two install targets, with installation instructions for both.

Preferred direction:

- Ship the skill bundle with the package, or add a dedicated installation command that exports the skill into a standard skills directory.

Acceptance criteria:

- After installation from the packaged artifact, the skill files needed by an agent are present and discoverable.
- The documented installation flow matches the actual shipped artifact.

### 2. `setup.sh` and installation docs use broken Python detection logic

Severity: high

Problem:

- The script checks `if [ -x "$py" ]` for values like `python3` and `python`.
- That only works for literal paths, not commands resolved via `PATH`.
- The same broken pattern appears in the installation reference.

Evidence:

- `vtf/scripts/setup.sh`
- `vtf/references/installation.md`

Why this matters:

- The advertised "auto-configure FunASR" flow is unreliable.
- It may fail to detect a working Python interpreter even when one exists in `PATH`.

Required fix:

- Replace command detection logic with a `command -v` based strategy for command names.
- Keep direct path checks only for explicit filesystem paths like `~/.venv/funasr/bin/python`.

Acceptance criteria:

- The installer finds `python3` or `python` from `PATH` when available.
- The documentation uses the same working logic as the script.

### 3. `setup.sh` is described as a one-step installer but does not install `vtf`

Severity: high

Problem:

- The script is presented as "one-click install + setup".
- It installs dependencies and writes config, but it does not install the `vtf` command itself.
- It ends by warning that `vtf` may not exist.

Evidence:

- `vtf/SKILL.md`
- `README.md`
- `vtf/scripts/setup.sh`

Why this matters:

- The script name and docs promise a complete setup path.
- The real behavior is partial bootstrapping.

Required fix:

- Either make the script actually install `vtf`, or rename/reframe it as a dependency bootstrapper.
- Make the docs state the exact prerequisite order.

Acceptance criteria:

- The documented quick-start path results in a usable `vtf` command, or the docs explicitly require a prior installation step.

### 4. `sink.feishu.lark_cli` is dead configuration

Severity: high

Problem:

- The config model and docs expose `sink.feishu.lark_cli`.
- The actual implementation ignores it and always uses `shutil.which("lark-cli")`.

Evidence:

- `src/vtf/config.py`
- `vtf/references/configuration.md`
- `src/vtf/sinks/feishu.py`
- `src/vtf/commands/init.py`

Why this matters:

- Users cannot override the command path even though the product claims they can.
- This is a false configuration surface.

Required fix:

- Either implement the config everywhere the command is resolved,
- or remove the config field and all documentation that advertises it.

Preferred direction:

- Implement it consistently in `doctor`, `init feishu`, and the Feishu sink.

Acceptance criteria:

- Setting `sink.feishu.lark_cli` changes the executable actually used.
- Tests cover the override behavior.

### 5. Feishu schema path defaults are invalid in practice

Severity: high

Problem:

- Docs recommend `schema = "assets/schemas/baokuan.toml"`.
- Code resolves relative schema paths from `Path.cwd()`.
- The packaged artifact does not currently ship those assets anyway.

Evidence:

- `vtf/references/configuration.md`
- `vtf/references/feishu.md`
- `vtf/references/installation.md`
- `src/vtf/sinks/feishu.py`
- `src/vtf/commands/init.py`

Why this matters:

- The default documented Feishu configuration is broken for normal users.
- The system is mixing at least three different roots: current working directory, config location, and skill root.

Required fix:

- Define one path-resolution rule and apply it everywhere.

Recommended rule:

- Absolute paths work as-is.
- Relative paths in config files resolve from the config file directory.
- Relative paths inside skill docs resolve from the skill root.
- Runtime code should not silently assume `cwd` unless the CLI explicitly documents that behavior.

Acceptance criteria:

- The documented sample schema path works in a real install.
- `init feishu` and `emit` use the same resolution semantics.

### 6. Workflow contract is inconsistent about whether all three analyses are required

Severity: high

Problem:

- Some docs say `summary`, `breakdown`, and `rewrite` are all required.
- Some docs say missing analysis kinds are acceptable.
- The implementation and tests allow partial `analyses` in `assemble`.
- The install doc even uses a smoke command that skips all three analyses.

Evidence:

- `vtf/SKILL.md`
- `vtf/references/pipeline.md`
- `vtf/references/data-shapes.md`
- `vtf/references/installation.md`
- `src/vtf/pipeline/assemble.py`
- `tests/test_assemble.py`
- `src/vtf/commands/run.py`

Why this matters:

- This is not a wording issue. It changes what counts as a completed pipeline.
- Agents cannot reliably decide whether to continue, retry, or fail.

Required fix:

- Pick one contract and enforce it across docs, code, and tests.

Two valid options:

1. Strict contract: all three analyses are required for completion.
2. Flexible contract: partial analyses are allowed, but completion criteria must say so explicitly.

Preferred direction:

- Keep strict completion for the canonical workflow, but allow explicit user-directed skip modes with clearly labeled degraded output.

Acceptance criteria:

- `SKILL.md`, pipeline docs, install docs, and data-shape docs all say the same thing.
- `assemble` and related tests enforce the chosen rule.

### 7. Cover URL is documented as mandatory but not enforced

Severity: medium

Problem:

- Docs say the final output must contain the cover URL.
- The markdown sink silently emits an empty cover cell if `meta.thumbnail` is missing.
- Current tests do not protect the cover requirement.

Evidence:

- `vtf/SKILL.md`
- `vtf/references/pipeline.md`
- `src/vtf/sinks/markdown.py`
- `tests/test_sink_markdown.py`

Why this matters:

- A documented hard requirement should either be enforced or downgraded to a best-effort behavior.

Required fix:

- Choose whether thumbnail is mandatory or optional.
- If mandatory, validate before emit.
- If optional, rewrite the docs accordingly.

Acceptance criteria:

- Code, tests, and docs agree on the thumbnail contract.

### 8. Static quality gates are currently red

Severity: medium

Problem:

- The README development section claims `ruff` and `mypy` should pass.
- They currently fail.

Evidence:

- `README.md`
- `uv run ruff check src tests`
- `uv run mypy`

Current concrete failures:

- line-length and simplification violations in command modules and tests
- `Any` return leakage in Feishu and init helpers
- type mismatch in `src/vtf/commands/run.py`

Required fix:

- Make `ruff` and `mypy` pass without weakening the configured standards.

Acceptance criteria:

- `uv run ruff check src tests` passes.
- `uv run mypy` passes.

### 9. `doctor` contains a broken internal doc reference

Severity: low

Problem:

- `doctor` prints `references/INSTALL.md`, which does not exist.

Evidence:

- `src/vtf/commands/doctor.py`

Required fix:

- Replace the bad path with the real document path.

Acceptance criteria:

- All remediation links printed by the CLI point to real project documents.

## Test Gaps To Add

Add focused tests for the repair work above.

Minimum additions:

1. Packaging test or artifact assertion for the shipped skill bundle.
2. Installer/unit test for Python interpreter detection logic.
3. Config test for `sink.feishu.lark_cli` override behavior.
4. Path-resolution test for Feishu schema paths.
5. Contract test for strict vs flexible analysis completion.
6. Thumbnail/cover contract test for markdown emission.

## Recommended Implementation Notes

These are implementation notes, not hard requirements.

### Packaging

- If the skill is intended for local agent discovery, consider shipping a copyable skill bundle and exposing an install/export command.
- If the skill is only meant to live in-repo, then remove language implying that package installation alone makes the skill available to agents.

### Path Resolution

- Centralize path resolution in one helper module.
- Avoid duplicating ad-hoc `Path.cwd()` logic in multiple commands.

### Completion Contract

- Separate "pipeline completion" from "partial debug run".
- If `--skip` remains, it should produce a clearly degraded state, not a silently successful canonical result.

## Final Acceptance Checklist

Claude Code should not stop until all of the following are true:

- `uvx --from skills-ref agentskills validate ./vtf` passes
- `uv run pytest` passes
- `uv run ruff check src tests` passes
- `uv run mypy` passes
- packaged installation contains or correctly installs the skill materials
- documented quick-start flow matches the real installation and runtime behavior
- schema path examples work as documented
- Feishu command override is either implemented or removed everywhere
- completion rules for `summary` / `breakdown` / `rewrite` are consistent across docs, code, and tests
- cover URL behavior is consistent across docs, code, and tests

## Non-Goal

Do not paper over these issues with documentation-only edits.

The core problem is consistency of product behavior. The repair must change the implementation where the docs currently describe behavior that the code does not actually provide.
