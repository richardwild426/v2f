from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any


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
    schema: str = ""
    lark_cli: str = "lark-cli"


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
        _merge_dict(cfg, _read_toml(user_path))
    if project_path and project_path.exists():
        _merge_dict(cfg, _read_toml(project_path))
    _merge_env(cfg, env)
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
    if prefix == "VTF" and "TABLE_TOKEN" in env:
        target.sink.feishu.base_token = env["TABLE_TOKEN"]  # type: ignore[attr-defined]
    if prefix == "VTF" and "TABLE_ID" in env:
        target.sink.feishu.table_id = env["TABLE_ID"]  # type: ignore[attr-defined]


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