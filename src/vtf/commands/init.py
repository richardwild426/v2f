from __future__ import annotations

import json
import subprocess
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import click

from vtf._ctx import get_config, get_logger
from vtf.config import (
    DEFAULT_FEISHU_SCHEMA,
    default_user_path,
    resolve_feishu_schema_path,
    resolve_lark_cli,
)
from vtf.errors import EnvironmentError as VtfEnvError
from vtf.errors import RemoteError, UserError, VtfError
from vtf.sinks.schema import StoryboardSchema, load_schema_fields, load_storyboard_schema


@click.group(name="init", help="一次性配置向导（目前支持 feishu）")
def cmd() -> None:
    pass


# ----- feishu 子命令 -----------------------------------------------------------


@cmd.command(name="feishu", help="自动创建/同步飞书 base+table，按 schema 建好所有字段")
@click.option("--folder", "folder_token", default="",
              help="云空间文件夹 token；不传则放在云空间根目录")
@click.option("--name", "base_name", default="",
              help="新 base 名，默认 'vtf 视频分析 - YYYY-MM-DD'")
@click.option("--table-name", default="分析记录", help="新 table 名（默认: 分析记录）")
@click.option("--schema", "schema_path", default="",
              help="schema TOML 路径，覆盖 cfg.sink.feishu.schema")
@click.option(
    "--write-config/--no-write-config",
    default=True,
    help="拿到 base_token / table_id 后是否回写 ~/.config/vtf/config.toml（默认是）",
)
@click.option(
    "--recreate",
    is_flag=True,
    help="忽略已配置的 base_token，强制重建一份新 base+table",
)
@click.pass_context
def feishu_cmd(
    ctx: click.Context,
    folder_token: str,
    base_name: str,
    table_name: str,
    schema_path: str,
    write_config: bool,
    recreate: bool,
) -> None:
    log = get_logger(ctx)
    cfg = get_config(ctx)
    f = cfg.sink.feishu

    try:
        raw_schema = schema_path or f.schema or DEFAULT_FEISHU_SCHEMA
        lark = _require_lark_cli_bound(cfg)
        schema_file = resolve_feishu_schema_path(cfg, raw_schema if schema_path else None)
        if not schema_file.exists():
            raise UserError(f"schema 文件不存在: {schema_file}")
        fields_def, storyboard = _load_schema_tables(schema_file)

        if f.base_token and not recreate:
            _sync_existing_table(
                lark,
                f,
                fields_def,
                storyboard=storyboard,
                schema_file=schema_file,
                write_config=write_config,
            )
            return

        # 没 base_token，或 --recreate：建 base + table + 全部字段
        _create_new_base_and_table(
            lark=lark,
            f=f,
            base_name=base_name or _default_base_name(),
            table_name=table_name,
            folder_token=folder_token,
            fields_def=fields_def,
            storyboard=storyboard,
            schema_file=schema_file,
            write_config=write_config,
        )
    except VtfError as e:
        log.error(str(e), step="init-feishu")
        raise SystemExit(e.exit_code) from e


# ----- 实现 ---------------------------------------------------------------------


def _default_base_name() -> str:
    return f"vtf 视频分析 - {datetime.now().strftime('%Y-%m-%d')}"


def _require_lark_cli_bound(cfg: Any) -> str:
    lark = resolve_lark_cli(cfg)
    if not lark:
        raise VtfEnvError(
            "lark-cli 未找到。请安装 lark-cli 并先跑 `lark-cli config init --new` 绑定飞书应用"
        )
    proc = subprocess.run(
        [lark, "config", "show"], capture_output=True, text=True, timeout=5
    )
    if proc.returncode != 0:
        raise VtfEnvError(
            f"lark-cli config show 失败: {proc.stderr.strip()[:200]}"
            "；先跑 `lark-cli config init --new`"
        )
    try:
        info = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise VtfEnvError("lark-cli config show 输出非 JSON，无法判断绑定状态") from None
    app_id = info.get("appId", "")
    if not app_id:
        raise VtfEnvError(
            "lark-cli 尚未绑定飞书应用。请先运行：lark-cli config init --new"
        )
    if cfg.sink.feishu.identity == "user" and not info.get("users"):
        raise VtfEnvError(
            "identity=user 但 lark-cli 尚未 OAuth 登录。请运行：lark-cli auth login"
        )
    return lark


