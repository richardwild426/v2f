from __future__ import annotations

from typing import Any

from vtf.sinks.base import EmitOutcome


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
        return (True, "")

    def emit(self, result: dict[str, Any], cfg: Any) -> EmitOutcome:
        # 实际写入逻辑在 CLI 层调用 lark-cli
        # 这里仅返回成功状态，CLI 负责执行实际写入
        return EmitOutcome(sink="feishu")
