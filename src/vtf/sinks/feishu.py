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
from vtf.sinks.schema import (
    StoryboardSchema,
    is_missing_value,
    is_required_field,
    load_schema_fields,
    load_storyboard_schema,
    missing_required_fields,
    render_field,
)


class _ScreenshotFeishuConfig:
    """轻量配置适配器，让 _batch_create / _upload_attachment 复用同一逻辑。"""

    def __init__(self, base_token: str, table_id: str, identity: str) -> None:
        self.base_token = base_token
        self.table_id = table_id
        self.identity = identity


class Feishu:
    name = "feishu"

    # 飞书附件单文件上限 2GB；留 100MB 余量避免临界报错
    _ATTACHMENT_MAX_BYTES = 1900 * 1024 * 1024

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
        schema_path = resolve_feishu_schema_path(cfg)
        if (
            schema_path.exists()
            and load_storyboard_schema(schema_path) is not None
            and not getattr(f, "storyboard_table_id", "")
        ):
            return (False, "缺少 storyboard_table_id; 请运行 vtf init feishu")
        if not resolve_lark_cli(cfg):
            return (False, "lark-cli 未找到; 参考 README 安装 lark-cli")
        return (True, "")

    def emit(self, result: dict[str, Any], cfg: Any) -> EmitOutcome:
        f = cfg.sink.feishu
        meta = result.get("meta", {})

        # 如果包含 screenshots 列表且配置了截图表，批量写入截图记录
        screenshots = meta.get("screenshots") or result.get("screenshots")
        if screenshots and isinstance(screenshots, list) and f.screenshot_table_id:
            return self.emit_screenshots(screenshots, meta, cfg)

        if not meta.get("thumbnail"):
            raise UserError("meta.thumbnail missing; feishu output must include cover URL")

        lark = resolve_lark_cli(cfg)
        if not lark:
            raise VtfEnvError("lark-cli 未找到; 参考 README 安装 lark-cli")

        schema_path = resolve_feishu_schema_path(cfg)
        if not schema_path.exists():
            raise UserError(f"schema 文件不存在: {schema_path}")

        fields_def = load_schema_fields(schema_path)
        storyboard = load_storyboard_schema(schema_path)
        missing = missing_required_fields(result, fields_def)
        if missing:
            details = ", ".join(f"{item.name}({item.source})" for item in missing)
            raise UserError(f"缺少飞书必填字段内容，已停止写入: {details}")
        storyboard_rows = self._render_storyboard_rows(result, f, storyboard)

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

        if storyboard is not None and storyboard_rows:
            self._batch_create_storyboard(lark, f, storyboard, record_id, storyboard_rows)

        attachment_msgs: list[str] = []
        for field_name, file_path_str in attachments:
            attachment_msgs.append(
                self._upload_attachment(lark, f, record_id, field_name, file_path_str)
            )

        reason = f"已写入飞书 (record_id: {record_id}, identity: {f.identity})"
        if attachment_msgs:
            reason += "; 附件: " + ", ".join(attachment_msgs)
        return EmitOutcome(sink="feishu", reason=reason)

    def emit_screenshots(
        self,
        screenshots: list[dict[str, Any]],
        meta: dict[str, Any],
        cfg: Any,
    ) -> EmitOutcome:
        """批量写入截图记录到飞书截图专用表。

        每张截图生成一条飞书记录，截图文件作为附件上传。

        Args:
            screenshots: 截图信息列表
            meta: 视频元信息（用于填充视频ID、标题等公共字段）
            cfg: 全局配置

        Returns:
            EmitOutcome 包含写入结果摘要
        """
        from vtf.config import resolve_feishu_screenshot_schema_path

        f = cfg.sink.feishu
        lark = resolve_lark_cli(cfg)
        if not lark:
            raise VtfEnvError("lark-cli 未找到; 参考 README 安装 lark-cli")

        schema_path = resolve_feishu_screenshot_schema_path(cfg)
        if not schema_path.exists():
            raise UserError(f"截图 schema 文件不存在: {schema_path}")

        schema = tomllib.loads(schema_path.read_text("utf-8"))
        fields_def = schema.get("fields", [])
        if not fields_def:
            raise UserError(f"截图 schema 文件无 fields 定义: {schema_path}")

        ok_count = 0
        fail_count = 0
        reasons: list[str] = []

        for screenshot in screenshots:
            # 构造单条截图的 result dict，使 render_field 能通过 "screenshots.xxx" 访问
            single_result: dict[str, Any] = {
                "meta": meta,
                "screenshots": screenshot,
            }

            names: list[str] = []
            row: list[Any] = []
            attachments: list[tuple[str, str]] = []

            for fdef in fields_def:
                name = fdef.get("name", "")
                source = fdef.get("source", "")
                if not name or not source:
                    continue
                ftype = fdef.get("type", "text")
                if ftype == "attachment":
                    value = render_field(single_result, source)
                    if value:
                        attachments.append((name, str(value)))
                    continue
                value = render_field(single_result, source)
                names.append(name)
                row.append(value if value is not None else "")

            try:
                # 截图表复用同一个 base_token，但使用独立的 screenshot_table_id
                record_id = self._batch_create(
                    lark,
                    _ScreenshotFeishuConfig(f.base_token, f.screenshot_table_id, f.identity),
                    names,
                    row,
                )
                for field_name, file_path_str in attachments:
                    msg = self._upload_attachment(
                        lark,
                        _ScreenshotFeishuConfig(f.base_token, f.screenshot_table_id, f.identity),
                        record_id,
                        field_name,
                        file_path_str,
                    )
                    reasons.append(msg)

                ok_count += 1
            except (RemoteError, UserError) as e:
                fail_count += 1
                reasons.append(f"截图 {screenshot.get('timestamp_str', '?')} 失败: {e}")

        summary = f"截图写入飞书: {ok_count} 成功"
        if fail_count:
            summary += f", {fail_count} 失败"
        if reasons:
            summary += "; " + "; ".join(reasons[:5])
        return EmitOutcome(sink="feishu", reason=summary)

    def _batch_create(
        self, lark: str, f: Any, names: list[str], row: list[Any]
    ) -> str:
        record_ids = self._batch_create_rows(lark, f, f.table_id, names, [row])
        if not record_ids:
            raise RemoteError("飞书 API 未返回 record_id，无法继续上传附件")
        return record_ids[0]

    def _batch_create_rows(
        self,
        lark: str,
        f: Any,
        table_id: str,
        names: list[str],
        rows: list[list[Any]],
    ) -> list[str]:
        payload = {"fields": names, "rows": rows}
        cmd = [
            lark,
            "base",
            "+record-batch-create",
            "--as",
            f.identity,
            "--base-token",
            f.base_token,
            "--table-id",
            table_id,
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
        if records:
            return [
                str(cast(dict[str, Any], item).get("record_id", ""))
                for item in records
                if cast(dict[str, Any], item).get("record_id")
            ]
        return [str(item) for item in data.get("record_id_list", []) if item]

    def _render_storyboard_rows(
        self,
        result: dict[str, Any],
        f: Any,
        storyboard: StoryboardSchema | None,
    ) -> list[list[Any]]:
        if storyboard is None:
            return []
        if not getattr(f, "storyboard_table_id", ""):
            raise UserError("缺少 storyboard_table_id; 请运行 vtf init feishu")

        raw_rows = render_field(result, storyboard.rows_source)
        if not isinstance(raw_rows, list) or not raw_rows:
            raise UserError(
                "缺少飞书子表分镜内容，已停止写入: "
                f"{storyboard.table_name}({storyboard.rows_source})"
            )

        rows: list[list[Any]] = []
        missing: list[str] = []
        for index, raw_row in enumerate(raw_rows, start=1):
            if not isinstance(raw_row, dict):
                raise UserError(
                    f"飞书子表分镜第 {index} 行必须是对象: {storyboard.rows_source}"
                )
            row: list[Any] = []
            for field in storyboard.fields:
                source = str(field.get("source", ""))
                value = render_field(raw_row, source)
                if is_required_field(field) and is_missing_value(value):
                    missing.append(f"第{index}行 {field.get('name', '')}({source})")
                row.append(value if value is not None else "")
            rows.append(row)
        if missing:
            raise UserError(
                "缺少飞书子表分镜必填字段内容，已停止写入: " + "; ".join(missing)
            )
        return rows

    def _batch_create_storyboard(
        self,
        lark: str,
        f: Any,
        storyboard: StoryboardSchema,
        record_id: str,
        rendered_rows: list[list[Any]],
    ) -> None:
        names = [storyboard.link_field, *[str(field["name"]) for field in storyboard.fields]]
        rows = [[[{"id": record_id}], *row] for row in rendered_rows]
        for start in range(0, len(rows), 200):
            self._batch_create_rows(
                lark,
                f,
                f.storyboard_table_id,
                names,
                rows[start : start + 200],
            )

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
