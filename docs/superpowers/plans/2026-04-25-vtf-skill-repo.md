# vtf 通用技能仓库 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前的单文件 `SKILL.md` 改写为脚本驱动、平台无关的 `vtf` 技能仓库,提供端到端 CLI + 分步 CLI、双 sink(markdown / feishu)、Claude Code 与 Codex 的 wrapper,代码内零业务硬编码。

**Architecture:** Python CLI + uvx 分发。流水线分 6 步,每步 stdin/stdout JSON。三级配置覆盖(flag > 项目 toml > 用户 toml > 内置默认)。AI 分析仅产出 prompt,LLM 由宿主智能体执行。Sink 接口化,支持 markdown 与 feishu 切换且失败自动降级。Wrapper 是薄壳引用核心 `AGENT_GUIDE.md`。

**Tech Stack:** Python 3.11+、Click、tomllib、Jinja2(可选模板)、yt-dlp(运行时依赖)、FunASR(运行时依赖,Python 路径自动探测)、pytest、ruff、mypy。包管理用 uv。

**Spec:** [`docs/superpowers/specs/2026-04-25-vtf-skill-repo-design.md`](../specs/2026-04-25-vtf-skill-repo-design.md)

---

## 文件结构总览

最终目录布局(每个文件单一职责):

```
vtf/
├── pyproject.toml                       # 包元数据 + 依赖 + entry point
├── README.md                            # 用户视角:这是什么、安装、快速开始
├── AGENT_GUIDE.md                       # 智能体视角:命令清单 + workflow + analyze 契约
├── .gitignore
├── src/vtf/
│   ├── __init__.py                      # __version__
│   ├── __main__.py                      # python -m vtf
│   ├── cli.py                           # 顶层 Click group + 子命令分发
│   ├── config.py                        # 三级配置加载与合并
│   ├── errors.py                        # 退出码常量与异常类
│   ├── logging.py                       # --json / --quiet 日志辅助
│   ├── platforms/
│   │   ├── __init__.py                  # 注册表 + detect()
│   │   ├── base.py                      # Platform Protocol
│   │   ├── bilibili.py
│   │   ├── youtube.py
│   │   └── generic.py
│   ├── transcribe/
│   │   ├── __init__.py
│   │   └── funasr.py                    # Python 路径探测 + 子进程调用
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── fetch.py
│   │   ├── download.py
│   │   ├── merge.py                     # 句子碎片合并(无 IO 纯算法)
│   │   ├── analyze.py                   # prompt 渲染,无 LLM 调用
│   │   └── assemble.py
│   ├── sinks/
│   │   ├── __init__.py                  # 注册表 + get()
│   │   ├── base.py                      # Sink Protocol
│   │   ├── markdown.py
│   │   ├── feishu.py
│   │   └── schema.py                    # source 路径解析 + transformer
│   ├── prompts/
│   │   ├── __init__.py                  # 模板加载
│   │   ├── summary.md
│   │   ├── breakdown.md
│   │   └── rewrite.md
│   ├── doctor.py
│   ├── installer.py                     # vtf install <platform>
│   └── commands/                        # 各子命令的薄入口
│       ├── __init__.py
│       ├── run.py
│       ├── fetch.py
│       ├── download.py
│       ├── transcribe.py
│       ├── merge.py
│       ├── analyze.py
│       ├── assemble.py
│       ├── emit.py
│       ├── init.py
│       ├── config_cmd.py
│       ├── install.py
│       └── doctor.py
├── wrappers/
│   ├── claude-code/SKILL.md
│   ├── codex/AGENTS.md
│   └── generic/README.md
├── examples/
│   └── schemas/baokuan.toml
├── tests/
│   ├── conftest.py                      # 共享 fixture
│   ├── fixtures/
│   │   ├── meta_bilibili.json
│   │   ├── meta_youtube.json
│   │   ├── transcript_zh.json
│   │   └── lines_zh.json
│   ├── test_config.py
│   ├── test_platforms.py
│   ├── test_merge.py
│   ├── test_analyze.py
│   ├── test_assemble.py
│   ├── test_sink_schema.py
│   ├── test_sink_markdown.py
│   ├── test_sink_feishu.py
│   ├── test_doctor.py
│   ├── test_installer.py
│   └── test_cli.py
├── docs/
│   ├── install.md
│   ├── configuration.md
│   ├── extending.md
│   ├── legacy/SKILL.md.archive.md       # 当前 SKILL.md 归档
│   ├── superpowers/specs/...            # 已存在
│   └── superpowers/plans/...            # 已存在
```

阶段划分(每阶段结束都是一个**可验证的进展点**):

- **Stage 0** — 仓库骨架与工具链(git init、pyproject、ruff、mypy、pytest)
- **Stage 1** — 配置模块(三级合并)
- **Stage 2** — 错误码、日志辅助、流水线数据形状
- **Stage 3** — 平台适配(bilibili / youtube / generic)
- **Stage 4** — 流水线步骤(fetch / download / transcribe / merge / analyze / assemble)
- **Stage 5** — Sinks(schema 渲染 / markdown / feishu + 降级)
- **Stage 6** — CLI 顶层与子命令(run + 分步)
- **Stage 7** — 管理命令(init / config / doctor / install)
- **Stage 8** — Wrappers + 示例 schema
- **Stage 9** — 文档与迁移

---

## Stage 0 — 仓库骨架

### Task 0.1: 初始化 git 仓库与 .gitignore

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: 初始化 git 仓库**

```bash
cd /Users/zvector/ws/video-to-feishu
git init
git config commit.gpgsign false  # 本地避免 GPG 提示;若用户已配置签名则跳过此步
```

- [ ] **Step 2: 写 .gitignore**

写入 `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.uv-cache/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.mp3
*.m4a
*.wav
.DS_Store
.vtf-cache/
```

- [ ] **Step 3: 首次提交**

```bash
git add .gitignore
git commit -m "chore: 初始化 git 仓库与 gitignore"
```

### Task 0.2: 创建 pyproject.toml

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: 写 pyproject.toml**

```toml
[project]
name = "vtf"
version = "0.1.0"
description = "通用视频内容流水线 CLI:URL → 转录 → AI 分析 → markdown / 飞书"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "vtf contributors" }]
dependencies = [
    "click>=8.1",
    "jinja2>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",
    "ruff>=0.4",
    "mypy>=1.10",
]

[project.scripts]
vtf = "vtf.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/vtf"]

[tool.hatch.build.targets.wheel.shared-data]
"src/vtf/prompts" = "vtf/prompts"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
files = ["src/vtf"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
```

- [ ] **Step 2: 创建包目录占位**

```bash
mkdir -p src/vtf tests
touch src/vtf/__init__.py tests/__init__.py
```

写入 `src/vtf/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: 同步依赖**

```bash
uv sync --extra dev
```

预期:`.venv/` 创建,依赖安装成功。

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml src/vtf/__init__.py tests/__init__.py
git commit -m "chore: 添加 pyproject.toml 与包骨架"
```

### Task 0.3: 接入 ruff + mypy + pytest 烟雾测试

**Files:**
- Create: `tests/test_smoke.py`
- Create: `src/vtf/__main__.py`

- [ ] **Step 1: 写最小烟雾测试**

`tests/test_smoke.py`:

```python
import vtf


def test_version_exposed():
    assert vtf.__version__ == "0.1.0"
```

- [ ] **Step 2: 写 __main__.py**

`src/vtf/__main__.py`:

```python
from vtf.cli import main


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 添加最小 cli.py 让导入通过**

`src/vtf/cli.py`:

```python
import click


@click.group()
@click.version_option(package_name="vtf")
def main() -> None:
    """vtf - 视频内容流水线 CLI"""


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑测试 + 静态检查**

```bash
uv run pytest -q
uv run ruff check src tests
uv run mypy
```

预期:全部通过。

- [ ] **Step 5: 提交**

```bash
git add tests/test_smoke.py src/vtf/__main__.py src/vtf/cli.py
git commit -m "chore: 添加烟雾测试与 CLI 最小入口"
```

---

## Stage 1 — 配置模块

### Task 1.1: 配置默认值与数据类

**Files:**
- Create: `src/vtf/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: 写失败测试 - 默认配置**

`tests/test_config.py`:

```python
from vtf.config import Config, load_config


def test_default_config_values():
    cfg = load_config(user_path=None, project_path=None, env={}, overrides={})
    assert cfg.output.sink == "markdown"
    assert cfg.transcribe.asr_model == "paraformer-zh"
    assert cfg.transcribe.vad_model == "fsmn-vad"
    assert cfg.transcribe.punc_model == "ct-punc"
    assert cfg.transcribe.batch_size_s == 300
    assert cfg.platform.bilibili.cookies_from_browser == "chrome"
    assert cfg.platform.youtube.cookies_from_browser == ""
    assert cfg.download.audio_format == "mp3"
    assert cfg.download.audio_quality == "0"
    assert cfg.download.retries == 3
    assert cfg.sink.feishu.lark_cli == "lark-cli"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_config.py -v
```

预期:`ImportError`。

- [ ] **Step 3: 写 config.py**

`src/vtf/config.py`:

```python
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
```

- [ ] **Step 4: 跑测试确认通过**

```bash
uv run pytest tests/test_config.py -v
```

预期:`test_default_config_values` PASS。

- [ ] **Step 5: 提交**

```bash
git add src/vtf/config.py tests/test_config.py
git commit -m "feat: 配置默认值与数据类"
```

### Task 1.2: 项目级 toml 覆盖用户级

**Files:**
- Modify: `tests/test_config.py`

- [ ] **Step 1: 添加测试**

追加到 `tests/test_config.py`:

```python
def test_project_overrides_user(tmp_path):
    user = tmp_path / "user.toml"
    user.write_text(
        '[output]\nsink = "feishu"\n[transcribe]\nasr_model = "u-model"\n',
        encoding="utf-8",
    )
    project = tmp_path / "vtf.toml"
    project.write_text('[transcribe]\nasr_model = "p-model"\n', encoding="utf-8")
    cfg = load_config(user_path=user, project_path=project, env={}, overrides={})
    assert cfg.output.sink == "feishu"
    assert cfg.transcribe.asr_model == "p-model"
```

- [ ] **Step 2: 跑测试确认通过(load_config 已支持)**

```bash
uv run pytest tests/test_config.py -v
```

预期:全部 PASS。

- [ ] **Step 3: 提交**

```bash
git add tests/test_config.py
git commit -m "test: 项目 toml 覆盖用户 toml"
```

### Task 1.3: 环境变量与 legacy 别名覆盖

**Files:**
- Modify: `tests/test_config.py`

- [ ] **Step 1: 添加测试**

```python
def test_env_overrides_files(tmp_path):
    user = tmp_path / "user.toml"
    user.write_text('[output]\nsink = "markdown"\n', encoding="utf-8")
    cfg = load_config(
        user_path=user,
        project_path=None,
        env={
            "VTF_OUTPUT_SINK": "feishu",
            "VTF_TRANSCRIBE_BATCH_SIZE_S": "120",
            "VTF_DOWNLOAD_RETRIES": "5",
        },
        overrides={},
    )
    assert cfg.output.sink == "feishu"
    assert cfg.transcribe.batch_size_s == 120
    assert cfg.download.retries == 5


def test_legacy_table_token_alias():
    cfg = load_config(
        user_path=None,
        project_path=None,
        env={"TABLE_TOKEN": "tok123", "TABLE_ID": "tbl456"},
        overrides={},
    )
    assert cfg.sink.feishu.base_token == "tok123"
    assert cfg.sink.feishu.table_id == "tbl456"
```

- [ ] **Step 2: 跑测试**

```bash
uv run pytest tests/test_config.py -v
```

预期:两个新测试 PASS。

- [ ] **Step 3: 提交**

```bash
git add tests/test_config.py
git commit -m "test: 环境变量与 legacy 别名覆盖"
```

### Task 1.4: overrides 字典优先级最高

**Files:**
- Modify: `tests/test_config.py`

- [ ] **Step 1: 添加测试**

```python
def test_overrides_have_highest_priority(tmp_path):
    user = tmp_path / "user.toml"
    user.write_text('[output]\nsink = "feishu"\n', encoding="utf-8")
    cfg = load_config(
        user_path=user,
        project_path=None,
        env={"VTF_OUTPUT_SINK": "feishu"},
        overrides={"output": {"sink": "markdown"}},
    )
    assert cfg.output.sink == "markdown"
```

- [ ] **Step 2: 跑测试**

```bash
uv run pytest tests/test_config.py -v
```

预期:PASS。

- [ ] **Step 3: 提交**

```bash
git add tests/test_config.py
git commit -m "test: overrides 优先级最高"
```

---

## Stage 2 — 错误、日志、流水线数据形状

### Task 2.1: 错误码与异常

**Files:**
- Create: `src/vtf/errors.py`
- Create: `tests/test_errors.py`

- [ ] **Step 1: 写测试**

`tests/test_errors.py`:

```python
from vtf.errors import (
    EXIT_OK,
    EXIT_USER,
    EXIT_ENV,
    EXIT_REMOTE,
    EXIT_BUG,
    UserError,
    EnvironmentError as VtfEnvError,
    RemoteError,
)


def test_exit_codes_distinct():
    assert {EXIT_OK, EXIT_USER, EXIT_ENV, EXIT_REMOTE, EXIT_BUG} == {0, 1, 2, 3, 4}


def test_exception_carries_exit_code():
    e = UserError("bad arg")
    assert e.exit_code == EXIT_USER
    assert str(e) == "bad arg"
    assert VtfEnvError("missing").exit_code == EXIT_ENV
    assert RemoteError("412").exit_code == EXIT_REMOTE
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_errors.py -v
```

预期:`ImportError`。

- [ ] **Step 3: 写 errors.py**

`src/vtf/errors.py`:

```python
EXIT_OK = 0
EXIT_USER = 1
EXIT_ENV = 2
EXIT_REMOTE = 3
EXIT_BUG = 4


class VtfError(Exception):
    exit_code: int = EXIT_BUG


class UserError(VtfError):
    exit_code = EXIT_USER


class EnvironmentError(VtfError):  # noqa: A001 - intentional shadowing
    exit_code = EXIT_ENV


class RemoteError(VtfError):
    exit_code = EXIT_REMOTE
```

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/test_errors.py -v
```

预期:PASS。

- [ ] **Step 5: 提交**

```bash
git add src/vtf/errors.py tests/test_errors.py
git commit -m "feat: 错误码与异常类型"
```

### Task 2.2: 结构化日志辅助

**Files:**
- Create: `src/vtf/logging.py`
- Create: `tests/test_logging.py`

- [ ] **Step 1: 写测试**

`tests/test_logging.py`:

```python
import io
import json

from vtf.logging import Logger


def test_text_mode_writes_to_stderr():
    buf = io.StringIO()
    log = Logger(stream=buf, json_mode=False, quiet=False)
    log.info("hello", step="fetch")
    out = buf.getvalue()
    assert "hello" in out
    assert "fetch" in out


def test_json_mode_emits_jsonl():
    buf = io.StringIO()
    log = Logger(stream=buf, json_mode=True, quiet=False)
    log.warn("degraded", step="emit", data={"reason": "412"})
    line = buf.getvalue().strip()
    rec = json.loads(line)
    assert rec["level"] == "warn"
    assert rec["step"] == "emit"
    assert rec["msg"] == "degraded"
    assert rec["data"]["reason"] == "412"
    assert "ts" in rec


def test_quiet_suppresses_info_keeps_error():
    buf = io.StringIO()
    log = Logger(stream=buf, json_mode=False, quiet=True)
    log.info("ignored")
    log.error("boom")
    out = buf.getvalue()
    assert "ignored" not in out
    assert "boom" in out
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_logging.py -v
```

- [ ] **Step 3: 写 logging.py**

`src/vtf/logging.py`:

```python
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import IO, Any


@dataclass
class Logger:
    stream: IO[str]
    json_mode: bool = False
    quiet: bool = False

    def info(self, msg: str, *, step: str = "", data: dict[str, Any] | None = None) -> None:
        if self.quiet:
            return
        self._emit("info", msg, step, data)

    def warn(self, msg: str, *, step: str = "", data: dict[str, Any] | None = None) -> None:
        self._emit("warn", msg, step, data)

    def error(self, msg: str, *, step: str = "", data: dict[str, Any] | None = None) -> None:
        self._emit("error", msg, step, data)

    def _emit(
        self,
        level: str,
        msg: str,
        step: str,
        data: dict[str, Any] | None,
    ) -> None:
        if self.json_mode:
            rec = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "msg": msg,
                "step": step,
                "data": data or {},
            }
            print(json.dumps(rec, ensure_ascii=False), file=self.stream)
        else:
            tag = f"[{step}]" if step else ""
            print(f"{level.upper():5} {tag} {msg}", file=self.stream)


def make_default(json_mode: bool, quiet: bool) -> Logger:
    return Logger(stream=sys.stderr, json_mode=json_mode, quiet=quiet)
```

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/test_logging.py -v
```

预期:全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add src/vtf/logging.py tests/test_logging.py
git commit -m "feat: 结构化日志辅助(text/json/quiet)"
```

