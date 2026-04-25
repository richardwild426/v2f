from __future__ import annotations

from pathlib import Path

import click

from vtf.commands import (
    analyze as _analyze,
)
from vtf.commands import (
    assemble as _assemble,
)
from vtf.commands import (
    config_cmd as _config_cmd,
)
from vtf.commands import (
    doctor as _doctor,
)
from vtf.commands import (
    download as _download,
)
from vtf.commands import (
    emit as _emit,
)
from vtf.commands import (
    fetch as _fetch,
)
from vtf.commands import (
    init as _init,
)
from vtf.commands import (
    install as _install,
)
from vtf.commands import (
    merge as _merge,
)
from vtf.commands import (
    run as _run,
)
from vtf.commands import (
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


if __name__ == "__main__":
    main()
