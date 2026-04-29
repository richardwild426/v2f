# Codex 修复审查 — 待办问题

审查对象：Codex 在 `docs/claude-code-remediation.md` 基础上所做的两轮修复
第二审查日期：2026-04-29

## 第一轮审查问题 — 全部已修复

| # | 问题 | 状态 |
|---|------|------|
| 1 | `run.py` --skip 硬错误 | ✅ --skip flag 已完全移除，CLI 返回 "No such option" |
| 2 | feishu.emit 缺 thumbnail 校验 | ✅ 新增 `raise UserError("thumbnail missing")` + 测试 |
| 3 | thumbnail 双重校验冗余 | ✅ markdown 改为 degraded=true + 占位文本；assemble 保留权威校验 |
| 4 | force-include 语义错误 | ✅ 恢复为 `shared-data` |
| 5 | schema_config_dir 泄漏 | ✅ 改为私有属性 `_vtf_schema_config_dir`，通过 getattr/setattr/delattr 管理 |
| 6 | resolve_schema_path 过度 fallback | ✅ 仅保留 config_dir + package_root 两级 |
| 7 | test_config 耦合内部字段 | ✅ 测试不再直接访问内部属性 |

## 当前状态

所有门禁通过：
- `uv run ruff check src tests` — All checks passed
- `uv run mypy` — Success
- `uv run pytest` — 73 passed
- `uvx --from skills-ref agentskills validate ./vtf` — Valid skill
- `uv build` — skill 文件 + prompts 均在 wheel 中

## 无遗留问题
