from __future__ import annotations

import os
import shutil
import tomllib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

DEFAULT_FEISHU_SCHEMA = "assets/schemas/baokuan.toml"


@dataclass
class OutputConfig:
    sink: str = "markdown"


@dataclass
class TranscribeConfig:
    funasr_python: str = ""
    asr_model: str = "paraformer-zh"
    vad_model: str = "fsmn-vad"
    punc_model: str = "ct-punc"
    batch_size_s: int = 300
    corrections_file: str = ""


@dataclass
class PlatformBilibili:
    cookies_from_browser: str = "chrome"
    cookies_file: str = ""


@dataclass
class PlatformYouTube:
    cookies_from_browser: str = ""
    cookies_file: str = ""


@dataclass
class PlatformConfig:
    bilibili: PlatformBilibili = field(default_factory=PlatformBilibili)
    youtube: PlatformYouTube = field(default_factory=PlatformYouTube)


@dataclass
class DownloadConfig:
    audio_format: str = "mp3"
    audio_quality: str = "0"
    retries: int = 3


@dataclass
class SinkMarkdown:
    template: str = ""


@dataclass
class SinkFeishu:
    base_token: str = ""
    table_id: str = ""
    schema: str = DEFAULT_FEISHU_SCHEMA
    lark_cli: str = "lark-cli"
    identity: str = "bot"


@dataclass
class SinkConfig:
    markdown: SinkMarkdown = field(default_factory=SinkMarkdown)
    feishu: SinkFeishu = field(default_factory=SinkFeishu)


@dataclass
class AnalyzePrompts:
    summary: str = ""
    breakdown: str = ""
    rewrite: str = ""


@dataclass
class AnalyzeConfig:
    prompts: AnalyzePrompts = field(default_factory=AnalyzePrompts)


@dataclass
class Config:
    output: OutputConfig = field(default_factory=OutputConfig)
    transcribe: TranscribeConfig = field(default_factory=TranscribeConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    sink: SinkConfig = field(default_factory=SinkConfig)
    analyze: AnalyzeConfig = field(default_factory=AnalyzeConfig)


def load_config(
    *,
    user_path: Path | None,
    project_path: Path | None,
    env: dict[str, str],
    overrides: dict[str, Any],
) -> Config:
    cfg = Config()
    if user_path and user_path.exists():
        user_data = _read_toml(user_path)
        _merge_dict(cfg, user_data)
        _set_schema_config_dir(cfg, user_data, user_path.parent)
    if project_path and project_path.exists():
        project_data = _read_toml(project_path)
        _merge_dict(cfg, project_data)
        _set_schema_config_dir(cfg, project_data, project_path.parent)
    _merge_env(cfg, env)
    if "VTF_SINK_FEISHU_SCHEMA" in env:
        _clear_schema_config_dir(cfg)
    _merge_dict(cfg, overrides)
    return cfg


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


def _merge_dict(target: Any, src: dict[str, Any]) -> None:
    for k, v in src.items():
        if not hasattr(target, k):
            continue
        cur = getattr(target, k)
        if is_dataclass(cur) and isinstance(v, dict):
            _merge_dict(cur, v)
        else:
            setattr(target, k, v)


_SCHEMA_CONFIG_DIR_ATTR = "_vtf_schema_config_dir"


def _set_schema_config_dir(cfg: Config, src: dict[str, Any], config_dir: Path) -> None:
    feishu = (src.get("sink") or {}).get("feishu") or {}
    raw_schema = feishu.get("schema")
    if isinstance(raw_schema, str) and raw_schema:
        p = Path(raw_schema).expanduser()
        if p.is_absolute():
            _clear_schema_config_dir(cfg)
        else:
            setattr(cfg.sink.feishu, _SCHEMA_CONFIG_DIR_ATTR, config_dir)


def _clear_schema_config_dir(cfg: Config) -> None:
    if hasattr(cfg.sink.feishu, _SCHEMA_CONFIG_DIR_ATTR):
        delattr(cfg.sink.feishu, _SCHEMA_CONFIG_DIR_ATTR)


def _schema_config_dir(cfg: Config) -> Path | None:
    value = getattr(cfg.sink.feishu, _SCHEMA_CONFIG_DIR_ATTR, None)
    return value if isinstance(value, Path) else None


def _merge_env(target: Any, env: dict[str, str], prefix: str = "VTF") -> None:
    if not is_dataclass(target):
        return
    for f in fields(target):
        full = f"{prefix}_{f.name.upper()}"
        cur = getattr(target, f.name)
        if is_dataclass(cur):
            _merge_env(cur, env, full)
        elif full in env:
            raw = env[full]
            setattr(target, f.name, _coerce(raw, type(cur)))
    # legacy aliases
    if prefix == "VTF":
        if "TABLE_TOKEN" in env and hasattr(target, "sink"):
            target.sink.feishu.base_token = env["TABLE_TOKEN"]
        if "TABLE_ID" in env and hasattr(target, "sink"):
            target.sink.feishu.table_id = env["TABLE_ID"]


def _coerce(raw: str, target_type: type) -> Any:
    if target_type is int:
        return int(raw)
    if target_type is bool:
        return raw.lower() in {"1", "true", "yes", "on"}
    return raw


def default_user_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / "vtf" / "config.toml"
    return Path.home() / ".config" / "vtf" / "config.toml"


def default_workdir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    if base:
        return Path(base) / "vtf"
    return Path.home() / ".cache" / "vtf"


def resolve_lark_cli(cfg: Config) -> str | None:
    """Return the lark-cli executable path from config, falling back to PATH lookup."""
    configured = cfg.sink.feishu.lark_cli
    if configured and "/" in configured:
        return configured
    if configured:
        resolved = shutil.which(configured)
        if resolved:
            return resolved
    return shutil.which("lark-cli")


def resolve_schema_path(raw: str, *, config_dir: Path | None = None) -> Path:
    """Resolve a schema path.

    Absolute paths and ~ paths are used as-is (after expanduser).
    Relative paths resolve from *config_dir* if given,
    otherwise from the vtf package directory (so shipped assets work).
    """
    p = Path(raw).expanduser()
    if p.is_absolute():
        return p

    candidates: list[Path] = []
    if config_dir is not None:
        candidates.append(config_dir / p)

    package_root = Path(__file__).parent
    candidates.extend(
        [
            package_root / p,
        ]
    )
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists():
            return resolved
    return (package_root / p).resolve()


def resolve_feishu_schema_path(cfg: Config, raw: str | None = None) -> Path:
    return resolve_schema_path(raw or cfg.sink.feishu.schema, config_dir=_schema_config_dir(cfg))