### Task 2.3: 数据形状文档(无代码,但锁住后续 IO 契约)

**Files:**
- Create: `docs/data-shapes.md`

- [ ] **Step 1: 写 docs/data-shapes.md**

```markdown
# Pipeline 数据形状参考

每个流水线步骤通过 stdin/stdout 传递 JSON。以下是契约,后续修改需更新本文档。

## meta.json (fetch 输出)

```json
{
  "platform": "bilibili",
  "video_id": "BV1xxx",
  "url": "https://www.bilibili.com/video/BV1xxx",
  "title": "...",
  "author": "...",
  "upload_date": "2026-04-01 12:30",
  "duration": 600,
  "duration_str": "10:00",
  "thumbnail": "https://...",
  "description": "...",
  "view": 12345,
  "like": 678,
  "favorite": 0,
  "share": 0,
  "reply": 90
}
```

## transcript.json (transcribe 输出)

```json
{
  "audio_path": "/path/to/audio.mp3",
  "asr_model": "paraformer-zh",
  "sentences": ["第一句", "第二句", "..."]
}
```

## lines.json (merge 输出)

```json
{
  "lines": ["合并后的第一行", "合并后的第二行", "..."]
}
```

## analysis.json (analyze 输出,result 由 agent 回填)

```json
{
  "kind": "summary",
  "prompt": "<完整渲染的 LLM prompt>",
  "context": {"title": "...", "author": "...", "lines_count": 42},
  "schema_hint": "expected: {text, points[], tags[]}",
  "result": null
}
```

agent 跑完 LLM 后,把 `result` 字段填上对象,再交给 `vtf assemble`。

## result.json (assemble 输出)

```json
{
  "meta": { ... },
  "lines": ["..."],
  "analyses": {
    "summary":   { "text": "...", "points": ["..."], "tags": ["..."] },
    "breakdown": { "text": "...", "hook": "...", "core": "...", "cta": "..." },
    "rewrite":   { "text": "..." }
  }
}
```

未跑的 analyze kind 在 `analyses` 中缺失即可,sink 渲染时按缺失处理。
```

- [ ] **Step 2: 提交**

```bash
git add docs/data-shapes.md
git commit -m "docs: 流水线数据形状参考"
```

---

## Stage 3 — 平台适配

### Task 3.1: Platform Protocol 与注册表

**Files:**
- Create: `src/vtf/platforms/__init__.py`
- Create: `src/vtf/platforms/base.py`
- Create: `tests/test_platforms.py`

- [ ] **Step 1: 写测试**

`tests/test_platforms.py`:

```python
import pytest

from vtf.platforms import detect


def test_detect_bilibili_long_url():
    p = detect("https://www.bilibili.com/video/BV1xxx")
    assert p.name == "bilibili"


def test_detect_bilibili_short_url():
    p = detect("https://b23.tv/abcd")
    assert p.name == "bilibili"


def test_detect_youtube_long_url():
    p = detect("https://www.youtube.com/watch?v=xxx")
    assert p.name == "youtube"


def test_detect_youtube_short_url():
    p = detect("https://youtu.be/xxx")
    assert p.name == "youtube"


def test_detect_unknown_falls_back_to_generic():
    p = detect("https://twitter.com/user/status/123")
    assert p.name == "generic"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_platforms.py -v
```

- [ ] **Step 3: 写 base.py**

`src/vtf/platforms/base.py`:

```python
from __future__ import annotations

from typing import Any, Protocol


class Platform(Protocol):
    name: str

    def matches(self, url: str) -> bool: ...
    def cookie_args(self, cfg: Any) -> list[str]: ...
    def normalize_metadata(self, raw: dict[str, Any]) -> dict[str, Any]: ...
```

- [ ] **Step 4: 写 __init__.py 注册表**

`src/vtf/platforms/__init__.py`:

```python
from __future__ import annotations

from vtf.platforms.base import Platform
from vtf.platforms.bilibili import Bilibili
from vtf.platforms.generic import Generic
from vtf.platforms.youtube import YouTube

REGISTRY: list[Platform] = [Bilibili(), YouTube()]
_FALLBACK: Platform = Generic()


def detect(url: str) -> Platform:
    for p in REGISTRY:
        if p.matches(url):
            return p
    return _FALLBACK


__all__ = ["Platform", "detect", "REGISTRY"]
```

- [ ] **Step 5: 写最小三个平台占位**

`src/vtf/platforms/bilibili.py`:

```python
from __future__ import annotations

import re
from typing import Any


class Bilibili:
    name = "bilibili"
    _pat = re.compile(r"(?:bilibili\.com|b23\.tv)")

    def matches(self, url: str) -> bool:
        return bool(self._pat.search(url))

    def cookie_args(self, cfg: Any) -> list[str]:
        b = cfg.platform.bilibili
        if b.cookies_file:
            return ["--cookies", b.cookies_file]
        if b.cookies_from_browser:
            return ["--cookies-from-browser", b.cookies_from_browser]
        return []

    def normalize_metadata(self, raw: dict[str, Any]) -> dict[str, Any]:
        return _common_normalize(raw, platform="bilibili")
```

`src/vtf/platforms/youtube.py`:

```python
from __future__ import annotations

import re
from typing import Any


class YouTube:
    name = "youtube"
    _pat = re.compile(r"(?:youtube\.com|youtu\.be)")

    def matches(self, url: str) -> bool:
        return bool(self._pat.search(url))

    def cookie_args(self, cfg: Any) -> list[str]:
        y = cfg.platform.youtube
        if y.cookies_file:
            return ["--cookies", y.cookies_file]
        if y.cookies_from_browser:
            return ["--cookies-from-browser", y.cookies_from_browser]
        return []

    def normalize_metadata(self, raw: dict[str, Any]) -> dict[str, Any]:
        out = _common_normalize(raw, platform="youtube")
        out["reply"] = raw.get("comment_count", 0)
        return out
```

`src/vtf/platforms/generic.py`:

```python
from __future__ import annotations

from typing import Any


class Generic:
    name = "generic"

    def matches(self, url: str) -> bool:
        return False

    def cookie_args(self, cfg: Any) -> list[str]:
        return []

    def normalize_metadata(self, raw: dict[str, Any]) -> dict[str, Any]:
        return _common_normalize(raw, platform="generic")
```

- [ ] **Step 6: 写共享归一化辅助**

新增 `src/vtf/platforms/_normalize.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any


def _common_normalize(raw: dict[str, Any], *, platform: str) -> dict[str, Any]:
    upload_date = raw.get("upload_date", "") or ""
    if upload_date and len(upload_date) == 8:
        try:
            upload_date = datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
    duration = int(raw.get("duration") or 0)
    return {
        "platform": platform,
        "video_id": raw.get("id", "") or "",
        "url": raw.get("webpage_url", "") or "",
        "title": raw.get("title", "") or "",
        "author": raw.get("uploader", "") or "",
        "upload_date": upload_date,
        "duration": duration,
        "duration_str": f"{duration // 60}:{duration % 60:02d}",
        "thumbnail": raw.get("thumbnail", "") or "",
        "description": (raw.get("description", "") or "")[:500],
        "view": int(raw.get("view_count") or 0),
        "like": int(raw.get("like_count") or 0),
        "favorite": 0,
        "share": 0,
        "reply": 0,
    }
```

更新三个平台文件,改为 `from vtf.platforms._normalize import _common_normalize` 而不是直接定义。

- [ ] **Step 7: 跑测试**

```bash
uv run pytest tests/test_platforms.py -v
```

预期:全部 PASS。

- [ ] **Step 8: 提交**

```bash
git add src/vtf/platforms tests/test_platforms.py
git commit -m "feat: 平台注册表与三个内置适配器"
```

### Task 3.2: 平台 cookie_args 测试

**Files:**
- Modify: `tests/test_platforms.py`

- [ ] **Step 1: 添加测试**

```python
from vtf.config import Config


def test_bilibili_default_cookie_args():
    p = next(x for x in __import__("vtf.platforms", fromlist=["REGISTRY"]).REGISTRY if x.name == "bilibili")
    args = p.cookie_args(Config())
    assert args == ["--cookies-from-browser", "chrome"]


def test_bilibili_cookies_file_overrides_browser(tmp_path):
    cfg = Config()
    f = tmp_path / "c.txt"
    f.write_text("# cookie", encoding="utf-8")
    cfg.platform.bilibili.cookies_file = str(f)
    p = next(x for x in __import__("vtf.platforms", fromlist=["REGISTRY"]).REGISTRY if x.name == "bilibili")
    args = p.cookie_args(cfg)
    assert args == ["--cookies", str(f)]


def test_youtube_no_cookie_by_default():
    p = next(x for x in __import__("vtf.platforms", fromlist=["REGISTRY"]).REGISTRY if x.name == "youtube")
    args = p.cookie_args(Config())
    assert args == []
```

- [ ] **Step 2: 跑测试**

```bash
uv run pytest tests/test_platforms.py -v
```

预期:全部 PASS。

- [ ] **Step 3: 提交**

```bash
git add tests/test_platforms.py
git commit -m "test: 平台 cookie_args 行为"
```

### Task 3.3: 元数据归一化测试

**Files:**
- Create: `tests/fixtures/raw_yt_dlp_bilibili.json`
- Create: `tests/fixtures/raw_yt_dlp_youtube.json`
- Modify: `tests/test_platforms.py`

- [ ] **Step 1: 写 fixture**

`tests/fixtures/raw_yt_dlp_bilibili.json`:

```json
{
  "id": "BV1xxx",
  "webpage_url": "https://www.bilibili.com/video/BV1xxx",
  "title": "测试视频",
  "uploader": "测试UP",
  "upload_date": "20260401",
  "duration": 600,
  "thumbnail": "https://i0.hdslb.com/x.jpg",
  "description": "abc",
  "view_count": 12345,
  "like_count": 678
}
```

`tests/fixtures/raw_yt_dlp_youtube.json`:

```json
{
  "id": "vid123",
  "webpage_url": "https://www.youtube.com/watch?v=vid123",
  "title": "demo",
  "uploader": "ChannelX",
  "upload_date": "20260330",
  "duration": 125,
  "thumbnail": "https://i.ytimg.com/x.jpg",
  "description": "y",
  "view_count": 1000,
  "like_count": 50,
  "comment_count": 7
}
```

- [ ] **Step 2: 写 conftest.py 提供 fixture 路径**

`tests/conftest.py`:

```python
import json
from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture()
def raw_bilibili():
    return json.loads((FIX / "raw_yt_dlp_bilibili.json").read_text("utf-8"))


@pytest.fixture()
def raw_youtube():
    return json.loads((FIX / "raw_yt_dlp_youtube.json").read_text("utf-8"))
```

- [ ] **Step 3: 添加测试**

```python
def test_bilibili_normalize(raw_bilibili):
    p = next(x for x in __import__("vtf.platforms", fromlist=["REGISTRY"]).REGISTRY if x.name == "bilibili")
    out = p.normalize_metadata(raw_bilibili)
    assert out["platform"] == "bilibili"
    assert out["video_id"] == "BV1xxx"
    assert out["title"] == "测试视频"
    assert out["author"] == "测试UP"
    assert out["upload_date"] == "2026-04-01 00:00"
    assert out["duration_str"] == "10:00"
    assert out["view"] == 12345
    assert out["favorite"] == 0
    assert out["share"] == 0
    assert out["reply"] == 0


def test_youtube_normalize_uses_comment_count(raw_youtube):
    p = next(x for x in __import__("vtf.platforms", fromlist=["REGISTRY"]).REGISTRY if x.name == "youtube")
    out = p.normalize_metadata(raw_youtube)
    assert out["reply"] == 7
    assert out["duration_str"] == "2:05"
```

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/test_platforms.py -v
```

预期:全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add tests/fixtures tests/conftest.py tests/test_platforms.py
git commit -m "test: 元数据归一化"
```

---

## Stage 4 — 流水线步骤

### Task 4.1: merge 算法(纯函数,无 IO)

**Files:**
- Create: `src/vtf/pipeline/__init__.py`
- Create: `src/vtf/pipeline/merge.py`
- Create: `tests/test_merge.py`

- [ ] **Step 1: 写测试**

`tests/test_merge.py`:

```python
from vtf.pipeline.merge import merge_into_lines


def test_simple_concat():
    out = merge_into_lines(["你好", "世界"])
    assert out == ["你好世界"]


def test_split_on_period():
    out = merge_into_lines(["你好。", "世界"])
    assert out == ["你好。", "世界"]


def test_does_not_split_inside_brackets():
    out = merge_into_lines(["他说（这", "是括号）。", "结束"])
    assert out == ["他说（这是括号）。", "结束"]


def test_strips_trailing_comma():
    out = merge_into_lines(["你好，"])
    assert out == ["你好"]


def test_skips_empty():
    out = merge_into_lines(["", " ", "正文"])
    assert out == ["正文"]
```

- [ ] **Step 2: 跑测试确认失败**

```bash
uv run pytest tests/test_merge.py -v
```

- [ ] **Step 3: 写 merge.py**

`src/vtf/pipeline/merge.py`:

```python
from __future__ import annotations

_OPEN = set("(《【〖「『〔｛")
_CLOSE_MAP = {
    "(": ")",
    "《": "》",
    "【": "】",
    "〖": "〗",
    "「": "」",
    "『": "』",
    "〔": "〕",
    "｛": "｝",
}
_ENDERS = set("。!?…")
_NEW_THOUGHT_FIRSTS = set("第首先然后而且所以但是然而不过可是如果虽然")


def merge_into_lines(sentences: list[str]) -> list[str]:
    lines: list[str] = []
    buf = ""
    stack: list[str] = []
    for raw in sentences:
        s = raw.strip()
        if not s:
            continue
        for ch in s:
            if ch in _OPEN:
                stack.append(ch)
            elif stack and ch == _CLOSE_MAP.get(stack[-1]):
                stack.pop()
        in_bracket = bool(stack)
        split = False
        if buf:
            if in_bracket:
                split = False
            elif buf[-1] in _ENDERS:
                split = True
            elif len(buf) > 15 and s[0] in _NEW_THOUGHT_FIRSTS:
                split = True
        if split:
            lines.append(buf)
            buf = s
        else:
            buf += s
    if buf:
        lines.append(buf)
    cleaned: list[str] = []
    for line in lines:
        ln = line.strip()
        while ln and ln[-1] == ",":
            ln = ln[:-1].strip()
        if ln:
            cleaned.append(ln)
    return cleaned


__all__ = ["merge_into_lines"]
```

`src/vtf/pipeline/__init__.py`:

```python
```

(空文件)

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/test_merge.py -v
```

预期:全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add src/vtf/pipeline tests/test_merge.py
git commit -m "feat: 句子碎片合并算法"
```

### Task 4.2: prompts 模板加载

**Files:**
- Create: `src/vtf/prompts/__init__.py`
- Create: `src/vtf/prompts/summary.md`
- Create: `src/vtf/prompts/breakdown.md`
- Create: `src/vtf/prompts/rewrite.md`
- Create: `tests/test_prompts.py`

- [ ] **Step 1: 写测试**

`tests/test_prompts.py`:

```python
from vtf.prompts import load_prompt, render_prompt


def test_load_builtin_summary():
    text = load_prompt("summary", override_path="")
    assert "{{ title }}" in text
    assert "{{ lines }}" in text


def test_load_override(tmp_path):
    p = tmp_path / "my.md"
    p.write_text("custom {{ title }}", encoding="utf-8")
    assert load_prompt("summary", override_path=str(p)) == "custom {{ title }}"


def test_render_substitutes():
    out = render_prompt("hello {{ title }} by {{ author }}", {"title": "T", "author": "A"})
    assert out == "hello T by A"


def test_render_lines_joined():
    out = render_prompt("L:\n{{ lines }}", {"lines": ["a", "b", "c"]})
    assert out == "L:\na\nb\nc"
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 写 prompts 模板**

`src/vtf/prompts/summary.md`:

```markdown
你是一个视频内容分析专家。请分析以下视频文案,生成结构化摘要。

视频标题:{{ title }}
作者:{{ author }}
平台:{{ platform }}
文案:
{{ lines }}