def _load_schema_tables(
    schema_file: Path,
) -> tuple[list[dict[str, Any]], StoryboardSchema | None]:
    items = load_schema_fields(schema_file)
    out: list[dict[str, Any]] = []
    for fdef in items:
        name = fdef.get("name", "")
        ftype = fdef.get("type", "text")
        if not name:
            continue
        out.append({"name": name, "type": ftype})
    if not out:
        raise UserError(f"schema 解析后字段列表为空: {schema_file}")
    return out, load_storyboard_schema(schema_file)


def _create_new_base_and_table(
    *,
    lark: str,
    f: Any,
    base_name: str,
    table_name: str,
    folder_token: str,
    fields_def: list[dict[str, Any]],
    storyboard: StoryboardSchema | None,
    schema_file: Path,
    write_config: bool,
) -> None:
    click.echo(f"正在创建 base「{base_name}」...")
    base_resp = _run_lark(
        lark,
        [
            "base",
            "+base-create",
            "--as",
            f.identity,
            "--name",
            base_name,
            *(["--folder-token", folder_token] if folder_token else []),
        ],
        timeout=30,
    )
    base = (base_resp.get("data") or {}).get("base") or {}
    base_token = base.get("token") or base.get("app_token") or ""
    base_url = base.get("url") or ""
    if not base_token:
        raise RemoteError(f"建 base 成功但未返回 token: {base_resp}")
    click.echo(f"  ✅ base_token = {base_token}")
    if base_url:
        click.echo(f"     URL: {base_url}")

    click.echo(f"正在建 table「{table_name}」并一次性建 {len(fields_def)} 个字段...")
    fields_payload = json.dumps(fields_def, ensure_ascii=False)
    table_resp = _run_lark(
        lark,
        [
            "base",
            "+table-create",
            "--as",
            f.identity,
            "--base-token",
            base_token,
            "--name",
            table_name,
            "--fields",
            fields_payload,
        ],
        timeout=60,
    )
    table_id = ((table_resp.get("data") or {}).get("table") or {}).get("table_id", "")
    if not table_id:
        raise RemoteError(f"建 table 成功但未返回 table_id: {table_resp}")
    click.echo(f"  ✅ table_id = {table_id}")

    storyboard_table_id = ""
    if storyboard is not None:
        storyboard_table_id = _create_storyboard_table(
            lark=lark,
            f=f,
            base_token=base_token,
            main_table_id=table_id,
            storyboard=storyboard,
        )

    if write_config:
        _patch_user_config(
            base_token=base_token,
            table_id=table_id,
            schema=str(schema_file),
            storyboard_table_id=storyboard_table_id or None,
        )
        click.echo(f"  ✅ 已写入 {default_user_path()}")
    else:
        click.echo("  ⚠️  --no-write-config: 请手动把以下配置加到 ~/.config/vtf/config.toml")
        click.echo("       [sink.feishu]")
        click.echo(f'       base_token = "{base_token}"')
        click.echo(f'       table_id = "{table_id}"')
        if storyboard_table_id:
            click.echo(f'       storyboard_table_id = "{storyboard_table_id}"')
        click.echo(f'       schema = "{schema_file}"')

    click.echo("")
    click.echo("⚠️  下一步（必须人工完成，飞书未开放该 OpenAPI）：")
    click.echo("    把机器人加为 base 协作者并授予「可编辑」权限")
    click.echo("      浏览器打开 base → 「···」→「更多」→「添加文档应用」→ 搜机器人名 → 可编辑")
    if base_url:
        click.echo(f"    base URL: {base_url}")
    click.echo("")
    click.echo("完成后，跑 `vtf doctor` 验证；之后即可 sink=feishu 写入。")


