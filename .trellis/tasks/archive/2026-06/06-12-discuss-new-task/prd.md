# Prevent missing Feishu field content in vtf output

## Goal

Make the vtf analysis and Feishu emit flow reliably fill the content expected by the configured Feishu Base schema. Missing field content should be prevented where possible during prompt generation, detected before writing records, and reported with actionable errors instead of silently creating incomplete rows.

## What I Already Know

* The user reports frequent omissions in the current analysis/generation flow: output does not consistently populate every intended Feishu Base field.
* The default Feishu schema is `vtf/assets/schemas/baokuan.toml`.
* The schema maps many Feishu columns to `meta`, `lines`, and `analyses` paths, including `analyses.summary.*`, `analyses.breakdown.*`, and `analyses.rewrite.*`.
* `vtf analyze` currently emits a prompt plus a small `schema_hint`, but it does not derive that hint from the Feishu schema.
* `vtf assemble` currently only verifies that `summary`, `breakdown`, and `rewrite` exist and have non-null `result` values.
* `Feishu.emit` currently renders schema fields at write time and converts missing non-attachment values to empty strings.
* Therefore, a partially filled LLM result can silently become empty Feishu cells.

## Assumptions (Temporary)

* The default behavior should use a tiered policy: analysis-derived fields are strict, platform metadata fields are lenient, and attachment fields remain best-effort.
* Attachment fields may remain best-effort because local files can be missing or oversized independently of LLM analysis quality.
* The MVP can focus on schema-backed validation and prompt guidance without adding live reads from the remote Feishu table during every emit.

## Open Questions

* None.

## Requirements (Evolving)

* Use the configured Feishu schema as the source of truth for expected output fields.
* Use a tiered validation policy:
  * `analyses.*` fields are required by default and block Feishu emit when missing or empty.
  * `meta.*` fields are optional by default except existing hard requirements such as `meta.thumbnail`.
  * `attachment` fields remain best-effort and do not block record creation.
* Infer requiredness automatically from schema `source` and field `type`; do not require `required = true/false` annotations in the default schema for this MVP.
* Make the analysis prompt/schema hint more explicit about the fields needed downstream by Feishu.
* Validate rendered Feishu field values before creating the record.
* Report missing fields with the Feishu field name and source path so the user can fix the analysis output.
* Keep attachment upload behavior separate from required text/number/datetime validation.
* Keep the implementation open to future explicit `required = true/false` schema overrides, but do not include that override in the MVP unless it falls out naturally.
* Add tests for missing schema-backed fields so regressions are caught.

## Acceptance Criteria (Evolving)

* [ ] If a required schema source such as `analyses.breakdown.hook` is missing, Feishu emit fails before `record-batch-create`.
* [ ] If an optional metadata source such as `meta.share` is missing, Feishu emit can still create the row with an empty value.
* [ ] The error message lists the missing Feishu column name and source path.
* [ ] Required attachment fields are not treated the same as analysis text fields; existing best-effort upload behavior remains compatible.
* [ ] `vtf analyze` output gives the agent field-level guidance for the relevant `analyses.<kind>.*` paths required by the Feishu schema.
* [ ] Unit tests cover validation success and failure paths.

## Definition of Done

* Tests added or updated where appropriate.
* Lint and typecheck pass.
* Documentation or notes updated if behavior changes.
* Rollout and rollback considered if risk is non-trivial.

## Out of Scope

* Live remote Feishu table introspection during every emit.
* Changing the actual Base schema design unless implementation discovers it is internally inconsistent.
* Fully automating LLM calls; current vtf contract still lets the agent fill `result` fields.

## Technical Notes

* Session initialized via `trellis-start`.
* Planning workflow follows `.agents/skills/trellis-brainstorm/SKILL.md`.
* Relevant files inspected:
  * `src/vtf/pipeline/analyze.py`
  * `src/vtf/pipeline/assemble.py`
  * `src/vtf/sinks/feishu.py`
  * `src/vtf/sinks/schema.py`
  * `vtf/assets/schemas/baokuan.toml`
  * `src/vtf/prompts/{summary,breakdown,rewrite}.md`
  * `vtf/SKILL.md`
  * `tests/test_analyze.py`
  * `tests/test_assemble.py`
  * `tests/test_sink_feishu.py`
* `src/vtf/commands/init.py` strips schema entries down to `{"name", "type"}` before calling lark-cli, so adding local-only validation keys to the schema will not affect table creation.

## Decision (ADR-lite)

**Context**: The same TOML schema already defines Feishu field names and source paths, but validation currently happens too late and treats missing values as empty strings.

**Decision**: Use schema-backed tiered validation with automatic requiredness inference. Analysis-derived fields should block emit when missing; platform metadata can be empty when upstream platforms do not provide it; attachments stay best-effort.

**Consequences**: This prevents incomplete analysis records from being written while preserving tolerance for unstable upstream metadata and large/missing attachment files. The implementation should avoid hardcoding the default schema's Chinese field names so custom schemas remain usable.

## Technical Approach

* Add a small schema-validation layer near `vtf.sinks.schema` or `vtf.sinks.feishu` that can render field values and classify missing required fields.
* Treat rendered values as missing when they are `None`, empty string, or empty list after transformation for required analysis-derived fields.
* In `Feishu.emit`, validate required schema-backed values before calling `record-batch-create`; raise `UserError` with the missing Feishu field names and source paths.
* Enhance `vtf analyze` schema guidance by deriving required downstream paths for the current kind from the configured Feishu schema when `output.sink = "feishu"` or a Feishu schema is configured.
* Preserve existing `vtf init feishu` behavior because table creation only needs `name` and `type`.

## Implementation Plan

* PR1: Add schema requiredness inference and field validation helpers with focused unit tests.
* PR2: Wire validation into `Feishu.emit` before remote writes and update tests for strict analysis fields versus lenient metadata fields.
* PR3: Improve `vtf analyze` field-level guidance and update docs/tests for the new contract.