请生成 JSON,包含字段:text(一句话摘要,50字以内)、points(核心要点数组,3-5条)、tags(标签数组,5个)。
```

`src/vtf/prompts/breakdown.md`:

```markdown
分析以下视频的结构。

标题:{{ title }}
作者:{{ author }}
文案:
{{ lines }}

请输出 JSON,包含字段:hook、core、cta、pros、suggestions、text(可选,完整说明)。
```

`src/vtf/prompts/rewrite.md`:

```markdown
你是一位 AI 科技自媒体博主,风格睿智、松弛、有见解。
对以下文案做创造性重构,而非简单替换。
- 保持核心信息不变,但表达方式、句式结构、叙述角度彻底改造
- 每行与原稿字数 ±30%,行数一致
- 删除口语词:啊、呢、吧、就是说、其实、那么
- 严禁低俗营销词

原文:
{{ lines }}

请逐行输出改写后的文案,放进 JSON 字段 text(用换行连接)。
```

- [ ] **Step 4: 写 prompts/__init__.py**

`src/vtf/prompts/__init__.py`:

```python
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
```

- [ ] **Step 5: 跑测试**

```bash
uv run pytest tests/test_prompts.py -v
```

预期:PASS。

- [ ] **Step 6: 提交**

```bash
git add src/vtf/prompts tests/test_prompts.py
git commit -m "feat: prompts 模板加载与渲染"
```

### Task 4.3: analyze 步骤

**Files:**
- Create: `src/vtf/pipeline/analyze.py`
- Create: `tests/test_analyze.py`

- [ ] **Step 1: 写测试**

`tests/test_analyze.py`:

```python
from vtf.config import Config
from vtf.pipeline.analyze import analyze


def test_analyze_summary_emits_prompt_and_context():
    cfg = Config()
    out = analyze(
        kind="summary",
        meta={"title": "T", "author": "A", "platform": "bilibili"},
        lines=["第一行", "第二行"],
        cfg=cfg,
    )
    assert out["kind"] == "summary"
    assert "T" in out["prompt"]
    assert "第一行" in out["prompt"]
    assert out["context"]["lines_count"] == 2
    assert out["result"] is None
    assert "schema_hint" in out


def test_analyze_uses_override_prompt(tmp_path):
    p = tmp_path / "my.md"
    p.write_text("MY {{ title }} END", encoding="utf-8")
    cfg = Config()
    cfg.analyze.prompts.summary = str(p)
    out = analyze(
        kind="summary",
        meta={"title": "Z", "author": "", "platform": ""},
        lines=[],
        cfg=cfg,
    )
    assert "MY Z END" in out["prompt"]


def test_analyze_unknown_kind_raises():
    import pytest

    from vtf.errors import UserError

    with pytest.raises(UserError):
        analyze(
            kind="bogus",
            meta={"title": "", "author": "", "platform": ""},
            lines=[],
            cfg=Config(),
        )
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 写 analyze.py**

`src/vtf/pipeline/analyze.py`:

```python
from __future__ import annotations

from typing import Any

from vtf.errors import UserError
from vtf.prompts import load_prompt, render_prompt

_KINDS = {"summary", "breakdown", "rewrite"}

_SCHEMA_HINTS = {
    "summary": "expected: {text, points[], tags[]}",
    "breakdown": "expected: {hook, core, cta, pros, suggestions, text}",
    "rewrite": "expected: {text}",
}


def analyze(
    *,
    kind: str,
    meta: dict[str, Any],
    lines: list[str],
    cfg: Any,
) -> dict[str, Any]:
    if kind not in _KINDS:
        raise UserError(f"unknown analyze kind: {kind!r}; allowed: {sorted(_KINDS)}")
    override = getattr(cfg.analyze.prompts, kind, "") or ""
    template = load_prompt(kind, override_path=override)
    prompt = render_prompt(
        template,
        {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "platform": meta.get("platform", ""),
            "lines": lines,
        },
    )
    return {
        "kind": kind,
        "prompt": prompt,
        "context": {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "platform": meta.get("platform", ""),
            "lines_count": len(lines),
        },
        "schema_hint": _SCHEMA_HINTS[kind],
        "result": None,
    }
```

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/test_analyze.py -v
```

预期:PASS。

- [ ] **Step 5: 提交**

```bash
git add src/vtf/pipeline/analyze.py tests/test_analyze.py
git commit -m "feat: analyze 步骤产出 prompt 与 context"
```

### Task 4.4: assemble 步骤

**Files:**
- Create: `src/vtf/pipeline/assemble.py`
- Create: `tests/test_assemble.py`

- [ ] **Step 1: 写测试**

`tests/test_assemble.py`:

```python
import pytest

from vtf.errors import UserError
from vtf.pipeline.assemble import assemble


def test_assemble_combines_inputs():
    meta = {"title": "T", "url": "u"}
    lines = ["a", "b"]
    analyses = [
        {"kind": "summary", "result": {"text": "S", "points": ["p"], "tags": ["#x"]}},
        {"kind": "breakdown", "result": {"text": "B"}},
    ]
    out = assemble(meta=meta, lines=lines, analyses=analyses)
    assert out["meta"] == meta
    assert out["lines"] == lines
    assert out["analyses"]["summary"]["text"] == "S"
    assert out["analyses"]["breakdown"]["text"] == "B"
    assert "rewrite" not in out["analyses"]


def test_assemble_rejects_unfilled_result():
    with pytest.raises(UserError, match="result"):
        assemble(
            meta={},
            lines=[],
            analyses=[{"kind": "summary", "result": None}],
        )


def test_assemble_rejects_duplicate_kind():
    with pytest.raises(UserError, match="duplicate"):
        assemble(
            meta={},
            lines=[],
            analyses=[
                {"kind": "summary", "result": {}},
                {"kind": "summary", "result": {}},
            ],
        )
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 写 assemble.py**

`src/vtf/pipeline/assemble.py`:

```python
from __future__ import annotations

from typing import Any

from vtf.errors import UserError


def assemble(
    *,
    meta: dict[str, Any],
    lines: list[str],
    analyses: list[dict[str, Any]],
) -> dict[str, Any]:
    out_analyses: dict[str, Any] = {}
    for a in analyses:
        kind = a.get("kind")
        if not kind:
            raise UserError("analysis missing 'kind'")
        if kind in out_analyses:
            raise UserError(f"duplicate analyze kind: {kind}")
        if a.get("result") is None:
            raise UserError(
                f"analyze[{kind}].result is null; agent must fill it before assemble"
            )
        out_analyses[kind] = a["result"]
    return {"meta": meta, "lines": lines, "analyses": out_analyses}
```

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/test_assemble.py -v
```

预期:PASS。

- [ ] **Step 5: 提交**

```bash
git add src/vtf/pipeline/assemble.py tests/test_assemble.py
git commit -m "feat: assemble 步骤"
```

### Task 4.5: fetch 步骤(yt-dlp 封装)

**Files:**
- Create: `src/vtf/pipeline/fetch.py`
- Create: `tests/test_fetch.py`

- [ ] **Step 1: 写测试**

`tests/test_fetch.py`:

```python
import json

import pytest

from vtf.config import Config
from vtf.pipeline.fetch import fetch


def test_fetch_calls_yt_dlp_with_cookie(monkeypatch, raw_bilibili):
    captured: dict = {}

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        captured["cmd"] = cmd
        return type(
            "R", (), {"returncode": 0, "stdout": json.dumps(raw_bilibili), "stderr": ""}
        )()

    monkeypatch.setattr("vtf.pipeline.fetch.subprocess.run", fake_run)
    cfg = Config()
    out = fetch(url="https://www.bilibili.com/video/BV1xxx", cfg=cfg)
    assert out["platform"] == "bilibili"
    assert "--cookies-from-browser" in captured["cmd"]
    assert "chrome" in captured["cmd"]


def test_fetch_youtube_no_cookie(monkeypatch, raw_youtube):
    captured: dict = {}

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        captured["cmd"] = cmd
        return type(
            "R", (), {"returncode": 0, "stdout": json.dumps(raw_youtube), "stderr": ""}
        )()

    monkeypatch.setattr("vtf.pipeline.fetch.subprocess.run", fake_run)
    out = fetch(url="https://youtu.be/vid123", cfg=Config())
    assert out["platform"] == "youtube"
    assert "--cookies-from-browser" not in captured["cmd"]


def test_fetch_propagates_yt_dlp_error(monkeypatch):
    from vtf.errors import RemoteError

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        return type("R", (), {"returncode": 1, "stdout": "", "stderr": "412"})()

    monkeypatch.setattr("vtf.pipeline.fetch.subprocess.run", fake_run)
    with pytest.raises(RemoteError, match="412"):
        fetch(url="https://www.bilibili.com/video/BV1xxx", cfg=Config())
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 写 fetch.py**

`src/vtf/pipeline/fetch.py`:

```python
from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

from vtf.errors import EnvironmentError as VtfEnvError, RemoteError
from vtf.platforms import detect


def fetch(*, url: str, cfg: Any) -> dict[str, Any]:
    yt_dlp = os.environ.get("VTF_YT_DLP") or shutil.which("yt-dlp")
    if not yt_dlp:
        raise VtfEnvError("yt-dlp 未找到。请 `pip install yt-dlp` 或设置 VTF_YT_DLP")
    platform = detect(url)
    cmd = [yt_dlp, "-J", *platform.cookie_args(cfg), url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RemoteError(f"yt-dlp 失败({r.returncode}):{r.stderr.strip()[:200]}")
    raw = json.loads(r.stdout)
    return platform.normalize_metadata(raw)
```

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/test_fetch.py -v
```

预期:PASS。

- [ ] **Step 5: 提交**

```bash
git add src/vtf/pipeline/fetch.py tests/test_fetch.py
git commit -m "feat: fetch 步骤封装 yt-dlp"
```

### Task 4.6: download 步骤

**Files:**
- Create: `src/vtf/pipeline/download.py`
- Create: `tests/test_download.py`

- [ ] **Step 1: 写测试**

`tests/test_download.py`:

```python
import pytest

from vtf.config import Config
from vtf.errors import EnvironmentError as VtfEnvError, RemoteError
from vtf.pipeline.download import download


def test_download_builds_command(monkeypatch, tmp_path):
    captured: dict = {}

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        captured["cmd"] = cmd
        out = tmp_path / "BV1.mp3"
        out.write_bytes(b"\x00")
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("vtf.pipeline.download.subprocess.run", fake_run)
    monkeypatch.setattr("vtf.pipeline.download.shutil.which", lambda _: "/usr/bin/yt-dlp")
    meta = {
        "platform": "bilibili",
        "video_id": "BV1",
        "url": "https://www.bilibili.com/video/BV1",
    }
    out = download(meta=meta, cfg=Config(), workdir=tmp_path)
    assert out == tmp_path / "BV1.mp3"
    assert "--audio-format" in captured["cmd"]
    assert "mp3" in captured["cmd"]
    assert "--cookies-from-browser" in captured["cmd"]


def test_download_missing_yt_dlp(monkeypatch, tmp_path):
    monkeypatch.delenv("VTF_YT_DLP", raising=False)
    monkeypatch.setattr("vtf.pipeline.download.shutil.which", lambda _: None)
    with pytest.raises(VtfEnvError):
        download(meta={"video_id": "x", "url": "u", "platform": "youtube"}, cfg=Config(), workdir=tmp_path)


def test_download_propagates_error(monkeypatch, tmp_path):
    monkeypatch.setattr("vtf.pipeline.download.shutil.which", lambda _: "/usr/bin/yt-dlp")

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        return type("R", (), {"returncode": 1, "stdout": "", "stderr": "boom"})()

    monkeypatch.setattr("vtf.pipeline.download.subprocess.run", fake_run)
    with pytest.raises(RemoteError, match="boom"):
        download(
            meta={"video_id": "x", "url": "u", "platform": "youtube"},
            cfg=Config(),
            workdir=tmp_path,
        )
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 写 download.py**

`src/vtf/pipeline/download.py`:

```python
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from vtf.errors import EnvironmentError as VtfEnvError, RemoteError
from vtf.platforms import detect


def download(*, meta: dict[str, Any], cfg: Any, workdir: Path) -> Path:
    yt_dlp = os.environ.get("VTF_YT_DLP") or shutil.which("yt-dlp")
    if not yt_dlp:
        raise VtfEnvError("yt-dlp 未找到。请 `pip install yt-dlp` 或设置 VTF_YT_DLP")
    workdir.mkdir(parents=True, exist_ok=True)
    out_path = workdir / f"{meta['video_id']}.{cfg.download.audio_format}"
    platform = detect(meta["url"])
    cmd = [
        yt_dlp,
        "--retries",
        str(cfg.download.retries),
        "--fragment-retries",
        str(cfg.download.retries),
        "-f",
        "bestaudio",
        "-x",
        "--audio-format",
        cfg.download.audio_format,
        "--audio-quality",
        cfg.download.audio_quality,
        "-o",
        str(out_path),
        *platform.cookie_args(cfg),
        meta["url"],
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RemoteError(f"yt-dlp 下载失败({r.returncode}):{r.stderr.strip()[:200]}")
    return out_path
```

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/test_download.py -v
```

预期:PASS。

- [ ] **Step 5: 提交**

```bash
git add src/vtf/pipeline/download.py tests/test_download.py
git commit -m "feat: download 步骤"
```

### Task 4.7: transcribe 模块(FunASR Python 探测 + 子进程)

**Files:**
- Create: `src/vtf/transcribe/__init__.py`
- Create: `src/vtf/transcribe/funasr.py`
- Create: `tests/test_transcribe.py`

- [ ] **Step 1: 写测试**

`tests/test_transcribe.py`:

```python
import json
from pathlib import Path

import pytest

from vtf.config import Config
from vtf.errors import EnvironmentError as VtfEnvError
from vtf.transcribe.funasr import find_funasr_python, transcribe


def test_find_uses_env_first(monkeypatch, tmp_path):
    py = tmp_path / "py"
    py.write_text("", encoding="utf-8")
    monkeypatch.setenv("VTF_TRANSCRIBE_FUNASR_PYTHON", str(py))

    def fake_run(cmd, capture_output, timeout):  # noqa: ARG001
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr("vtf.transcribe.funasr.subprocess.run", fake_run)
    assert find_funasr_python(Config()) == str(py)


def test_find_falls_back_to_path(monkeypatch):
    monkeypatch.delenv("VTF_TRANSCRIBE_FUNASR_PYTHON", raising=False)
    monkeypatch.setattr("vtf.transcribe.funasr.shutil.which", lambda x: f"/bin/{x}" if x == "python3" else None)

    def fake_run(cmd, capture_output, timeout):  # noqa: ARG001
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr("vtf.transcribe.funasr.subprocess.run", fake_run)
    cfg = Config()
    cfg.transcribe.funasr_python = ""
    assert find_funasr_python(cfg) == "/bin/python3"


def test_find_returns_none_when_nothing_works(monkeypatch):
    monkeypatch.delenv("VTF_TRANSCRIBE_FUNASR_PYTHON", raising=False)
    monkeypatch.setattr("vtf.transcribe.funasr.shutil.which", lambda x: None)
    assert find_funasr_python(Config()) is None


def test_transcribe_extracts_marked_json(monkeypatch, tmp_path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"\x00")

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        out = (
            "[funasr] loading models...\n"
            "TRANSCRIPT_JSON_START\n"
            + json.dumps(["你好", "世界"], ensure_ascii=False)
            + "\nTRANSCRIPT_JSON_END\n"
        )
        return type("R", (), {"returncode": 0, "stdout": out, "stderr": ""})()

    monkeypatch.setattr("vtf.transcribe.funasr.subprocess.run", fake_run)
    monkeypatch.setattr("vtf.transcribe.funasr.find_funasr_python", lambda _cfg: "/usr/bin/python3")
    out = transcribe(audio_path=audio, cfg=Config())
    assert out["sentences"] == ["你好", "世界"]
    assert out["asr_model"] == "paraformer-zh"


def test_transcribe_missing_funasr(monkeypatch, tmp_path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"\x00")
    monkeypatch.setattr("vtf.transcribe.funasr.find_funasr_python", lambda _cfg: None)
    with pytest.raises(VtfEnvError):
        transcribe(audio_path=audio, cfg=Config())
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 写 funasr.py**

`src/vtf/transcribe/funasr.py`:

```python
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from vtf.errors import EnvironmentError as VtfEnvError, RemoteError

_TRANSCRIBE_TEMPLATE = r'''
import json, os
from funasr import AutoModel

with open({corr_path!r}) as f:
    corrections = json.load(f)

model = AutoModel(
    model={asr_model!r},
    vad_model={vad_model!r},
    punc_model={punc_model!r},
    disable_update=True,
)
result = model.generate(
    input={audio!r},
    batch_size_s={batch_size_s},
    sentence_timestamp=True,
)

sentences = []
for res in result:
    if "sentence_info" in res:
        for s in res["sentence_info"]:
            text = s["text"].strip()
            if text:
                sentences.append(text)

for i, s in enumerate(sentences):
    for wrong, right in corrections.items():
        sentences[i] = sentences[i].replace(wrong, right)

print("TRANSCRIPT_JSON_START")
print(json.dumps(sentences, ensure_ascii=False))
print("TRANSCRIPT_JSON_END")
'''


def find_funasr_python(cfg: Any) -> str | None:
    candidates: list[str] = []
    env_py = os.environ.get("VTF_TRANSCRIBE_FUNASR_PYTHON") or cfg.transcribe.funasr_python
    if env_py:
        candidates.append(env_py)
    candidates += [shutil.which("funasr") or "", shutil.which("python3") or "", shutil.which("python") or ""]
    for c in candidates:
        if not c:
            continue
        try:
            r = subprocess.run([c, "-c", "import funasr"], capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0:
            return c
    return None


def transcribe(*, audio_path: Path, cfg: Any) -> dict[str, Any]:
    py = find_funasr_python(cfg)
    if not py:
        raise VtfEnvError(
            "FunASR 未找到。请在某个 Python 环境中 `pip install funasr`,"
            "并通过 VTF_TRANSCRIBE_FUNASR_PYTHON 指向它"
        )
    corrections: dict[str, str] = {}
    if cfg.transcribe.corrections_file:
        try:
            with open(cfg.transcribe.corrections_file, encoding="utf-8") as f:
                corrections = json.load(f)
        except FileNotFoundError:
            pass
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(corrections, f, ensure_ascii=False)
        corr_path = f.name
    try:
        code = _TRANSCRIBE_TEMPLATE.format(
            corr_path=corr_path,
            asr_model=cfg.transcribe.asr_model,
            vad_model=cfg.transcribe.vad_model,
            punc_model=cfg.transcribe.punc_model,
            audio=str(audio_path),
            batch_size_s=cfg.transcribe.batch_size_s,
        )
        r = subprocess.run(
            [py, "-c", code], capture_output=True, text=True, timeout=1800
        )
    finally:
        try:
            os.unlink(corr_path)
        except OSError:
            pass
    if r.returncode != 0:
        raise RemoteError(f"FunASR 转录失败({r.returncode}):{r.stderr.strip()[:300]}")
    sentences = _extract_marked_json(r.stdout)
    return {
        "audio_path": str(audio_path),
        "asr_model": cfg.transcribe.asr_model,
        "sentences": sentences,
    }


def _extract_marked_json(stdout: str) -> list[str]:
    start = stdout.find("TRANSCRIPT_JSON_START")
    end = stdout.find("TRANSCRIPT_JSON_END")
    if start >= 0 and end >= 0:
        body = stdout[start + len("TRANSCRIPT_JSON_START") : end].strip()
        return list(json.loads(body))
    return list(json.loads(stdout.strip()))


__all__ = ["find_funasr_python", "transcribe"]
```

`src/vtf/transcribe/__init__.py`:

```python
from vtf.transcribe.funasr import find_funasr_python, transcribe

__all__ = ["find_funasr_python", "transcribe"]
```

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/test_transcribe.py -v
```

预期:PASS。

- [ ] **Step 5: 提交**

```bash
git add src/vtf/transcribe tests/test_transcribe.py
git commit -m "feat: FunASR 转录封装与 Python 路径探测"
```

---

## Stage 5 — Sinks

### Task 5.1: schema 路径解析与 transformer

**Files:**
- Create: `src/vtf/sinks/__init__.py`
- Create: `src/vtf/sinks/base.py`
- Create: `src/vtf/sinks/schema.py`
- Create: `tests/test_sink_schema.py`

- [ ] **Step 1: 写测试**

`tests/test_sink_schema.py`:

```python
import pytest

from vtf.sinks.schema import render_field, resolve_path

RESULT = {
    "meta": {"url": "https://x", "title": "T"},
    "lines": ["a", "b"],
    "analyses": {
        "summary": {"text": "S", "tags": ["#x", "#y"]},
        "rewrite": {"text": "R1\nR2"},
    },
}


def test_resolve_basic():
    assert resolve_path(RESULT, "meta.url") == "https://x"
    assert resolve_path(RESULT, "analyses.summary.text") == "S"


def test_resolve_missing_returns_none():
    assert resolve_path(RESULT, "analyses.breakdown.text") is None
    assert resolve_path(RESULT, "x.y.z") is None


def test_render_field_joined():
    assert render_field(RESULT, "lines | joined") == "a\nb"


def test_render_field_tags_hashtag():
    assert render_field(RESULT, "analyses.summary.tags | tags_hashtag") == "#x #y"


def test_render_field_stats_compact():
    r = {"meta": {"view": 100, "like": 5, "favorite": 0, "share": 0, "reply": 1}}
    assert (
        render_field(r, "meta | stats_compact")
        == "播放100 | 点赞5 | 收藏0 | 分享0 | 评论1"
    )


def test_render_field_unknown_transformer_raises():
    from vtf.errors import UserError

    with pytest.raises(UserError, match="transformer"):
        render_field(RESULT, "lines | nonsense")
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 写 sinks/base.py**

`src/vtf/sinks/base.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class EmitOutcome:
    sink: str
    degraded: bool = False
    reason: str = ""


class Sink(Protocol):
    name: str

    def available(self, cfg: Any) -> tuple[bool, str]: ...
    def emit(self, result: dict[str, Any], cfg: Any) -> EmitOutcome: ...
```

- [ ] **Step 4: 写 sinks/schema.py**

`src/vtf/sinks/schema.py`:

```python
from __future__ import annotations

from typing import Any

from vtf.errors import UserError


def resolve_path(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def render_field(data: dict[str, Any], expr: str) -> Any:
    if "|" in expr:
        left, right = (s.strip() for s in expr.split("|", 1))
        value = resolve_path(data, left)
        return _apply_transformer(value, right)
    return resolve_path(data, expr)


def _apply_transformer(value: Any, name: str) -> Any:
    if name == "joined":
        if not isinstance(value, list):
            return ""
        return "\n".join(str(x) for x in value)
    if name == "tags_hashtag":
        if not isinstance(value, list):
            return ""
        return " ".join(str(x) for x in value)
    if name == "stats_compact":
        if not isinstance(value, dict):
            return ""
        return (
            f"播放{value.get('view', 0)} | 点赞{value.get('like', 0)} | "
            f"收藏{value.get('favorite', 0)} | 分享{value.get('share', 0)} | "
            f"评论{value.get('reply', 0)}"
        )
    raise UserError(f"unknown transformer: {name!r}; "
                    f"allowed: joined, tags_hashtag, stats_compact")
```

- [ ] **Step 5: 写 sinks/__init__.py**

`src/vtf/sinks/__init__.py`:

```python
from __future__ import annotations

from vtf.errors import UserError
from vtf.sinks.base import EmitOutcome, Sink
from vtf.sinks.feishu import Feishu
from vtf.sinks.markdown import Markdown


def get(name: str) -> Sink:
    for s in (Markdown(), Feishu()):
        if s.name == name:
            return s
    raise UserError(f"unknown sink: {name!r}; allowed: markdown, feishu")


__all__ = ["EmitOutcome", "Sink", "get"]
```

- [ ] **Step 6: 跑测试**

```bash
uv run pytest tests/test_sink_schema.py -v
```

预期:PASS。

- [ ] **Step 7: 提交**

```bash
git add src/vtf/sinks tests/test_sink_schema.py
git commit -m "feat: sink schema 路径解析与 transformer"
```

### Task 5.2: markdown sink

**Files:**
- Create: `src/vtf/sinks/markdown.py`
- Create: `tests/test_sink_markdown.py`

- [ ] **Step 1: 写测试**

`tests/test_sink_markdown.py`:

```python
import io

from vtf.config import Config
from vtf.sinks.markdown import Markdown, render_markdown

SAMPLE = {
    "meta": {
        "platform": "bilibili",
        "title": "T",
        "author": "A",
        "url": "u",
        "duration_str": "10:00",
        "upload_date": "2026-04-01 12:00",
        "view": 100,
        "like": 5,
        "favorite": 0,
        "share": 0,
        "reply": 1,
    },
    "lines": ["第一行", "第二行"],
    "analyses": {
        "summary": {"text": "总结", "tags": ["#x", "#y"]},
        "breakdown": {"text": "拆解"},
    },
}


def test_render_includes_basics():
    md = render_markdown(SAMPLE)
    assert "T" in md
    assert "A" in md
    assert "10:00" in md
    assert "第一行" in md
    assert "第二行" in md
    assert "总结" in md
    assert "拆解" in md
    assert "#x #y" in md


def test_render_skips_missing_analysis():
    data = {**SAMPLE, "analyses": {"summary": {"text": "S"}}}
    md = render_markdown(data)
    assert "二创改写" not in md


def test_emit_writes_to_stdout(capsys):
    Markdown().emit(SAMPLE, Config())
    out = capsys.readouterr().out
    assert "第一行" in out


def test_available_always_true():
    ok, _ = Markdown().available(Config())
    assert ok is True
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 写 markdown.py**

`src/vtf/sinks/markdown.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from jinja2 import Template

from vtf.sinks.base import EmitOutcome


_BUILTIN_TEMPLATE = """\
# 🎬 视频分析报告

## 基本信息

| 字段 | 内容 |
|------|------|
| **标题** | {{ meta.title }} |
| **作者** | {{ meta.author }} |
| **平台** | {{ meta.platform }} |
| **时长** | {{ meta.duration_str }} |
| **发布时间** | {{ meta.upload_date }} |
| **链接** | {{ meta.url }} |

## 数据

- 播放数:{{ meta.view }}
- 点赞数:{{ meta.like }}
- 收藏数:{{ meta.favorite }}
- 分享数:{{ meta.share }}
- 评论数:{{ meta.reply }}

---

## 📝 文案提取({{ lines | length }} 行)

{% for line in lines %}{{ line }}
{% endfor %}
{% if analyses.rewrite %}
---

## ✍️ 二创改写

{{ analyses.rewrite.text }}
{% endif %}
{% if analyses.summary %}
---

## 📊 摘要

{{ analyses.summary.text }}

{% if analyses.summary.tags %}**标签:** {{ analyses.summary.tags | join(' ') }}
{% endif %}
{% endif %}
{% if analyses.breakdown %}
---

## 🔍 视频拆解

{{ analyses.breakdown.text }}
{% endif %}
"""


def render_markdown(result: dict[str, Any], template_path: str = "") -> str:
    src = Path(template_path).read_text("utf-8") if template_path else _BUILTIN_TEMPLATE
    return Template(src, autoescape=False).render(**result)


class Markdown:
    name = "markdown"

    def available(self, cfg: Any) -> tuple[bool, str]:
        return True, ""

    def emit(self, result: dict[str, Any], cfg: Any) -> EmitOutcome:
        text = render_markdown(result, cfg.sink.markdown.template)
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return EmitOutcome(sink="markdown")


__all__ = ["Markdown", "render_markdown"]
```

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/test_sink_markdown.py -v
```

预期:PASS。

- [ ] **Step 5: 提交**

```bash
git add src/vtf/sinks/markdown.py tests/test_sink_markdown.py
git commit -m "feat: markdown sink"
```

### Task 5.3: feishu sink(成功路径)

**Files:**
- Create: `src/vtf/sinks/feishu.py`
- Create: `tests/test_sink_feishu.py`
- Create: `tests/fixtures/schema_minimal.toml`

- [ ] **Step 1: 写 fixture**

`tests/fixtures/schema_minimal.toml`:

```toml
[[fields]]
name = "对标素材链接"
type = "text"
source = "meta.url"

[[fields]]
name = "标题"
type = "text"
source = "meta.title"

[[fields]]
name = "文案提取"
type = "text"
source = "lines | joined"

[[fields]]
name = "标签"
type = "text"
source = "analyses.summary.tags | tags_hashtag"

[[fields]]
name = "发布时间"
type = "datetime"
source = "meta.upload_date"
```

- [ ] **Step 2: 写测试**

`tests/test_sink_feishu.py`:

```python
import json
from pathlib import Path

import pytest

from vtf.config import Config
from vtf.errors import UserError
from vtf.sinks.feishu import Feishu


FIX = Path(__file__).parent / "fixtures"

SAMPLE = {
    "meta": {
        "url": "https://example",
        "title": "T",
        "upload_date": "2026-04-01 12:00",
    },
    "lines": ["L1", "L2"],
    "analyses": {"summary": {"tags": ["#a", "#b"]}},
}


def _cfg_with_schema(schema_path: str) -> Config:
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "tbl"
    cfg.sink.feishu.schema = schema_path
    return cfg


def test_available_requires_all_fields():
    ok, reason = Feishu().available(Config())
    assert ok is False
    assert "schema" in reason or "base_token" in reason or "table_id" in reason


def test_available_ok_when_configured():
    cfg = _cfg_with_schema(str(FIX / "schema_minimal.toml"))
    ok, _ = Feishu().available(cfg)
    assert ok is True


def test_emit_calls_lark_cli(monkeypatch, tmp_path):
    captured: dict = {}

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        captured["cmd"] = cmd
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("vtf.sinks.feishu.subprocess.run", fake_run)
    monkeypatch.setattr("vtf.sinks.feishu.shutil.which", lambda _: "/usr/bin/lark-cli")
    cfg = _cfg_with_schema(str(FIX / "schema_minimal.toml"))
    out = Feishu().emit(SAMPLE, cfg)
    assert out.sink == "feishu"
    assert out.degraded is False
    cmd = captured["cmd"]
    assert "base" in cmd and "+record-batch-create" in cmd
    payload_idx = cmd.index("--json") + 1
    payload = json.loads(cmd[payload_idx])
    fields = payload["fields"]
    rows = payload["rows"]
    assert "对标素材链接" in fields
    assert rows[0][fields.index("对标素材链接")] == "https://example"
    assert rows[0][fields.index("文案提取")] == "L1\nL2"
    assert rows[0][fields.index("标签")] == "#a #b"


def test_emit_missing_schema_raises():
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "tbl"
    with pytest.raises(UserError, match="schema"):
        Feishu().emit(SAMPLE, cfg)
```

- [ ] **Step 3: 跑测试确认失败**

- [ ] **Step 4: 写 feishu.py**

`src/vtf/sinks/feishu.py`:

```python
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

from vtf.errors import RemoteError, UserError
from vtf.sinks.base import EmitOutcome
from vtf.sinks.schema import render_field


class Feishu:
    name = "feishu"

    def available(self, cfg: Any) -> tuple[bool, str]:
        f = cfg.sink.feishu
        if not f.base_token:
            return False, "缺少 base_token(请跑 `vtf init feishu` 或设置 VTF_SINK_FEISHU_BASE_TOKEN)"
        if not f.table_id:
            return False, "缺少 table_id"
        if not f.schema:
            return False, "缺少 schema 路径(请在 config 设置 sink.feishu.schema)"
        if not Path(f.schema).exists():
            return False, f"schema 文件不存在:{f.schema}"
        return True, ""

    def emit(self, result: dict[str, Any], cfg: Any) -> EmitOutcome:
        ok, reason = self.available(cfg)
        if not ok:
            raise UserError(reason)
        cli_name = os.environ.get("VTF_SINK_FEISHU_LARK_CLI") or cfg.sink.feishu.lark_cli
        cli = shutil.which(cli_name) or cli_name
        if not Path(cli).exists() and shutil.which(cli_name) is None:
            return self._degrade(
                result, reason=f"lark-cli '{cli_name}' 未找到。请安装或设置 VTF_SINK_FEISHU_LARK_CLI"
            )
        schema = self._load_schema(cfg.sink.feishu.schema)
        fields = [f["name"] for f in schema]
        row: list[Any] = []
        for f in schema:
            val = render_field(result, f["source"])
            row.append("" if val is None else val)
        payload = json.dumps({"fields": fields, "rows": [row]}, ensure_ascii=False)
        cmd = [
            cli,
            "base",
            "+record-batch-create",
            "--base-token",
            cfg.sink.feishu.base_token,
            "--table-id",
            cfg.sink.feishu.table_id,
            "--json",
            payload,
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            return self._degrade(result, reason=f"调用 lark-cli 失败:{e}")
        if r.returncode != 0:
            return self._degrade(
                result, reason=f"lark-cli 退出码 {r.returncode}:{r.stderr.strip()[:200]}"
            )
        return EmitOutcome(sink="feishu")

    def _load_schema(self, path: str) -> list[dict[str, Any]]:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        fields = data.get("fields", [])
        if not fields:
            raise UserError(f"schema 文件没有 [[fields]]:{path}")
        return list(fields)

    def _degrade(self, result: dict[str, Any], *, reason: str) -> EmitOutcome:
        from vtf.sinks.markdown import render_markdown

        sys.stdout.write(render_markdown(result))
        if not sys.stdout.closed:
            sys.stdout.write("\n")
        return EmitOutcome(sink="markdown", degraded=True, reason=reason)
```