def _create_storyboard_table(
    *,
    lark: str,
    f: Any,
    base_token: str,
    main_table_id: str,
    storyboard: StoryboardSchema,
) -> str:
    fields_def = _storyboard_field_defs(storyboard)
    click.echo(
        f"正在建子表「{storyboard.table_name}」并一次性建 {len(fields_def)} 个字段..."
    )
    table_resp = _run_lark(
        lark,
        [
            "base",
            "+table-create",
            "--as",
            f.identity,
            "--base-token",
            base_token,
            "--name",
            storyboard.table_name,
            "--fields",
            json.dumps(fields_def, ensure_ascii=False),
        ],
        timeout=60,
    )
    table_id = ((table_resp.get("data") or {}).get("table") or {}).get("table_id", "")
    if not table_id:
        raise RemoteError(f"建子表成功但未返回 table_id: {table_resp}")
    click.echo(f"  ✅ storyboard_table_id = {table_id}")
    _create_storyboard_link_field(
        lark=lark,
        f=f,
        base_token=base_token,
        storyboard_table_id=table_id,
        main_table_id=main_table_id,
        storyboard=storyboard,
    )
    return str(table_id)


def _sync_existing_table(
    lark: str,
    f: Any,
    fields_def: list[dict[str, Any]],
    *,
    storyboard: StoryboardSchema | None,
    schema_file: Path,
    write_config: bool,
) -> None:
    if not f.table_id:
        raise UserError(
            "已配置 base_token 但未配 table_id；无法定位目标表。请补全配置或加 --recreate 重建"
        )
    click.echo(f"检测到已配置 base_token={f.base_token}，进入字段同步模式...")
    existing = _list_existing_fields(lark, f)
    existing_names = {item.get("name", "") for item in existing}
    name_to_type = {item.get("name", ""): item.get("type", "") for item in existing}

    missing: list[dict[str, Any]] = []
    type_mismatch: list[tuple[str, str, str]] = []  # (name, schema_type, existing_type)

    for fdef in fields_def:
        name = fdef["name"]
        if name not in existing_names:
            missing.append(fdef)
            continue
        # 飞书 +field-list 返回的 type 可能是数字或字符串，宽松对比
        existing_type = str(name_to_type.get(name, ""))
        if existing_type and existing_type != fdef["type"]:
            type_mismatch.append((name, fdef["type"], existing_type))

    for fdef in missing:
        click.echo(f"  + 创建字段「{fdef['name']}」(type={fdef['type']})...")
        _create_field(lark, f, fdef["name"], fdef["type"])

    if missing:
        click.echo(f"✅ 已补齐 {len(missing)} 个字段：{', '.join(m['name'] for m in missing)}")
        click.echo("   注意：新字段追加在表末尾，可在飞书 UI 里手动拖动调整顺序")
    else:
        click.echo("✅ 所有字段已存在，无需补齐")

    if type_mismatch:
        click.echo("")
        click.echo("⚠️  以下字段名匹配但类型不一致（vtf 不会自动改类型，避免丢数据）：")
        for name, schema_type, existing_type in type_mismatch:
            click.echo(f"    - {name}: schema={schema_type}, 飞书表格={existing_type}")
        click.echo("    如需对齐，请在飞书表格里手动改字段类型，或手动 +field-update")

    if storyboard is not None:
        storyboard_table_id = _sync_storyboard_table(
            lark=lark,
            f=f,
            storyboard=storyboard,
        )
        if write_config and storyboard_table_id != getattr(f, "storyboard_table_id", ""):
            _patch_user_config(
                base_token=f.base_token,
                table_id=f.table_id,
                schema=str(schema_file),
                storyboard_table_id=storyboard_table_id,
            )
            click.echo(f"  ✅ 已写入 storyboard_table_id 到 {default_user_path()}")


