from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any, cast

from vtf.config import resolve_feishu_schema_path, resolve_lark_cli
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
        if f.identity not in ("bot", "user"):
            return (False, f"sink.feishu.identity 取值非法: {f.identity!r}; 仅支持 bot 或 user")
        if not resolve_lark_cli(cfg):
            return (False, "lark-cli 未找到; 参考 README 安装 lark-cli")
        return (True, "")

    def emit(self, result: dict[str, Any], cfg: Any) -> EmitOutcome:
        f = cfg.sink.feishu
        meta = result.get("meta", {})
        if not meta.get("thumbnail"):
            raise UserError("meta.thumbnail missing; feishu output must include cover URL")

        lark = resolve_lark_cli(cfg)
        if not lark:
            raise VtfEnvError("lark-cli 未找到; 参考 README 安装 lark-cli")

        schema_path = resolve_feishu_schema_path(cfg)
        if not schema_path.exists():
            raise UserError(f"schema 文件不存在: {schema_path}")

        schema = tomllib.loads(schema_path.read_text("utf-8"))
        fields_def = schema.get("fields", [])
        if not fields_def:
            raise UserError(f"schema 文件无 fields 定义: {schema_path}")

        names: list[str] = []
        row: list[Any] = []
        attachments: list[tuple[str, str]] = []  # [(field_name, file_path), ...]

        for fdef in fields_def:
            name = fdef.get("name", "")
            source = fdef.get("source", "")
            if not name or not source:
                continue
            ftype = fdef.get("type", "text")
            if ftype == "attachment":
                value = render_field(result, source)
                # 附件字段不进入 batch_create payload，单独走 upload-attachment
                if value:
                    attachments.append((name, str(value)))
                continue
            value = render_field(result, source)
            names.append(name)
            row.append(value if value is not None else "")

        record_id = self._batch_create(lark, f, names, row)

        attachment_msgs: list[str] = []
        for field_name, file_path_str in attachments:
            attachment_msgs.append(
                self._upload_attachment(lark, f, record_id, field_name, file_path_str)
            )

        reason = f"已写入飞书 (record_id: {record_id}, identity: {f.identity})"
        if attachment_msgs:
            reason += "; 附件: " + ", ".join(attachment_msgs)
        return EmitOutcome(sink="feishu", reason=reason)

    def _batch_create(
        self, lark: str, f: Any, names: list[str], row: list[Any]
    ) -> str:
        payload = {"fields": names, "rows": [row]}
        cmd = [
            lark,
            "base",
            "+record-batch-create",
            "--as",
            f.identity,
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
            raise RemoteError(
                f"lark-cli 输出非 JSON: {proc.stdout.strip()[:300]}"
            ) from None

        if not resp.get("ok"):
            err = resp.get("error") or {}
            msg = err.get("message") or err.get("msg") or proc.stdout[:300]
            code = err.get("code")
            hint = ""
            if code == 99991672 or "NoPermission" in str(msg) or "Forbidden" in str(msg):
                hint = (
                    f"\n  → 修复：identity={f.identity} 对该 base 没有写权限。"
                    "若 identity=bot，请把机器人加为 base 协作者并授予「可编辑」权限"
                    "（base 右上角「···」→「更多」→「添加文档应用」）；"
                    "若 identity=user，请确认登录用户对 base 有可编辑权限。"
                )
            elif (
                code == 1254045
                or "字段名不存在" in str(msg)
                or "field name not found" in str(msg).lower()
            ):
                hint = (
                    "\n  → 修复：飞书表格里缺少 schema 中定义的字段。"
                    "运行 `vtf init feishu` 自动补齐缺失字段；"
                    "若是首次启用，运行 `vtf init feishu` 会按 schema 建好整张表。"
                )
            raise RemoteError(f"飞书 API 返回失败 (code={code}): {msg}{hint}")

        data = resp.get("data") or {}
        records = data.get("records") or []
        if not records:
            raise RemoteError("飞书 API 未返回 record_id，无法继续上传附件")
        first: dict[str, Any] = cast(dict[str, Any], records[0])
        return cast(str, first.get("record_id", ""))

    # 飞书附件单文件上限 2GB；留 100MB 余量避免临界报错
    _ATTACHMENT_MAX_BYTES = 1900 * 1024 * 1024

    def _upload_attachment(
        self, lark: str, f: Any, record_id: str, field_name: str, file_path_str: str
    ) -> str:
        path = Path(file_path_str).expanduser()
        if not path.exists():
            return f"{field_name}=跳过(文件不存在: {path})"
        size = path.stat().st_size
        if size == 0:
            return f"{field_name}=跳过(空文件)"
        if size > self._ATTACHMENT_MAX_BYTES:
            mb = size // (1024 * 1024)
            return (
                f"{field_name}=跳过({mb}MB 超过 1900MB 上限；如需上传请压缩或截断后手动添加)"
            )

        cmd = [
            lark,
            "base",
            "+record-upload-attachment",
            "--as",
            f.identity,
            "--base-token",
            f.base_token,
            "--table-id",
            f.table_id,
            "--record-id",
            record_id,
            "--field-id",
            field_name,
            "--file",
            str(path),
        ]
        # 大文件可能耗时较久；timeout 给到 30 分钟
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0:
            return (
                f"{field_name}=失败({proc.returncode}: "
                f"{proc.stderr.strip()[:160]})"
            )
        try:
            resp = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return f"{field_name}=失败(非 JSON 响应)"
        if not resp.get("ok"):
            err = resp.get("error") or {}
            return f"{field_name}=失败({err.get('message') or err.get('msg') or 'unknown'})"
        mb = size // (1024 * 1024)
        return f"{field_name}=已上传({mb}MB)"
