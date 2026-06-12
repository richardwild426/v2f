# Feishu Schema Contract

> Executable contracts for vtf Feishu schema mapping, analysis guidance, and emit-time validation.

---

## Scenario: Schema-backed Feishu field completeness

### 1. Scope / Trigger

- Trigger: Changes that touch `vtf analyze`, `vtf emit`, Feishu schema files, or schema rendering helpers.
- Reason: The same TOML schema drives downstream LLM result expectations and Feishu Base record creation. Missing validation can silently create incomplete Base rows.

### 2. Signatures

- `vtf analyze --kind {summary,breakdown,rewrite} --meta meta.json < lines.json`
- `vtf emit < result.json`
- `resolve_feishu_schema_path(cfg, raw=None) -> Path`
- `load_schema_fields(schema_path: Path) -> list[dict[str, Any]]`
- `required_analysis_fields(fields_def, kind) -> list[RequiredAnalysisField]`
- `missing_required_fields(data, fields_def) -> list[MissingField]`

### 3. Contracts

- Schema fields use TOML entries:

```toml
[[fields]]
name = "摘要"
type = "text"
source = "analyses.summary.text"
```

- `source` may include one transformer after `|`, such as `analyses.summary.tags | tags_hashtag`.
- Requiredness is inferred, not manually annotated:
  - `analyses.*` + non-`attachment` => required.
  - `meta.*` => optional, except hard requirements enforced elsewhere such as `meta.thumbnail`.
  - `type = "attachment"` => best-effort, never blocks main record creation.
- `vtf analyze` output includes `required_result_fields` for the current kind when the configured schema resolves:

```json
{
  "kind": "summary",
  "schema_hint": "expected: {text, points[], tags[]}; required for Feishu: text, tags",
  "required_result_fields": [
    {
      "field": "摘要",
      "source": "analyses.summary.text",
      "result_path": "text"
    }
  ],
  "result": null
}
```

### 4. Validation & Error Matrix

| Condition | Behavior |
|---|---|
| Schema path does not exist at emit time | Raise `UserError("schema 文件不存在: ...")` |
| Schema has no `fields` | Raise `UserError("schema 文件无 fields 定义: ...")` |
| Required `analyses.*` field renders as `None`, empty string, empty list, or empty dict | Raise `UserError("缺少飞书必填字段内容，已停止写入: 字段名(source)")` before `record-batch-create` |
| Optional `meta.*` field is missing | Emit empty string for that cell |
| Attachment source is missing, empty, oversized, or upload fails | Keep main record; report attachment skip/failure in outcome reason |

### 5. Good / Base / Bad Cases

- Good: `analyses.summary.text` and `analyses.summary.tags` are present; `vtf analyze` advertises both paths and `vtf emit` writes the row.
- Base: `meta.share` is absent from platform metadata; emit writes an empty cell and continues.
- Bad: `analyses.breakdown.hook` is absent; emit stops before the remote write and lists `开场钩子(analyses.breakdown.hook)`.

### 6. Tests Required

- Schema helper tests for requiredness inference.
- Regression test that missing required analysis fields block before `subprocess.run`.
- Regression test that missing optional metadata still writes an empty cell.
- Analyze test that `required_result_fields` only includes paths for the current kind.
- Config/init test that the default packaged schema resolves in both source-tree and installed shared-data layouts.

### 7. Wrong vs Correct

#### Wrong

```python
value = render_field(result, source)
row.append(value if value is not None else "")
```

This silently turns missing analysis output into empty Feishu cells.

#### Correct

```python
missing = missing_required_fields(result, fields_def)
if missing:
    details = ", ".join(f"{item.name}({item.source})" for item in missing)
    raise UserError(f"缺少飞书必填字段内容，已停止写入: {details}")
```

Validate schema-backed analysis content before any remote write.
