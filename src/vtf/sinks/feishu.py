from __future__ import annotations

import json
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from vtf.errors import EnvironmentError as VtfEnvError
from vtf.errors import RemoteError, UserError
from vtf.sinks.base import EmitOutcome
from vtf.sinks.schema import render_field


class Feishu:
    name = "feishu"

    def available(self, cfg: Any) -> tuple[bool, str]:
        f = cfg.sink.feishu
        if not f.base_token:
            return (False, "缺少 base_token; 请运行 vtf init feishu")
        if not f.table_id:
            return (False, "缺少 table_id; 请运行 vtf init feishu")
        if not f.schema:
            return (False, "缺少 schema 文件路径; 请运行 vtf init feishu")
        if not shutil.which("lark-cli"):
            return (False, "lark-cli 未找到; 参考 README 安装 lark-cli")
        return (True, "")

    def emit(self, result: dict[str, Any], cfg: Any) -> EmitOutcome:
        f = cfg.sink.feishu

        lark = shutil.which("lark-cli")
        if not lark:
            raise VtfEnvError("lark-cli 未找到; 参考 README 安装 lark-cli")

        schema_path = Path(f.schema).expanduser()
        if not schema_path.is_absolute():
            schema_path = Path.cwd() / schema_path
        if not schema_path.exists():
            raise UserError(f"schema 文件不存在: {schema_path}")

        schema = tomllib.loads(schema_path.read_text("utf-8"))
        fields_def = schema.get("fields", [])
        if not fields_def:
            raise UserError(f"schema 文件无 fields 定义: {schema_path}")

        names: list[str] = []
        row: list[Any] = []
        for fdef in fields_def:
            name = fdef.get("name", "")
            source = fdef.get("source", "")
            if not name or not source:
                continue
            value = render_field(result, source)
            names.append(name)
            row.append(value if value is not None else "")

        payload = {"fields": names, "rows": [row]}
        cmd = [
            lark,
            "base",
            "+record-batch-create",
            "--base-token",
            f.base_token,
            "--table-id",
            f.table_id,
            "--json",
            json.dumps(payload, ensure_ascii=False),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            raise RemoteError(
                f"lark-cli 写入失败({proc.returncode}): {proc.stderr.strip()[:300]}"
            )

        try:
            resp = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return EmitOutcome(sink="feishu", reason=proc.stdout.strip()[:300])

        if not resp.get("ok"):
            err = resp.get("error") or {}
            msg = err.get("message") or proc.stdout[:300]
            raise RemoteError(f"飞书 API 返回失败: {msg}")

        record_id = ""
        data = resp.get("data") or {}
        records = data.get("records") or []
        if records:
            record_id = records[0].get("record_id", "")
        return EmitOutcome(sink="feishu", reason=f"已写入飞书 (record_id: {record_id})")