- [ ] **Step 5: 跑测试**

```bash
uv run pytest tests/test_sink_feishu.py -v
```

预期:`test_available_requires_all_fields`、`test_available_ok_when_configured`、`test_emit_calls_lark_cli`、`test_emit_missing_schema_raises` 全 PASS。

- [ ] **Step 6: 提交**

```bash
git add src/vtf/sinks/feishu.py tests/test_sink_feishu.py tests/fixtures/schema_minimal.toml
git commit -m "feat: feishu sink(成功路径)"
```

### Task 5.4: feishu sink 失败降级

**Files:**
- Modify: `tests/test_sink_feishu.py`

- [ ] **Step 1: 添加测试**

```python
def test_emit_lark_cli_missing_falls_back_to_markdown(monkeypatch, capsys):
    monkeypatch.setattr("vtf.sinks.feishu.shutil.which", lambda _: None)
    cfg = _cfg_with_schema(str(FIX / "schema_minimal.toml"))
    cfg.sink.feishu.lark_cli = "no-such-cli"
    out = Feishu().emit(SAMPLE, cfg)
    assert out.sink == "markdown"
    assert out.degraded is True
    assert "no-such-cli" in out.reason
    captured = capsys.readouterr().out
    assert "L1" in captured  # markdown 的内容打到了 stdout


def test_emit_lark_cli_failure_falls_back(monkeypatch, capsys):
    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        return type("R", (), {"returncode": 7, "stdout": "", "stderr": "boom"})()

    monkeypatch.setattr("vtf.sinks.feishu.subprocess.run", fake_run)
    monkeypatch.setattr("vtf.sinks.feishu.shutil.which", lambda _: "/usr/bin/lark-cli")
    cfg = _cfg_with_schema(str(FIX / "schema_minimal.toml"))
    out = Feishu().emit(SAMPLE, cfg)
    assert out.sink == "markdown"
    assert out.degraded is True
    assert "boom" in out.reason or "7" in out.reason
    assert "L1" in capsys.readouterr().out
```

- [ ] **Step 2: 跑测试**

```bash
uv run pytest tests/test_sink_feishu.py -v
```

预期:全部 PASS。

- [ ] **Step 3: 提交**

```bash
git add tests/test_sink_feishu.py
git commit -m "test: feishu sink 失败降级"
```

---

## Stage 6 — CLI 顶层与子命令

### Task 6.1: CLI 顶层 group 与全局 flags

**Files:**
- Modify: `src/vtf/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: 写测试**

`tests/test_cli.py`:

```python
from click.testing import CliRunner

from vtf.cli import main


def test_help_lists_subcommands():
    r = CliRunner().invoke(main, ["--help"])
    assert r.exit_code == 0
    for sub in ("run", "fetch", "download", "transcribe", "merge", "analyze",
                "assemble", "emit", "init", "config", "install", "doctor"):
        assert sub in r.output


def test_global_flags_recognized():
    r = CliRunner().invoke(main, ["--json", "--quiet", "--help"])
    assert r.exit_code == 0
```

- [ ] **Step 2: 跑测试确认部分失败(子命令未注册)**

- [ ] **Step 3: 改写 cli.py**

`src/vtf/cli.py`:

```python
from __future__ import annotations

from pathlib import Path

import click

from vtf.commands import (
    analyze as _analyze,
    assemble as _assemble,
    config_cmd as _config_cmd,
    doctor as _doctor,
    download as _download,
    emit as _emit,
    fetch as _fetch,
    init as _init,
    install as _install,
    merge as _merge,
    run as _run,
    transcribe as _transcribe,
)


@click.group()
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None,
              help="覆盖配置文件路径")
@click.option("--workdir", type=click.Path(path_type=Path), default=None,
              help="中间产物目录(默认 $XDG_CACHE_HOME/vtf/)")
@click.option("--json", "json_mode", is_flag=True, help="日志走 JSON Lines 到 stderr")
@click.option("--quiet", is_flag=True, help="仅输出错误")
@click.version_option(package_name="vtf")
@click.pass_context
def main(ctx: click.Context, config_path: Path | None, workdir: Path | None,
         json_mode: bool, quiet: bool) -> None:
    """vtf - 视频内容流水线 CLI"""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    ctx.obj["workdir"] = workdir
    ctx.obj["json_mode"] = json_mode
    ctx.obj["quiet"] = quiet


main.add_command(_run.cmd, name="run")
main.add_command(_fetch.cmd, name="fetch")
main.add_command(_download.cmd, name="download")
main.add_command(_transcribe.cmd, name="transcribe")
main.add_command(_merge.cmd, name="merge")
main.add_command(_analyze.cmd, name="analyze")
main.add_command(_assemble.cmd, name="assemble")
main.add_command(_emit.cmd, name="emit")
main.add_command(_init.cmd, name="init")
main.add_command(_config_cmd.cmd, name="config")
main.add_command(_install.cmd, name="install")
main.add_command(_doctor.cmd, name="doctor")
```

- [ ] **Step 4: 创建 commands/ 占位**

```bash
mkdir -p src/vtf/commands
touch src/vtf/commands/__init__.py
```

为每个子命令文件写最小占位:

`src/vtf/commands/_stub.py`:

```python
import click


def make_stub(name: str) -> click.Command:
    @click.command(name=name, help=f"{name} (待实现)")
    def cmd() -> None:
        click.echo(f"{name} not implemented", err=True)
        raise SystemExit(2)

    return cmd
```

为每个 commands/<name>.py 写:

`src/vtf/commands/run.py`:

```python
from vtf.commands._stub import make_stub

cmd = make_stub("run")
```

(对 fetch / download / transcribe / merge / analyze / assemble / emit / init / config_cmd / install / doctor 重复;`config_cmd.py` 内 `cmd = make_stub("config")`。)

- [ ] **Step 5: 跑测试**

```bash
uv run pytest tests/test_cli.py -v
```

预期:`test_help_lists_subcommands`、`test_global_flags_recognized` PASS。

- [ ] **Step 6: 提交**

```bash
git add src/vtf/cli.py src/vtf/commands
git commit -m "feat: CLI 顶层 group 与子命令占位"
```

### Task 6.2: 配置加载辅助 + 实现 `vtf fetch`

**Files:**
- Modify: `src/vtf/cli.py`
- Modify: `src/vtf/commands/fetch.py`
- Create: `src/vtf/_ctx.py`

- [ ] **Step 1: 写 _ctx.py**

`src/vtf/_ctx.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

import click

from vtf.config import Config, default_user_path, default_workdir, load_config
from vtf.logging import Logger, make_default


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
    return make_default(json_mode=bool(obj.get("json_mode")), quiet=bool(obj.get("quiet")))
```

- [ ] **Step 2: 写 fetch 命令测试**

追加到 `tests/test_cli.py`:

```python
import json as _json


def test_fetch_emits_normalized_meta(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        return type(
            "R",
            (),
            {
                "returncode": 0,
                "stdout": _json.dumps(
                    {
                        "id": "vid",
                        "webpage_url": "https://youtu.be/vid",
                        "title": "Y",
                        "uploader": "U",
                        "upload_date": "20260401",
                        "duration": 60,
                        "view_count": 10,
                        "comment_count": 3,
                    }
                ),
                "stderr": "",
            },
        )()

    monkeypatch.setattr("vtf.pipeline.fetch.subprocess.run", fake_run)
    monkeypatch.setattr("vtf.pipeline.fetch.shutil.which", lambda _: "/usr/bin/yt-dlp")
    r = CliRunner().invoke(main, ["fetch", "https://youtu.be/vid"])
    assert r.exit_code == 0
    out = _json.loads(r.output)
    assert out["platform"] == "youtube"
    assert out["reply"] == 3
```

- [ ] **Step 3: 跑测试确认失败**

- [ ] **Step 4: 实现 fetch 命令**

`src/vtf/commands/fetch.py`:

```python
from __future__ import annotations

import json

import click

from vtf._ctx import get_config, get_logger
from vtf.errors import VtfError
from vtf.pipeline.fetch import fetch


@click.command(name="fetch", help="抓取视频元数据(yt-dlp -J)")
@click.argument("url")
@click.pass_context
def cmd(ctx: click.Context, url: str) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    try:
        meta = fetch(url=url, cfg=cfg)
    except VtfError as e:
        log.error(str(e), step="fetch")
        raise SystemExit(e.exit_code) from e
    click.echo(json.dumps(meta, ensure_ascii=False))
```

- [ ] **Step 5: 跑测试**

```bash
uv run pytest tests/test_cli.py -v
```

预期:fetch 测试 PASS。

- [ ] **Step 6: 提交**

```bash
git add src/vtf/_ctx.py src/vtf/commands/fetch.py tests/test_cli.py
git commit -m "feat: CLI fetch 子命令"
```

### Task 6.3: 实现 download / transcribe / merge 子命令

**Files:**
- Modify: `src/vtf/commands/download.py`
- Modify: `src/vtf/commands/transcribe.py`
- Modify: `src/vtf/commands/merge.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 写测试(三个子命令各一)**

追加到 `tests/test_cli.py`:

```python
def test_download_reads_meta_from_file(tmp_path, monkeypatch):
    meta = {"platform": "youtube", "video_id": "vid", "url": "https://youtu.be/vid"}
    meta_file = tmp_path / "m.json"
    meta_file.write_text(_json.dumps(meta), encoding="utf-8")

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        out = tmp_path / "vid.mp3"
        out.write_bytes(b"\x00")
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("vtf.pipeline.download.subprocess.run", fake_run)
    monkeypatch.setattr("vtf.pipeline.download.shutil.which", lambda _: "/usr/bin/yt-dlp")
    r = CliRunner().invoke(
        main, ["--workdir", str(tmp_path), "download", "--meta", str(meta_file)]
    )
    assert r.exit_code == 0
    assert r.output.strip().endswith("vid.mp3")


def test_merge_reads_stdin_writes_stdout():
    payload = _json.dumps({"sentences": ["你好。", "世界"]})
    r = CliRunner().invoke(main, ["merge"], input=payload)
    assert r.exit_code == 0
    out = _json.loads(r.output)
    assert out["lines"] == ["你好。", "世界"]


def test_transcribe_emits_transcript(tmp_path, monkeypatch):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"\x00")

    def fake_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        return type(
            "R",
            (),
            {
                "returncode": 0,
                "stdout": "TRANSCRIPT_JSON_START\n"
                + _json.dumps(["第一句", "第二句"], ensure_ascii=False)
                + "\nTRANSCRIPT_JSON_END\n",
                "stderr": "",
            },
        )()

    monkeypatch.setattr("vtf.transcribe.funasr.subprocess.run", fake_run)
    monkeypatch.setattr("vtf.transcribe.funasr.find_funasr_python", lambda _cfg: "/bin/python")
    r = CliRunner().invoke(main, ["transcribe", str(audio)])
    assert r.exit_code == 0
    out = _json.loads(r.output)
    assert out["sentences"] == ["第一句", "第二句"]
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现 download 子命令**

`src/vtf/commands/download.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import click

from vtf._ctx import get_config, get_logger, get_workdir
from vtf.errors import VtfError
from vtf.pipeline.download import download


@click.command(name="download", help="下载视频音频")
@click.option("--meta", "meta_path", type=click.Path(path_type=Path, exists=True), required=True)
@click.pass_context
def cmd(ctx: click.Context, meta_path: Path) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    meta = json.loads(meta_path.read_text("utf-8"))
    try:
        out = download(meta=meta, cfg=cfg, workdir=get_workdir(ctx))
    except VtfError as e:
        log.error(str(e), step="download")
        raise SystemExit(e.exit_code) from e
    click.echo(str(out))
```

- [ ] **Step 4: 实现 transcribe 子命令**

`src/vtf/commands/transcribe.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import click

from vtf._ctx import get_config, get_logger
from vtf.errors import VtfError
from vtf.transcribe import transcribe


@click.command(name="transcribe", help="FunASR 转录音频")
@click.argument("audio", type=click.Path(path_type=Path, exists=True))
@click.pass_context
def cmd(ctx: click.Context, audio: Path) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    try:
        out = transcribe(audio_path=audio, cfg=cfg)
    except VtfError as e:
        log.error(str(e), step="transcribe")
        raise SystemExit(e.exit_code) from e
    click.echo(json.dumps(out, ensure_ascii=False))
```

- [ ] **Step 5: 实现 merge 子命令**

`src/vtf/commands/merge.py`:

```python
from __future__ import annotations

import json
import sys

import click

from vtf.pipeline.merge import merge_into_lines


@click.command(name="merge", help="合并 transcript 句子为字幕行(stdin → stdout)")
def cmd() -> None:
    data = json.load(sys.stdin)
    sentences = data.get("sentences", [])
    lines = merge_into_lines(sentences)
    click.echo(json.dumps({"lines": lines}, ensure_ascii=False))
```

- [ ] **Step 6: 跑测试**

```bash
uv run pytest tests/test_cli.py -v
```

预期:三个新测试 PASS。

- [ ] **Step 7: 提交**

```bash
git add src/vtf/commands tests/test_cli.py
git commit -m "feat: CLI download / transcribe / merge 子命令"
```

### Task 6.4: 实现 analyze / assemble / emit 子命令

**Files:**
- Modify: `src/vtf/commands/analyze.py`
- Modify: `src/vtf/commands/assemble.py`
- Modify: `src/vtf/commands/emit.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 写测试**

```python
def test_analyze_summary_via_stdin():
    meta_file_payload = {"meta": {"title": "T", "author": "A", "platform": "bilibili"},
                         "lines": ["a", "b"]}
    r = CliRunner().invoke(main, ["analyze", "--kind", "summary"],
                           input=_json.dumps(meta_file_payload, ensure_ascii=False))
    assert r.exit_code == 0
    out = _json.loads(r.output)
    assert out["kind"] == "summary"
    assert "T" in out["prompt"]


def test_assemble_combines_files(tmp_path):
    meta_p = tmp_path / "meta.json"
    meta_p.write_text(_json.dumps({"title": "T"}), encoding="utf-8")
    lines_p = tmp_path / "lines.json"
    lines_p.write_text(_json.dumps({"lines": ["a"]}), encoding="utf-8")
    a_p = tmp_path / "a.json"
    a_p.write_text(_json.dumps({"kind": "summary", "result": {"text": "S"}}), encoding="utf-8")
    r = CliRunner().invoke(
        main,
        ["assemble", "--meta", str(meta_p), "--lines", str(lines_p), "--analysis", str(a_p)],
    )
    assert r.exit_code == 0
    out = _json.loads(r.output)
    assert out["meta"]["title"] == "T"
    assert out["analyses"]["summary"]["text"] == "S"


def test_emit_markdown_via_stdin():
    payload = _json.dumps({
        "meta": {"title": "T", "author": "A", "platform": "yt", "url": "u",
                 "duration_str": "1:00", "upload_date": "", "view": 0, "like": 0,
                 "favorite": 0, "share": 0, "reply": 0},
        "lines": ["x"],
        "analyses": {},
    }, ensure_ascii=False)
    r = CliRunner().invoke(main, ["emit", "--sink", "markdown"], input=payload)
    assert r.exit_code == 0
    assert "x" in r.output
```

- [ ] **Step 2: 实现 analyze 子命令**

`src/vtf/commands/analyze.py`:

```python
from __future__ import annotations

import json
import sys

import click

from vtf._ctx import get_config, get_logger
from vtf.errors import VtfError
from vtf.pipeline.analyze import analyze


@click.command(name="analyze", help="为某种 kind 生成 LLM prompt(stdin: {meta, lines})")
@click.option("--kind", required=True, type=click.Choice(["summary", "breakdown", "rewrite"]))
@click.pass_context
def cmd(ctx: click.Context, kind: str) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    payload = json.load(sys.stdin)
    try:
        out = analyze(
            kind=kind,
            meta=payload.get("meta", {}),
            lines=payload.get("lines", []),
            cfg=cfg,
        )
    except VtfError as e:
        log.error(str(e), step="analyze")
        raise SystemExit(e.exit_code) from e
    click.echo(json.dumps(out, ensure_ascii=False))
```

- [ ] **Step 3: 实现 assemble 子命令**

`src/vtf/commands/assemble.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import click

from vtf._ctx import get_logger
from vtf.errors import VtfError
from vtf.pipeline.assemble import assemble


@click.command(name="assemble", help="拼装最终 result.json")
@click.option("--meta", "meta_path", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--lines", "lines_path", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--analysis", "analyses", multiple=True, type=click.Path(path_type=Path, exists=True))
@click.pass_context
def cmd(ctx: click.Context, meta_path: Path, lines_path: Path, analyses: tuple[Path, ...]) -> None:
    log = get_logger(ctx)
    meta = json.loads(meta_path.read_text("utf-8"))
    lines_data = json.loads(lines_path.read_text("utf-8"))
    items = [json.loads(p.read_text("utf-8")) for p in analyses]
    try:
        out = assemble(meta=meta, lines=lines_data["lines"], analyses=items)
    except VtfError as e:
        log.error(str(e), step="assemble")
        raise SystemExit(e.exit_code) from e
    click.echo(json.dumps(out, ensure_ascii=False))
```

- [ ] **Step 4: 实现 emit 子命令**

`src/vtf/commands/emit.py`:

```python
from __future__ import annotations

import json
import sys

import click

from vtf._ctx import get_config, get_logger
from vtf.errors import VtfError
from vtf.sinks import get as get_sink


@click.command(name="emit", help="把 result.json 落到当前 sink(stdin)")
@click.option("--sink", "sink_name", default="", help="临时覆盖 sink:markdown / feishu")
@click.pass_context
def cmd(ctx: click.Context, sink_name: str) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    name = sink_name or cfg.output.sink
    result = json.load(sys.stdin)
    try:
        sink = get_sink(name)
        outcome = sink.emit(result, cfg)
    except VtfError as e:
        log.error(str(e), step="emit")
        raise SystemExit(e.exit_code) from e
    if outcome.degraded:
        log.warn("feishu degraded", step="emit", data={"reason": outcome.reason})
```

- [ ] **Step 5: 跑测试**

```bash
uv run pytest tests/test_cli.py -v
```

预期:三个新测试 PASS。

- [ ] **Step 6: 提交**

```bash
git add src/vtf/commands tests/test_cli.py
git commit -m "feat: CLI analyze / assemble / emit 子命令"
```

### Task 6.5: 实现 `vtf run`(端到端)

**Files:**
- Modify: `src/vtf/commands/run.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 写测试**

```python
def test_run_end_to_end_markdown(tmp_path, monkeypatch):
    audio = tmp_path / "vid.mp3"

    def fake_yt_dlp_run(cmd, capture_output, text, timeout):  # noqa: ARG001
        if "-J" in cmd:
            return type(
                "R",
                (),
                {
                    "returncode": 0,
                    "stdout": _json.dumps(
                        {
                            "id": "vid",
                            "webpage_url": "https://youtu.be/vid",
                            "title": "T",
                            "uploader": "U",
                            "upload_date": "20260401",
                            "duration": 60,
                            "view_count": 10,
                            "comment_count": 3,
                        }
                    ),
                    "stderr": "",
                },
            )()
        audio.write_bytes(b"\x00")
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    def fake_funasr(cmd, capture_output, text, timeout):  # noqa: ARG001
        return type(
            "R",
            (),
            {
                "returncode": 0,
                "stdout": "TRANSCRIPT_JSON_START\n"
                + _json.dumps(["你好。", "世界"], ensure_ascii=False)
                + "\nTRANSCRIPT_JSON_END\n",
                "stderr": "",
            },
        )()

    monkeypatch.setattr("vtf.pipeline.fetch.subprocess.run", fake_yt_dlp_run)
    monkeypatch.setattr("vtf.pipeline.download.subprocess.run", fake_yt_dlp_run)
    monkeypatch.setattr("vtf.pipeline.fetch.shutil.which", lambda _: "/usr/bin/yt-dlp")
    monkeypatch.setattr("vtf.pipeline.download.shutil.which", lambda _: "/usr/bin/yt-dlp")
    monkeypatch.setattr("vtf.transcribe.funasr.subprocess.run", fake_funasr)
    monkeypatch.setattr("vtf.transcribe.funasr.find_funasr_python", lambda _cfg: "/bin/python")
    r = CliRunner().invoke(
        main,
        ["--workdir", str(tmp_path), "run", "https://youtu.be/vid",
         "--sink", "markdown", "--skip", "summary", "--skip", "breakdown", "--skip", "rewrite"],
    )
    assert r.exit_code == 0, r.output
    assert "T" in r.output
    assert "你好。" in r.output
```

- [ ] **Step 2: 实现 run 命令**

`src/vtf/commands/run.py`:

```python
from __future__ import annotations

import json

import click

from vtf._ctx import get_config, get_logger, get_workdir
from vtf.errors import VtfError
from vtf.pipeline.analyze import analyze
from vtf.pipeline.assemble import assemble
from vtf.pipeline.download import download
from vtf.pipeline.fetch import fetch
from vtf.pipeline.merge import merge_into_lines
from vtf.sinks import get as get_sink
from vtf.transcribe import transcribe

_ALL_KINDS = ["summary", "breakdown", "rewrite"]


@click.command(name="run", help="端到端流水线:URL → 落 sink")
@click.argument("url")
@click.option("--sink", "sink_name", default="", help="临时覆盖 sink")
@click.option("--skip", "skips", multiple=True, type=click.Choice(_ALL_KINDS),
              help="跳过某个 analyze kind(可重复)")
@click.option("--resume", is_flag=True, help="复用 workdir 中已有产物(暂未实现细节,等价于不强制清理)")
@click.pass_context
def cmd(ctx: click.Context, url: str, sink_name: str, skips: tuple[str, ...], resume: bool) -> None:
    cfg = get_config(ctx)
    log = get_logger(ctx)
    workdir = get_workdir(ctx)
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        log.info("fetch", step="run")
        meta = fetch(url=url, cfg=cfg)
        (workdir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), "utf-8")
        log.info("download", step="run")
        audio = download(meta=meta, cfg=cfg, workdir=workdir)
        log.info("transcribe", step="run")
        transcript = transcribe(audio_path=audio, cfg=cfg)
        log.info("merge", step="run")
        lines = merge_into_lines(transcript["sentences"])
        analyses_out: list[dict] = []
        for kind in _ALL_KINDS:
            if kind in skips:
                continue
            log.info("analyze", step="run", data={"kind": kind})
            ana = analyze(kind=kind, meta=meta, lines=lines, cfg=cfg)
            ana["result"] = ana["result"] or _placeholder_result(kind)
            analyses_out.append(ana)
        log.info("assemble", step="run")
        result = assemble(meta=meta, lines=lines, analyses=analyses_out)
        name = sink_name or cfg.output.sink
        sink = get_sink(name)
        ok, reason = sink.available(cfg)
        if not ok and name == "feishu":
            log.warn("feishu unavailable, fall back to markdown",
                     step="run", data={"reason": reason})
            sink = get_sink("markdown")
        outcome = sink.emit(result, cfg)
        if outcome.degraded:
            log.warn("feishu degraded", step="run", data={"reason": outcome.reason})
    except VtfError as e:
        log.error(str(e), step="run")
        raise SystemExit(e.exit_code) from e


