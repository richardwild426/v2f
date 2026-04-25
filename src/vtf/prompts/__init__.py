from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

from jinja2 import Environment

_env = Environment(autoescape=False, keep_trailing_newline=True)


def load_prompt(kind: str, *, override_path: str) -> str:
    if override_path:
        return Path(override_path).read_text("utf-8")
    return files("vtf.prompts").joinpath(f"{kind}.md").read_text("utf-8")


def render_prompt(template: str, ctx: dict[str, Any]) -> str:
    rendered_ctx = dict(ctx)
    if "lines" in rendered_ctx and isinstance(rendered_ctx["lines"], list):
        rendered_ctx["lines"] = "\n".join(rendered_ctx["lines"])
    return _env.from_string(template).render(**rendered_ctx)


__all__ = ["load_prompt", "render_prompt"]
