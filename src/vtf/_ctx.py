from __future__ import annotations

import os
from pathlib import Path

import click

from vtf.config import Config, default_user_path, default_workdir, load_config
from vtf.logging import Logger


def get_config(ctx: click.Context) -> Config:
    obj = ctx.obj or {}
    user = obj.get("config_path") or default_user_path()
    project = Path("vtf.toml") if Path("vtf.toml").exists() else None
    return load_config(
        user_path=user if user.exists() else None,
        project_path=project,
        env=dict(os.environ),
        overrides={},
    )


def get_workdir(ctx: click.Context) -> Path:
    obj = ctx.obj or {}
    return obj.get("workdir") or default_workdir()


def get_logger(ctx: click.Context) -> Logger:
    obj = ctx.obj or {}
    return Logger(json_mode=bool(obj.get("json_mode")), quiet=bool(obj.get("quiet")))