def _placeholder_result(kind: str) -> dict:
    """run 自身不调 LLM。当 agent 直接 `vtf run` 时,result 缺失,这里给一个空骨架,
    告知用户:要拿到真正的 LLM 输出,请用分步流程并由 agent 回填 result。"""
    if kind == "rewrite":
        return {"text": "(未执行 LLM:请用分步命令并由 agent 填充 result)"}
    if kind == "breakdown":
        return {"text": "(未执行 LLM)"}
    return {"text": "(未执行 LLM)", "points": [], "tags": []}
```

(注意:`_placeholder_result` 显式说明 `run` 端到端不调 LLM,提示用户分步流程才是 analyze 的正解。这与 spec §4.2 一致。)

- [ ] **Step 3: 跑测试**

```bash
uv run pytest tests/test_cli.py -v
```

预期:`test_run_end_to_end_markdown` PASS。

- [ ] **Step 4: 提交**

```bash
git add src/vtf/commands/run.py tests/test_cli.py
git commit -m "feat: CLI run 端到端命令"
```

---

## Stage 7 — 管理命令

### Task 7.1: `vtf doctor`

**Files:**
- Create: `src/vtf/doctor.py`
- Modify: `src/vtf/commands/doctor.py`
- Create: `tests/test_doctor.py`

- [ ] **Step 1: 写测试**

`tests/test_doctor.py`:

```python
from click.testing import CliRunner

from vtf.cli import main
from vtf.doctor import check_yt_dlp, check_funasr, check_lark_cli


def test_check_yt_dlp_present(monkeypatch):
    monkeypatch.setattr("vtf.doctor.shutil.which", lambda _: "/usr/bin/yt-dlp")
    ok, msg = check_yt_dlp()
    assert ok is True
    assert "yt-dlp" in msg


def test_check_yt_dlp_missing(monkeypatch):
    monkeypatch.setattr("vtf.doctor.shutil.which", lambda _: None)
    ok, msg = check_yt_dlp()
    assert ok is False
    assert "pip install yt-dlp" in msg


def test_check_funasr_present(monkeypatch):
    from vtf.config import Config
    monkeypatch.setattr("vtf.doctor.find_funasr_python", lambda _cfg: "/bin/python")
    ok, msg = check_funasr(Config())
    assert ok is True


def test_doctor_command_runs():
    r = CliRunner().invoke(main, ["doctor"])
    assert r.exit_code in (0, 2)
    assert "yt-dlp" in r.output or "FunASR" in r.output or "lark" in r.output
```

- [ ] **Step 2: 写 doctor.py**

`src/vtf/doctor.py`:

```python
from __future__ import annotations

import os
import shutil
from typing import Any

from vtf.transcribe.funasr import find_funasr_python


def check_yt_dlp() -> tuple[bool, str]:
    p = os.environ.get("VTF_YT_DLP") or shutil.which("yt-dlp")
    if p:
        return True, f"yt-dlp 就绪:{p}"
    return False, "yt-dlp 未找到。修复:`pip install yt-dlp`,或设置 VTF_YT_DLP"


def check_funasr(cfg: Any) -> tuple[bool, str]:
    py = find_funasr_python(cfg)
    if py:
        return True, f"FunASR 就绪(Python:{py})"
    return False, ("FunASR 未找到。修复:在某个 Python 中 `pip install funasr`,"
                   "并通过 VTF_TRANSCRIBE_FUNASR_PYTHON 指向它")


def check_lark_cli(cfg: Any) -> tuple[bool, str]:
    name = os.environ.get("VTF_SINK_FEISHU_LARK_CLI") or cfg.sink.feishu.lark_cli
    p = shutil.which(name)
    if p:
        return True, f"lark-cli 就绪:{p}(命令名:{name})"
    return False, (f"lark-cli '{name}' 未找到(仅写飞书时需要)。修复:安装对应 CLI 或"
                   f"设置 VTF_SINK_FEISHU_LARK_CLI 指向你的命令")


def run_all(cfg: Any) -> list[tuple[str, bool, str]]:
    return [
        ("yt-dlp", *check_yt_dlp()),
        ("FunASR", *check_funasr(cfg)),
        ("lark-cli", *check_lark_cli(cfg)),
    ]
```

- [ ] **Step 3: 实现 doctor 命令**

`src/vtf/commands/doctor.py`:

```python
from __future__ import annotations

import click

from vtf._ctx import get_config
from vtf.doctor import run_all


@click.command(name="doctor", help="检查 vtf 依赖环境")
@click.pass_context
def cmd(ctx: click.Context) -> None:
    cfg = get_config(ctx)
    failed = 0
    for name, ok, msg in run_all(cfg):
        marker = "✓" if ok else "✗"
        click.echo(f"{marker} {name}: {msg}")
        if not ok:
            failed += 1
    if failed:
        raise SystemExit(2)
```

- [ ] **Step 4: 跑测试**

```bash
uv run pytest tests/test_doctor.py -v
```

预期:全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add src/vtf/doctor.py src/vtf/commands/doctor.py tests/test_doctor.py
git commit -m "feat: vtf doctor 环境自检"
```

### Task 7.2: `vtf init feishu`