def _sync_storyboard_table(
    *,
    lark: str,
    f: Any,
    storyboard: StoryboardSchema,
) -> str:
    table_id = getattr(f, "storyboard_table_id", "") or _find_table_id_by_name(
        lark, f, storyboard.table_name
    )
    if not table_id:
        click.echo(f"未找到子表「{storyboard.table_name}」，开始创建...")
        return _create_storyboard_table(
            lark=lark,
            f=f,
            base_token=f.base_token,
            main_table_id=f.table_id,
            storyboard=storyboard,
        )

    click.echo(
        f"检测到 storyboard_table_id={table_id}，同步子表「{storyboard.table_name}」字段..."
    )
    existing = _list_existing_fields(lark, f, table_id=table_id)
    existing_names = {item.get("name", "") for item in existing}

    for fdef in _storyboard_field_defs(storyboard):
        name = fdef["name"]
        if name in existing_names:
            continue
        click.echo(f"  + 创建子表字段「{name}」(type={fdef['type']})...")
        _create_field(lark, f, name, fdef["type"], table_id=table_id)

    if storyboard.link_field not in existing_names:
        _create_storyboard_link_field(
            lark=lark,
            f=f,
            base_token=f.base_token,
            storyboard_table_id=table_id,
            main_table_id=f.table_id,
            storyboard=storyboard,
        )
    else:
        click.echo(f"  ✅ 子表关联字段「{storyboard.link_field}」已存在")
    return str(table_id)


def _storyboard_field_defs(storyboard: StoryboardSchema) -> list[dict[str, Any]]:
    return [
        {"name": str(field["name"]), "type": str(field.get("type", "text"))}
        for field in storyboard.fields
    ]


def _create_storyboard_link_field(
    *,
    lark: str,
    f: Any,
    base_token: str,
    storyboard_table_id: str,
    main_table_id: str,
    storyboard: StoryboardSchema,
) -> None:
    payload = {
        "name": storyboard.link_field,
        "type": "link",
        "link_table": main_table_id,
        "bidirectional": True,
        "bidirectional_link_field_name": storyboard.master_link_field,
    }
    click.echo(
        f"  + 创建子表关联字段「{storyboard.link_field}」"
        f"（主表反向字段「{storyboard.master_link_field}」）..."
    )
    _create_field_payload(
        lark,
        f,
        payload,
        base_token=base_token,
        table_id=storyboard_table_id,
    )


# ----- lark-cli 调用辅助 --------------------------------------------------------


