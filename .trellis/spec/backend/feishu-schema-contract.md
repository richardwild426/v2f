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

---

## Scenario: Storyboard child table for per-shot breakdown

### 1. Scope / Trigger

- Trigger: Changes that touch the default Feishu schema, `vtf init feishu`, `vtf analyze --kind breakdown`, or `vtf emit` child-table writes.
- Reason: The Feishu Base model can include a master video table plus a child table for per-shot storyboard rows. This is a cross-layer contract: TOML schema -> prompt guidance -> config -> Base table creation -> record write payloads.

### 2. Signatures

- `load_storyboard_schema(schema_path: Path) -> StoryboardSchema | None`
- `storyboard_required_analysis_field(storyboard, kind) -> RequiredAnalysisField | None`
- `vtf init feishu [--schema path] [--recreate]`
- `vtf emit < result.json`
- Config key: `sink.feishu.storyboard_table_id`
- Env key: `VTF_SINK_FEISHU_STORYBOARD_TABLE_ID`

### 3. Contracts

- A schema may define one optional child table:

```toml
[storyboard]
table_name = "分镜明细"
rows_source = "analyses.breakdown.shots"
link_field = "所属视频"
master_link_field = "脚本拆解"

[[storyboard.fields]]
name = "镜头"
type = "number"
source = "shot"
```

- If `[storyboard]` is absent, custom schemas keep the legacy single-table behavior.
- `vtf analyze --kind breakdown` must include `shots` in `required_result_fields` when `rows_source = "analyses.breakdown.shots"`.
- `vtf init feishu` must create or sync the child table, then create a child-table `link` field:

```json
{
  "name": "所属视频",
  "type": "link",
  "link_table": "tbl_main",
  "bidirectional": true,
  "bidirectional_link_field_name": "脚本拆解"
}
```

- `vtf emit` writes the main record first, then writes child rows to `storyboard_table_id`.
- Child row link values must use Feishu record link shape:

```json
[{ "id": "rec_main" }]
```

### 4. Validation & Error Matrix

| Condition | Behavior |
|---|---|
| `[storyboard]` exists but `rows_source` is empty | Raise `UserError("schema storyboard 缺少 rows_source: ...")` |
| `[storyboard]` exists but no usable fields are defined | Raise `UserError("schema storyboard ... fields ...")` |
| Schema has storyboard but config has no `storyboard_table_id` at emit time | Raise `UserError("缺少 storyboard_table_id; 请运行 vtf init feishu")` before remote writes |
| `rows_source` renders as missing, non-list, or empty list | Raise `UserError("缺少飞书子表分镜内容，已停止写入: 分镜明细(analyses.breakdown.shots)")` before remote writes |
| A storyboard row is not an object | Raise `UserError("飞书子表分镜第 N 行必须是对象: ...")` before remote writes |

### 5. Good / Base / Bad Cases

- Good: Default `baokuan.toml` creates a main table plus `分镜明细`; `vtf emit` writes the main record and child rows linked by `所属视频`.
- Base: A custom schema without `[storyboard]` creates and writes only the main table, preserving existing behavior.
- Bad: `analyses.breakdown.shots` is `[]`; emit stops before creating a partial main record.

### 6. Tests Required

- Schema tests for `load_storyboard_schema` and `storyboard_required_analysis_field`.
- Analyze test that breakdown advertises `shots` when storyboard is configured.
- Init test that default packaged schema creates child table and link field, and writes `storyboard_table_id`.
- Init test that existing bases can create a missing child table during sync.
- Emit test that child rows include `所属视频 = [{"id": main_record_id}]`.
- Emit regression tests for missing `storyboard_table_id` and empty `shots`.

### 7. Wrong vs Correct

#### Wrong

```toml
[[fields]]
name = "脚本拆解"
type = "link"
source = "analyses.breakdown.shots"
```

This tries to model per-shot data as one main-table field and cannot store one row per shot.

#### Correct

```toml
[storyboard]
rows_source = "analyses.breakdown.shots"
link_field = "所属视频"
master_link_field = "脚本拆解"
```

The child table owns the per-shot rows. Its link field points to the main table and lets Feishu generate the main-table reverse field.