**Files:**
- Modify: `src/vtf/commands/init.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 写测试**

```python
def test_init_feishu_writes_config(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    schema = tmp_path / "schema.toml"
    schema.write_text('[[fields]]\nname = "x"\ntype = "text"\nsource = "meta.url"\n', "utf-8")
    r = CliRunner().invoke(
        main,
        ["init", "feishu"],
        input=f"tok\ntbl\n{schema}\n",
    )
    assert r.exit_code == 0, r.output
    written = (tmp_path / "xdg" / "vtf" / "config.toml").read_text("utf-8")
    assert 'sink = "feishu"' in written
    assert "tok" in written and "tbl" in written
```

- [ ] **Step 2: 实现 init 命令**

`src/vtf/commands/init.py`:

```python
from __future__ import annotations

from pathlib import Path

import click

from vtf.config import default_user_path


@click.group(name="init", help="交互式初始化")
def cmd() -> None:
    pass


@cmd.command("feishu")
def init_feishu() -> None:
    base_token = click.prompt("base_token", type=str).strip()
    table_id = click.prompt("table_id", type=str).strip()
    schema = click.prompt("schema 路径(toml)", type=str).strip()
    if not Path(schema).exists():
        click.echo(f"⚠️  warning: schema 路径不存在:{schema}", err=True)
    target = default_user_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    body = (
        '[output]\n'
        'sink = "feishu"\n\n'
        '[sink.feishu]\n'
        f'base_token = "{base_token}"\n'
        f'table_id = "{table_id}"\n'
        f'schema = "{schema}"\n'
    )
    target.write_text(body, "utf-8")
    click.echo(f"✓ 已写入 {target}")
```

- [ ] **Step 3: 跑测试**

```bash
uv run pytest tests/test_cli.py -v
```

- [ ] **Step 4: 提交**

```bash
git add src/vtf/commands/init.py tests/test_cli.py
git commit -m "feat: vtf init feishu 交互式向导"
```

### Task 7.3: `vtf config get/set/list/unset`

**Files:**
- Modify: `src/vtf/commands/config_cmd.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: 写测试**

```python
def test_config_set_and_get(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    runner = CliRunner()
    r = runner.invoke(main, ["config", "set", "output.sink", "feishu"])
    assert r.exit_code == 0
    r = runner.invoke(main, ["config", "get", "output.sink"])
    assert r.exit_code == 0
    assert r.output.strip() == "feishu"


def test_config_list_includes_set_value(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    runner = CliRunner()
    runner.invoke(main, ["config", "set", "transcribe.asr_model", "x-model"])
    r = runner.invoke(main, ["config", "list"])
    assert r.exit_code == 0
    assert "x-model" in r.output


def test_config_unset(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    runner = CliRunner()
    runner.invoke(main, ["config", "set", "output.sink", "feishu"])
    runner.invoke(main, ["config", "unset", "output.sink"])
    r = runner.invoke(main, ["config", "get", "output.sink"])
    assert r.output.strip() == "markdown"  # 回到默认
```

- [ ] **Step 2: 实现 config 命令组**

`src/vtf/commands/config_cmd.py`:

```python
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import click

from vtf._ctx import get_config
from vtf.config import default_user_path


@click.group(name="config", help="读写用户级配置文件")
def cmd() -> None:
    pass


@cmd.command("get")
@click.argument("key")
@click.pass_context
def _get(ctx: click.Context, key: str) -> None:
    cfg = get_config(ctx)
    val: Any = cfg
    for part in key.split("."):
        if not hasattr(val, part):
            raise SystemExit(1)
        val = getattr(val, part)
    click.echo(str(val))


@cmd.command("set")
@click.argument("key")
@click.argument("value")
def _set(key: str, value: str) -> None:
    path = default_user_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read(path)
    parts = key.split(".")
    cursor = data
    for p in parts[:-1]:
        cursor = cursor.setdefault(p, {})
    cursor[parts[-1]] = _coerce(value)
    _write(path, data)
    click.echo(f"set {key} = {value}")


@cmd.command("unset")
@click.argument("key")
def _unset(key: str) -> None:
    path = default_user_path()
    if not path.exists():
        return
    data = _read(path)
    parts = key.split(".")
    cursor = data
    for p in parts[:-1]:
        if p not in cursor:
            return
        cursor = cursor[p]
    cursor.pop(parts[-1], None)
    _write(path, data)


@cmd.command("list")
def _list() -> None:
    path = default_user_path()
    if not path.exists():
        click.echo("(empty)")
        return
    click.echo(path.read_text("utf-8"))


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return dict(tomllib.load(f))


def _write(path: Path, data: dict[str, Any]) -> None:
    lines: list[str] = []
    _flatten(data, [], lines)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), "utf-8")


def _flatten(d: dict[str, Any], prefix: list[str], out: list[str]) -> None:
    scalars = {k: v for k, v in d.items() if not isinstance(v, dict)}
    if scalars:
        if prefix:
            out.append(f"[{'.'.join(prefix)}]")
        for k, v in scalars.items():
            out.append(f'{k} = {_render_value(v)}')
        out.append("")
    for k, v in d.items():
        if isinstance(v, dict):
            _flatten(v, prefix + [k], out)


def _render_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return f'"{v}"'


def _coerce(raw: str) -> Any:
    if raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    try:
        return int(raw)
    except ValueError:
        return raw
```

- [ ] **Step 3: 跑测试**

```bash
uv run pytest tests/test_cli.py -v
```

预期:三个 config 测试 PASS。

- [ ] **Step 4: 提交**

```bash
git add src/vtf/commands/config_cmd.py tests/test_cli.py
git commit -m "feat: vtf config get/set/list/unset"
```

### Task 7.4: `vtf install <platform>`

**Files:**
- Create: `src/vtf/installer.py`
- Modify: `src/vtf/commands/install.py`
- Create: `tests/test_installer.py`
- Create: `wrappers/claude-code/SKILL.md`(占位,Stage 8 完整化)
- Create: `wrappers/codex/AGENTS.md`(占位)
- Create: `wrappers/generic/README.md`(占位)
- Create: `AGENT_GUIDE.md`(占位)

- [ ] **Step 1: 写 wrapper 占位文件**

`AGENT_GUIDE.md`(根目录):

```markdown
# vtf Agent Guide

(完整内容在 Stage 8 编写。)
```

`wrappers/claude-code/SKILL.md`:

```markdown
---
name: vtf
description: 视频 → 转录 → AI 分析 → markdown / 飞书表格的通用流水线
---

# vtf

通过 `uvx --from <repo-url> vtf <subcommand>` 调用。

详见 AGENT_GUIDE.md。
```

`wrappers/codex/AGENTS.md`:

```markdown
## vtf

视频流水线。调用方式:`uvx --from <repo-url> vtf <subcommand>`。详见 AGENT_GUIDE.md。
```

`wrappers/generic/README.md`:

```markdown
# vtf 通用包装

把 AGENT_GUIDE.md 的内容塞给你的 agent 即可。
```

- [ ] **Step 2: 写 installer 测试**

`tests/test_installer.py`:

```python
from pathlib import Path

import pytest

from vtf.installer import install


def test_install_claude_code_to_target(tmp_path):
    target = tmp_path / "skills"
    out = install(platform="claude-code", target=target, dry_run=False)
    assert (target / "SKILL.md").exists()
    assert (target / "AGENT_GUIDE.md").exists()
    assert "wrote" in out.summary


def test_install_codex_appends_to_agents_md(tmp_path):
    target = tmp_path
    existing = target / "AGENTS.md"
    existing.write_text("# Project\n\nExisting content.\n", "utf-8")
    install(platform="codex", target=target, dry_run=False)
    body = existing.read_text("utf-8")
    assert "Existing content." in body
    assert "## vtf" in body


def test_install_dry_run_creates_nothing(tmp_path):
    target = tmp_path / "skills"
    out = install(platform="claude-code", target=target, dry_run=True)
    assert not (target / "SKILL.md").exists()
    assert "would write" in out.summary


def test_install_unknown_platform_raises(tmp_path):
    from vtf.errors import UserError
    with pytest.raises(UserError):
        install(platform="bogus", target=tmp_path, dry_run=False)
```

- [ ] **Step 3: 写 installer.py**

`src/vtf/installer.py`:

```python
from __future__ import annotations

import shutil
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from vtf.errors import UserError

_SUPPORTED = {"claude-code", "codex", "generic"}


@dataclass
class InstallOutcome:
    summary: str


def install(*, platform: str, target: Path, dry_run: bool) -> InstallOutcome:
    if platform not in _SUPPORTED:
        raise UserError(f"unknown platform: {platform!r}; allowed: {sorted(_SUPPORTED)}")
    repo_root = _find_repo_root()
    src_dir = repo_root / "wrappers" / platform
    if platform == "codex":
        return _install_codex(src_dir, target, dry_run)
    return _install_dir(src_dir, target, dry_run, repo_root)


def _install_dir(src: Path, target: Path, dry_run: bool, repo_root: Path) -> InstallOutcome:
    actions: list[str] = []
    target.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        dest = target / item.name
        if dry_run:
            actions.append(f"would write {dest}")
        else:
            shutil.copy2(item, dest)
            actions.append(f"wrote {dest}")
    guide = repo_root / "AGENT_GUIDE.md"
    if guide.exists():
        dest_guide = target / "AGENT_GUIDE.md"
        if dry_run:
            actions.append(f"would write {dest_guide}")
        else:
            shutil.copy2(guide, dest_guide)
            actions.append(f"wrote {dest_guide}")
    return InstallOutcome(summary="\n".join(actions))


def _install_codex(src: Path, target: Path, dry_run: bool) -> InstallOutcome:
    target.mkdir(parents=True, exist_ok=True)
    agents = target / "AGENTS.md"
    snippet = (src / "AGENTS.md").read_text("utf-8").rstrip() + "\n"
    if dry_run:
        return InstallOutcome(summary=f"would append vtf section to {agents}")
    if agents.exists():
        body = agents.read_text("utf-8").rstrip() + "\n\n" + snippet
    else:
        body = snippet
    agents.write_text(body, "utf-8")
    return InstallOutcome(summary=f"appended vtf section to {agents}")


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here, *here.parents):
        if (p / "wrappers").exists() and (p / "AGENT_GUIDE.md").exists():
            return p
    raise UserError("无法定位仓库根目录(wrappers/ 与 AGENT_GUIDE.md)")
```

- [ ] **Step 4: 实现 install 命令**

`src/vtf/commands/install.py`:

```python
from __future__ import annotations

from pathlib import Path

import click

from vtf.errors import VtfError
from vtf.installer import install


@click.command(name="install", help="把 wrapper 复制到目标 agent 的 skill 目录")
@click.argument("platform")
@click.option("--target", type=click.Path(path_type=Path), required=True)
@click.option("--dry-run", is_flag=True)
def cmd(platform: str, target: Path, dry_run: bool) -> None:
    try:
        out = install(platform=platform, target=target, dry_run=dry_run)
    except VtfError as e:
        click.echo(str(e), err=True)
        raise SystemExit(e.exit_code) from e
    click.echo(out.summary)
```

- [ ] **Step 5: 跑测试**

```bash
uv run pytest tests/test_installer.py -v
```

预期:全部 PASS。

- [ ] **Step 6: 提交**

```bash
git add src/vtf/installer.py src/vtf/commands/install.py tests/test_installer.py wrappers AGENT_GUIDE.md
git commit -m "feat: vtf install <platform>"
```

---

## Stage 8 — Wrappers 完整化与示例

### Task 8.1: 编写完整的 AGENT_GUIDE.md

**Files:**
- Modify: `AGENT_GUIDE.md`

- [ ] **Step 1: 写完整的 AGENT_GUIDE.md**

替换 `AGENT_GUIDE.md` 全部内容为:

```markdown
# vtf Agent 使用指南

`vtf` 是一个把视频(B站 / YouTube / 任意 yt-dlp 支持的源)转换成结构化分析结果的 CLI 流水线。

## 何时使用

- 用户给了视频 URL,需要 markdown 报告或写入飞书表格
- 用户要按"摘要 / 视频拆解 / 二创改写"分析视频内容
- 用户要批量处理一组视频

## 调用方式

主推:`uvx --from <repo-url> vtf <subcommand>`

无 uvx 环境:`pip install -e <repo>` 后用 `vtf <subcommand>`。

## 命令清单

### 端到端

| 命令 | 用途 |
|------|------|
| `vtf run <url>` | 一条龙;走配置好的 sink。**不会执行 LLM 分析,产出占位结果**。仅适合"我只要 transcript + markdown 框架"。 |
| `vtf run <url> --sink markdown` | 临时切到 markdown |
| `vtf run <url> --skip rewrite` | 跳过某个 analyze kind |

### 分步(推荐:让你能在 analyze 步骤注入 LLM)

| 命令 | 输入 | 输出 |
|------|------|------|
| `vtf fetch <url>` | URL | meta.json(stdout) |
| `vtf download --meta meta.json` | meta 文件 | 音频文件路径(stdout) |
| `vtf transcribe <audio>` | 音频文件 | transcript.json |
| `vtf merge` | transcript.json(stdin) | lines.json |
| `vtf analyze --kind summary` | `{meta, lines}`(stdin) | analysis.json(含 prompt + result=null) |
| `vtf assemble --meta m.json --lines l.json --analysis a1.json ...` | 多文件 | result.json |
| `vtf emit` | result.json(stdin) | 落到当前 sink |

### 管理

| 命令 | 用途 |
|------|------|
| `vtf doctor` | 检查 yt-dlp / FunASR / lark-cli 是否就绪 |
| `vtf init feishu` | 交互式配置飞书写入 |
| `vtf config get|set|list|unset` | 管理用户级 config.toml |
| `vtf install claude-code --target <dir>` | 安装 wrapper 到目标 agent 的 skill 目录 |
| `vtf install codex --target <project-root>` | 把 vtf 节追加到工程根 AGENTS.md |

## 典型 Workflow:把视频分析成飞书表格记录

> 注意:**analyze 的 LLM 调用由你这个 agent 完成**。CLI 只生成 prompt。

```bash
URL="https://www.bilibili.com/video/BV1xxx"
WORK="$(mktemp -d)"

uvx --from <repo-url> vtf fetch  "$URL"           > "$WORK/meta.json"
uvx --from <repo-url> vtf download --meta "$WORK/meta.json" > "$WORK/audio.path"
uvx --from <repo-url> vtf transcribe "$(cat "$WORK/audio.path")" > "$WORK/transcript.json"
uvx --from <repo-url> vtf merge < "$WORK/transcript.json" > "$WORK/lines.json"

# 准备 analyze 输入(meta + lines 合一)
jq -s '{meta: .[0], lines: .[1].lines}' "$WORK/meta.json" "$WORK/lines.json" > "$WORK/ctx.json"

for KIND in summary breakdown rewrite; do
  uvx --from <repo-url> vtf analyze --kind "$KIND" < "$WORK/ctx.json" > "$WORK/$KIND.raw.json"
done
```

接下来对每个 `$KIND.raw.json`:

1. 读 `prompt` 字段,把它喂给你内置的 LLM。
2. 期望 LLM 返回一个 JSON,匹配 `schema_hint` 字段描述的形状。
3. 把 LLM 的 JSON 写回 `result` 字段(替换 `null`)。

回填后:

```bash
uvx --from <repo-url> vtf assemble \
  --meta "$WORK/meta.json" --lines "$WORK/lines.json" \
  --analysis "$WORK/summary.raw.json" \
  --analysis "$WORK/breakdown.raw.json" \
  --analysis "$WORK/rewrite.raw.json" \
  > "$WORK/result.json"

uvx --from <repo-url> vtf emit < "$WORK/result.json"
```

## 飞书写入失败如何感知

`vtf emit` 在 `--json` 模式下,若飞书写入失败,会打 `{"level":"warn","msg":"feishu degraded","data":{"reason":...}}` 到 stderr,**自动降级把 markdown 内容写到 stdout**,**不丢数据**。退出码仍为 0。

非 `--json` 模式下,降级信息以人类可读形式打到 stderr。

## 配置位置

- 用户级:`${XDG_CONFIG_HOME:-~/.config}/vtf/config.toml`
- 项目级:`./vtf.toml`(在调用目录下,会覆盖用户级)
- 环境变量:`VTF_<SECTION>_<KEY>`(全大写,例如 `VTF_OUTPUT_SINK=feishu`)
- CLI flag(最高优先级):`--sink markdown` 等

详见 `docs/configuration.md`。

## 字段 schema 自定义

飞书 sink 不内置任何业务字段。要写飞书,必须配置 `sink.feishu.schema` 指向一个 toml 文件。

示例(可直接复用):`examples/schemas/baokuan.toml`(「爆款制造机」19 字段)。

字段 source 表达式参考 `docs/extending.md`。

## 故障速查

- `vtf doctor` —— 一行命令看出哪个依赖缺
- B站元数据失败:确保浏览器登录过 bilibili.com,或在配置里换 `cookies_from_browser` 为 safari/firefox/edge
- FunASR 找不到:`pip install funasr` 后用 `VTF_TRANSCRIBE_FUNASR_PYTHON` 指向那个 Python
- lark-cli 找不到:配置里把 `sink.feishu.lark_cli` 改成你实际的命令名
```

- [ ] **Step 2: 提交**

```bash
git add AGENT_GUIDE.md
git commit -m "docs: 完整 AGENT_GUIDE.md"
```

### Task 8.2: 完整 wrappers/claude-code/SKILL.md

**Files:**
- Modify: `wrappers/claude-code/SKILL.md`

- [ ] **Step 1: 改写 wrappers/claude-code/SKILL.md**

```markdown
---
name: vtf
description: 视频(B站/YouTube/通用)→ FunASR 转录 → 文案合并 → AI 分析(prompt 由你执行)→ markdown 或 飞书多维表格输出。当用户给视频 URL 并希望提取文案/摘要/拆解/二创/写表格时使用。
---

# vtf - 视频内容流水线

## 触发场景

- 用户给 B站/YouTube URL,需要 transcript、摘要、拆解或二创改写
- 用户要把视频信息写入飞书多维表格(配合 lark-cli)
- 用户要批量处理视频

## 调用方式

所有命令通过 `uvx --from <repo-url> vtf <subcommand>` 调用,**首次使用先跑 `vtf doctor` 检查环境**。

## 重要:你需要执行 LLM Prompt

`vtf analyze` 不调用 LLM,仅生成 prompt。**你需要**把 `analysis.json` 里的 `prompt` 字段喂给自己的 LLM,把 LLM 输出的 JSON 写回 `analysis.json` 的 `result` 字段(替换 `null`),再交给 `vtf assemble`。

## 完整指南

详见仓库根目录的 [`AGENT_GUIDE.md`](../../AGENT_GUIDE.md),包含:

- 全部命令清单
- 典型 workflow(端到端 + 分步)
- 配置三级覆盖与环境变量
- 飞书 schema 自定义方法
- 故障速查
```

- [ ] **Step 2: 提交**

```bash
git add wrappers/claude-code/SKILL.md
git commit -m "docs: 完整 Claude Code wrapper SKILL.md"
```

### Task 8.3: 完整 wrappers/codex/AGENTS.md

**Files:**
- Modify: `wrappers/codex/AGENTS.md`

- [ ] **Step 1: 改写**

```markdown
## vtf - 视频内容流水线

视频(B站 / YouTube / yt-dlp 支持的任意源)→ FunASR 转录 → 文案合并 → AI 分析(由 agent 执行 prompt)→ markdown / 飞书多维表格。

调用方式:`uvx --from <repo-url> vtf <subcommand>`

**当用户给视频 URL** 并希望提取文案、生成摘要/拆解/二创、或写飞书表格时,使用本工具。

### 关键命令

- `vtf doctor` —— 环境自检
- `vtf run <url>` —— 端到端(无 LLM 调用,产出占位)
- 推荐分步:`vtf fetch <url>` → `download` → `transcribe` → `merge` → `analyze --kind <K>` → 由你执行 prompt 并回填 `result` → `assemble` → `emit`

### 重要约定

- `vtf analyze` 输出含 `prompt` 字段。**你**负责把它喂给 LLM,然后把 LLM 的 JSON 输出写回 `result` 字段。
- `vtf emit` 失败会自动降级到 markdown,带 `--json` 时会发出 `feishu degraded` 警告。

### 完整指南

详见仓库根的 `AGENT_GUIDE.md`(命令清单、workflow、配置、schema 自定义、故障速查)。
```

- [ ] **Step 2: 提交**

```bash
git add wrappers/codex/AGENTS.md
git commit -m "docs: 完整 Codex wrapper AGENTS.md"
```

### Task 8.4: 示例 schema(爆款制造机 19 字段)

**Files:**
- Create: `examples/schemas/baokuan.toml`

- [ ] **Step 1: 写 baokuan.toml**

```toml
# 「爆款制造机」表格 schema 示例
# 用法:在 ~/.config/vtf/config.toml 设置:
#   [sink.feishu]
#   schema = "/绝对路径/examples/schemas/baokuan.toml"
# 或通过 `vtf config set sink.feishu.schema /path/...`

[[fields]]
name = "对标素材链接"
type = "text"
source = "meta.url"

[[fields]]
name = "标题"
type = "text"
source = "meta.title"

[[fields]]
name = "作者名"
type = "text"
source = "meta.author"

[[fields]]
name = "文案提取"
type = "text"
source = "lines | joined"

[[fields]]
name = "二创改写"
type = "text"
source = "analyses.rewrite.text"

[[fields]]
name = "摘要"
type = "text"
source = "analyses.summary.text"

[[fields]]
name = "视频拆解"
type = "text"
source = "analyses.breakdown.text"

[[fields]]
name = "标签"
type = "text"
source = "analyses.summary.tags | tags_hashtag"

[[fields]]
name = "数据"
type = "text"
source = "meta | stats_compact"

[[fields]]
name = "视频时长"
type = "text"
source = "meta.duration_str"

[[fields]]
name = "播放数"
type = "text"
source = "meta.view"

[[fields]]
name = "点赞数"
type = "text"
source = "meta.like"

[[fields]]
name = "收藏数"
type = "text"
source = "meta.favorite"

[[fields]]
name = "分享数"
type = "text"
source = "meta.share"

[[fields]]
name = "评论数"
type = "text"
source = "meta.reply"

[[fields]]
name = "下载链接"
type = "text"
source = "meta.url"

[[fields]]
name = "封面链接"
type = "text"
source = "meta.thumbnail"

[[fields]]
name = "发布时间"
type = "datetime"
source = "meta.upload_date"

[[fields]]
name = "提取时间"
type = "datetime"
source = "meta.extracted_at"
```

- [ ] **Step 2: 提交**

```bash
git add examples/schemas/baokuan.toml
git commit -m "docs: 爆款制造机 19 字段示例 schema"
```

---

## Stage 9 — 文档与迁移

### Task 9.1: 写 README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: 写 README.md**

```markdown
# vtf - 通用视频内容流水线

把视频(B站 / YouTube / 任意 yt-dlp 支持的源)转录为文案,生成摘要 / 拆解 / 二创,输出为 markdown 或飞书多维表格。

**核心原则**

- 脚本驱动:任何能跑 shell 的 agent 都能用
- 零业务硬编码:模型、cookie 浏览器、字段 schema、CLI 名称、prompts 全部走配置
- LLM 解耦:本工具不连任何 LLM provider,prompt 由调用方 agent 执行
- 双 sink:markdown(默认) / 飞书,飞书写入失败自动降级
- 平台 wrapper:Claude Code 与 Codex 开箱即用

## 安装

```bash
# 推荐:uvx 现场跑(零安装,需 uv ≥ 0.4)
uvx --from git+<repo-url> vtf doctor

# 本地开发
git clone <repo-url> vtf
cd vtf
uv sync --extra dev
uv run vtf doctor
```

## 接入到 agent

```bash
# Claude Code
uvx --from git+<repo-url> vtf install claude-code --target ~/.claude/skills/vtf

# Codex(把 vtf 节追加到工程根 AGENTS.md)
uvx --from git+<repo-url> vtf install codex --target ./
```

## 5 分钟体验(markdown 输出)

```bash
URL="https://youtu.be/<id>"
uvx --from git+<repo-url> vtf run "$URL" --sink markdown
```

## 配置飞书写入

```bash
uvx --from git+<repo-url> vtf init feishu
# 交互输入 base_token / table_id / schema 文件路径
# 之后 `vtf run <url>` 自动写飞书,失败回退 markdown
```

## 文档

- [`AGENT_GUIDE.md`](AGENT_GUIDE.md) —— 智能体使用指南
- [`docs/install.md`](docs/install.md) —— 详细安装(包含各平台)
- [`docs/configuration.md`](docs/configuration.md) —— 完整配置字段
- [`docs/extending.md`](docs/extending.md) —— 加新平台 / 新 sink / schema 自定义
- [`docs/data-shapes.md`](docs/data-shapes.md) —— 流水线 JSON 契约
- [`docs/legacy/SKILL.md.archive.md`](docs/legacy/SKILL.md.archive.md) —— 旧版操作手册(归档)

## 许可

MIT
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: README.md"
```

### Task 9.2: 写 docs/install.md

**Files:**
- Create: `docs/install.md`

- [ ] **Step 1: 写 install.md**

```markdown
# 安装

## 前置依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| Python ≥ 3.11 | 运行时 | 系统包管理器 / [mise](https://mise.jdx.dev) |
| uv ≥ 0.4 | 推荐启动器 | `curl -LsSf https://astral.sh/uv/install.sh | sh` |
| yt-dlp | 元数据 + 下载 | `pip install yt-dlp` |
| FunASR | 中文转录(可选其他模型) | `pip install funasr` |
| lark-cli(或同类) | 写飞书表格(可选) | 见仓库 |

`vtf doctor` 一次性检查上面所有依赖。

## 安装 vtf 本身

### 推荐:uvx 现场跑(零持久安装)

```bash
uvx --from git+<repo-url> vtf doctor
```

每次调用都新建临时虚拟环境,不污染系统。

### 本地 clone(开发或常用)

```bash
git clone <repo-url> vtf
cd vtf
uv sync --extra dev   # 安装 dev 依赖含 pytest、ruff、mypy
uv run vtf --help
```

### pip 安装(传统方式)

```bash
pip install -e <repo-path>
vtf --help
```

## 接入到 Claude Code

```bash
mkdir -p ~/.claude/skills/vtf
uvx --from git+<repo-url> vtf install claude-code --target ~/.claude/skills/vtf
```

或工程级:

```bash
mkdir -p .claude/skills/vtf
uvx --from git+<repo-url> vtf install claude-code --target .claude/skills/vtf
```

## 接入到 Codex

```bash
# 工程根目录运行,会把 vtf 节追加到 ./AGENTS.md
uvx --from git+<repo-url> vtf install codex --target ./
```

## 接入到其他 agent(通用方式)

把仓库根 `AGENT_GUIDE.md` 的内容粘进你的 agent 的 skill / system prompt。

## 配置飞书写入(可选)

参考 `AGENT_GUIDE.md` 中"飞书写入"章节,或运行:

```bash
uvx --from git+<repo-url> vtf init feishu
```

## 卸载

uvx 模式下:无需卸载(无持久状态),用 `vtf config unset <key>` 清掉个性化设置即可。

clone 模式:删除 git 目录,清掉 `~/.config/vtf/`。
```

- [ ] **Step 2: 提交**

```bash
git add docs/install.md
git commit -m "docs: install.md"
```

### Task 9.3: 写 docs/configuration.md

**Files:**
- Create: `docs/configuration.md`

- [ ] **Step 1: 写 configuration.md**

```markdown
# 配置参考

## 三级覆盖优先级(高 → 低)

1. CLI flag(`--sink`、`--workdir`、`--config`)
2. 环境变量 `VTF_*` / 兼容 `TABLE_TOKEN` `TABLE_ID`
3. 项目级 `./vtf.toml`(若存在)
4. 用户级 `${XDG_CONFIG_HOME:-~/.config}/vtf/config.toml`
5. 内置默认值

## 完整字段

```toml
[output]
# 默认 sink:markdown 或 feishu
sink = "markdown"

[transcribe]
funasr_python = ""           # 留空自动探测;可指向任意装了 funasr 的 Python
asr_model = "paraformer-zh"  # FunASR 兼容模型名
vad_model = "fsmn-vad"
punc_model = "ct-punc"
batch_size_s = 300
corrections_file = ""        # JSON 纠错字典路径(键值替换),留空跳过

[platform.bilibili]
cookies_from_browser = "chrome"   # chrome/safari/firefox/edge,留空 = 不带 cookie
cookies_file = ""                  # 二选一:Netscape 格式 cookie 文件

[platform.youtube]
cookies_from_browser = ""
cookies_file = ""

[download]
audio_format = "mp3"         # yt-dlp 支持的音频格式
audio_quality = "0"          # yt-dlp --audio-quality(0 = 最佳)
retries = 3

[sink.markdown]
template = ""                # 留空 = 内置模板;否则指向 .md.j2 Jinja 模板

[sink.feishu]
base_token = ""              # 飞书多维表格 token(必填)
table_id = ""                # 表格 ID(必填)
schema = ""                  # 字段 schema toml 路径(必填)
lark_cli = "lark-cli"        # CLI 命令名,可换为 oapi、自封装命令等

[analyze.prompts]
summary = ""                 # 自定义 summary prompt 路径,空 = 内置
breakdown = ""
rewrite = ""
```

## 环境变量映射

每个嵌套字段都有对应的 `VTF_<SECTION>_<KEY>` 环境变量:

| 配置键 | 环境变量 |
|--------|----------|
| `output.sink` | `VTF_OUTPUT_SINK` |
| `transcribe.funasr_python` | `VTF_TRANSCRIBE_FUNASR_PYTHON` |
| `transcribe.asr_model` | `VTF_TRANSCRIBE_ASR_MODEL` |
| `platform.bilibili.cookies_from_browser` | `VTF_PLATFORM_BILIBILI_COOKIES_FROM_BROWSER` |
| `sink.feishu.base_token` | `VTF_SINK_FEISHU_BASE_TOKEN` |
| `sink.feishu.lark_cli` | `VTF_SINK_FEISHU_LARK_CLI` |
| `download.retries` | `VTF_DOWNLOAD_RETRIES` |
| `analyze.prompts.summary` | `VTF_ANALYZE_PROMPTS_SUMMARY` |

## Legacy 别名(过渡期保留)

| Legacy | 等价 |
|--------|------|
| `TABLE_TOKEN` | `VTF_SINK_FEISHU_BASE_TOKEN` |
| `TABLE_ID` | `VTF_SINK_FEISHU_TABLE_ID` |

未来版本可能移除。请逐步迁移到 `VTF_*`。

## 外部命令路径

| 环境变量 | 用途 | 默认行为 |
|----------|------|----------|
| `VTF_YT_DLP` | yt-dlp 路径 | `which yt-dlp` |
| `VTF_TRANSCRIBE_FUNASR_PYTHON` | 装了 funasr 的 Python | 自动探测 PATH |
| `VTF_SINK_FEISHU_LARK_CLI` | 写飞书的 CLI 命令名 | `cfg.sink.feishu.lark_cli`(默认 lark-cli) |

## XDG

- 用户配置:`$XDG_CONFIG_HOME/vtf/config.toml`,缺省 `~/.config/vtf/config.toml`
- 中间产物缓存:`$XDG_CACHE_HOME/vtf/`,缺省 `~/.cache/vtf/`
- 用 `--workdir` 临时覆盖

## 命令行子命令

参考 `AGENT_GUIDE.md` 命令清单。
```

- [ ] **Step 2: 提交**

```bash
git add docs/configuration.md
git commit -m "docs: configuration.md"
```

### Task 9.4: 写 docs/extending.md

**Files:**
- Create: `docs/extending.md`

- [ ] **Step 1: 写 extending.md**

```markdown
# 扩展指南

## 加新平台(视频源)

实现 `vtf.platforms.base.Platform` Protocol:

```python
class MyPlatform:
    name = "myplatform"
    def matches(self, url: str) -> bool: ...
    def cookie_args(self, cfg) -> list[str]: ...
    def normalize_metadata(self, raw: dict) -> dict: ...
```

把实例追加到 `vtf/platforms/__init__.py` 的 `REGISTRY` 列表中(早注册的优先匹配)。

`normalize_metadata` 必须返回 `docs/data-shapes.md` 中定义的 `meta.json` 结构。

## 加新 sink

实现 `vtf.sinks.base.Sink` Protocol:

```python
from vtf.sinks.base import EmitOutcome

class MySink:
    name = "mysink"
    def available(self, cfg) -> tuple[bool, str]:
        return True, ""
    def emit(self, result: dict, cfg) -> EmitOutcome:
        ...
        return EmitOutcome(sink="mysink")
```

在 `vtf/sinks/__init__.py` 的 `get` 中注册。

失败时,推荐 `_degrade(result, reason=...)` 回退到 markdown 并返回 `EmitOutcome(degraded=True, reason=...)`,与 feishu sink 行为一致。

## Schema 字段语法

`source` 字段支持点路径 + 管道 transformer:

| 表达式 | 行为 |
|--------|------|
| `meta.title` | 取 `result.meta.title` |
| `analyses.summary.text` | 取嵌套字段 |
| `lines \| joined` | 把数组用换行连接 |
| `analyses.summary.tags \| tags_hashtag` | 数组用空格连接(适合 `#tag1 #tag2`) |
| `meta \| stats_compact` | 渲染为"播放X | 点赞Y | ...") |