def _run_lark(lark: str, args: list[str], *, timeout: int) -> dict[str, Any]:
    cmd = [lark, *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RemoteError(
            f"lark-cli {' '.join(args[:2])} 失败({proc.returncode}): "
            f"{proc.stderr.strip()[:300]}"
        )
    try:
        resp = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RemoteError(
            f"lark-cli {' '.join(args[:2])} 输出非 JSON: {proc.stdout.strip()[:300]}"
        ) from None
    if not resp.get("ok"):
        err = resp.get("error") or {}
        msg = err.get("message") or err.get("msg") or "unknown"
        code = err.get("code")
        hint = ""
        if code == 99991672 or "NoPermission" in str(msg):
            hint = (
                "\n  → 修复：机器人身份对该 base 没有权限。"
                "把机器人加为 base 协作者并授予「可管理」权限（建/改字段需要可管理）"
            )
        raise RemoteError(
            f"飞书 API 失败 (code={code}): {msg}{hint}"
        )
    return cast(dict[str, Any], resp)


def _list_existing_tables(lark: str, f: Any) -> list[dict[str, Any]]:
    resp = _run_lark(
        lark,
        [
            "base",
            "+table-list",
            "--as",
            f.identity,
            "--base-token",
            f.base_token,
            "--limit",
            "100",
        ],
        timeout=30,
    )
    data = resp.get("data") or {}
    items = data.get("items") or data.get("tables") or []
    out: list[dict[str, Any]] = []
    for it in items:
        out.append(
            {
                "table_id": it.get("table_id") or it.get("id", ""),
                "table_name": it.get("table_name") or it.get("name", ""),
            }
        )
    return out


def _find_table_id_by_name(lark: str, f: Any, table_name: str) -> str:
    for table in _list_existing_tables(lark, f):
        if table.get("table_name") == table_name:
            return str(table.get("table_id") or "")
    return ""


def _list_existing_fields(
    lark: str, f: Any, *, table_id: str | None = None
) -> list[dict[str, Any]]:
    resp = _run_lark(
        lark,
        [
            "base",
            "+field-list",
            "--as",
            f.identity,
            "--base-token",
            f.base_token,
            "--table-id",
            table_id or f.table_id,
            "--limit",
            "100",
        ],
        timeout=30,
    )
    data = resp.get("data") or {}
    items = data.get("items") or data.get("fields") or []
    out: list[dict[str, Any]] = []
    for it in items:
        out.append(
            {
                "name": it.get("field_name") or it.get("name", ""),
                "type": it.get("type") or it.get("ui_type", ""),
            }
        )
    return out


def _create_field(
    lark: str,
    f: Any,
    name: str,
    ftype: str,
    *,
    table_id: str | None = None,
) -> None:
    payload = {"name": name, "type": ftype}
    _create_field_payload(lark, f, payload, table_id=table_id)


def _create_field_payload(
    lark: str,
    f: Any,
    payload: dict[str, Any],
    *,
    base_token: str | None = None,
    table_id: str | None = None,
) -> None:
    _run_lark(
        lark,
        [
            "base",
            "+field-create",
            "--as",
            f.identity,
            "--base-token",
            base_token or f.base_token,
            "--table-id",
            table_id or f.table_id,
            "--json",
            json.dumps(payload, ensure_ascii=False),
        ],
        timeout=30,
    )


# ----- 配置文件回写（仅 patch [sink.feishu]，保留其它段；不引入额外依赖） ------------


def _patch_user_config(
    *,
    base_token: str,
    table_id: str,
    schema: str,
    storyboard_table_id: str | None = None,
) -> None:
    path = default_user_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, Any] = {}
    if path.exists():
        existing = tomllib.loads(path.read_text("utf-8"))

    # 覆盖 [sink.feishu] 三个键
    sink = existing.setdefault("sink", {})
    feishu = sink.setdefault("feishu", {})
    feishu["base_token"] = base_token
    feishu["table_id"] = table_id
    if storyboard_table_id is not None:
        feishu["storyboard_table_id"] = storyboard_table_id
    feishu["schema"] = schema
    # 同时切到 feishu sink，免得用户还要手动改 [output]
    output = existing.setdefault("output", {})
    output["sink"] = "feishu"

    path.write_text(_dump_toml(existing), encoding="utf-8")


def _dump_toml(data: dict[str, Any]) -> str:
    """极简 TOML 序列化：仅支持嵌套 dict + str/int/bool/float 标量。够 vtf config 用。"""
    lines: list[str] = []
    # 顶层标量先写
    scalars = {k: v for k, v in data.items() if not isinstance(v, dict)}
    for k, v in scalars.items():
        lines.append(f"{k} = {_toml_value(v)}")
    if scalars:
        lines.append("")
    # 嵌套段（一层和两层；vtf config 只用到这两级）
    for k, v in data.items():
        if not isinstance(v, dict):
            continue
        _dump_section(lines, k, v)
    return "\n".join(lines).rstrip() + "\n"


def _dump_section(lines: list[str], header: str, section: dict[str, Any]) -> None:
    scalars = {k: v for k, v in section.items() if not isinstance(v, dict)}
    sub = {k: v for k, v in section.items() if isinstance(v, dict)}
    if scalars:
        lines.append(f"[{header}]")
        for k, v in scalars.items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    for k, v in sub.items():
        _dump_section(lines, f"{header}.{k}", v)


def _toml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        # 转义双引号和反斜杠
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    raise UserError(f"不支持的 TOML 值类型: {type(v).__name__}")
