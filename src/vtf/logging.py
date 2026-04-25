from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any


class Logger:
    def __init__(
        self,
        stream: Any = sys.stderr,
        json_mode: bool = False,
        quiet: bool = False,
    ) -> None:
        self._stream = stream
        self._json = json_mode
        self._quiet = quiet

    def _emit(
        self,
        level: str,
        msg: str,
        step: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        if self._quiet and level == "info":
            return
        if self._json:
            rec: dict[str, Any] = {
                "ts": datetime.now().isoformat(),
                "level": level,
                "msg": msg,
            }
            if step:
                rec["step"] = step
            if data:
                rec["data"] = data
            self._stream.write(json.dumps(rec, ensure_ascii=False) + "\n")
        else:
            prefix = f"[{step}] " if step else ""
            self._stream.write(f"{prefix}{msg}\n")

    def info(self, msg: str, step: str | None = None, data: dict[str, Any] | None = None) -> None:
        self._emit("info", msg, step, data)

    def warn(self, msg: str, step: str | None = None, data: dict[str, Any] | None = None) -> None:
        self._emit("warn", msg, step, data)

    def error(self, msg: str, step: str | None = None, data: dict[str, Any] | None = None) -> None:
        self._emit("error", msg, step, data)