未来若加 transformer,放在 `vtf/sinks/schema.py::_apply_transformer`。

## 自定义 prompts

写一个 markdown 文件,使用 `{{ title }}`、`{{ author }}`、`{{ platform }}`、`{{ lines }}` 占位符,然后:

```toml
[analyze.prompts]
summary = "/abs/path/to/my-summary.md"
```

或环境变量 `VTF_ANALYZE_PROMPTS_SUMMARY=/abs/path/to/my.md`。

## 自定义 markdown 模板

`[sink.markdown] template = "/abs/path/to/my.md.j2"` 指向 Jinja2 模板。可用变量:`meta`、`lines`、`analyses`(详见 `docs/data-shapes.md`)。
```

- [ ] **Step 2: 提交**

```bash
git add docs/extending.md
git commit -m "docs: extending.md"
```

### Task 9.5: 归档原 SKILL.md

**Files:**
- Move: `SKILL.md` → `docs/legacy/SKILL.md.archive.md`

- [ ] **Step 1: 移动文件**

```bash
mkdir -p docs/legacy
git mv SKILL.md docs/legacy/SKILL.md.archive.md
```

- [ ] **Step 2: 在归档文件顶部加注释**

打开 `docs/legacy/SKILL.md.archive.md`,在第 1 行 frontmatter `---` 之前插入:

```markdown
> **归档说明**
>
> 这是 vtf 仓库前身的"操作手册"风格文档。已被 `vtf` CLI + `AGENT_GUIDE.md` 替代。
> 保留作为历史参考与迁移对照。最新使用方法请看仓库根 `README.md` 与 `AGENT_GUIDE.md`。

```

- [ ] **Step 3: 提交**

```bash
git add docs/legacy
git commit -m "chore: 归档原 SKILL.md 到 docs/legacy"
```

### Task 9.6: 总验证(所有测试 + 静态检查 + 烟雾)

**Files:**(无新建)

- [ ] **Step 1: 跑全部测试**

```bash
uv run pytest -q
```

预期:全部 PASS,无失败。

- [ ] **Step 2: 跑 ruff**

```bash
uv run ruff check src tests
```

预期:无问题。

- [ ] **Step 3: 跑 mypy**

```bash
uv run mypy
```

预期:无问题。

- [ ] **Step 4: 烟雾测试 CLI**

```bash
uv run vtf --help
uv run vtf doctor
uv run vtf config list
```

预期:三条命令均正常输出,doctor 给出依赖检查结果。

- [ ] **Step 5: 提交(若有 lint/类型修复)**

如果上述步骤暴露了 lint 或类型问题,在此修复并提交:

```bash
git add -A
git commit -m "chore: 通过 ruff / mypy / pytest 全验证"
```

否则跳过,跑下面的最终 tag。

- [ ] **Step 6: 最终 tag**

```bash
git tag v0.1.0
```

至此 v0.1.0 完成,可以发布或开始 dogfood。

---

## 自检结果

**Spec 覆盖检查:**

| Spec 章节 | 实施任务 |
|-----------|----------|
| §3.1 仓库结构 | Stage 0 + 各模块阶段 |
| §3.2 数据流 | Task 2.3 + 各 pipeline 任务 |
| §4 CLI 命令面 | Stage 6(run/分步)+ Stage 7(管理) |
| §5 配置模型(三级 + 别名) | Stage 1 全部任务 |
| §6 平台模型 | Stage 3 全部任务 |
| §7 Sink 模型 | Stage 5 全部任务 |
| §8 Prompts | Task 4.2 |
| §9 错误处理与可观测性 | Task 2.1 + 2.2,各命令的 try/except |
| §10 安装与 wrapper | Task 7.4 + Stage 8 |
| §11 测试策略 | 单元 + 契约散落各任务,集成在 Task 6.5 |
| §12 向后兼容(归档 + 别名) | Task 9.5 + Task 1.3 |

**类型一致性:** `Config` 字段名统一在 `config.py`;sink 的 `EmitOutcome` 在 `sinks/base.py` 单一定义;`detect()` / `Platform` 在 `platforms/__init__.py` 与 `platforms/base.py` 对齐;`merge_into_lines` 名字在算法、命令、测试中一致。

**Placeholder 扫描:** 已通读,所有 step 都有具体代码或具体命令。`<repo-url>` 是文档显式标注的占位符(仓库无远端时由用户自填),不是行动 placeholder。
