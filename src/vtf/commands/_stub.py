import click


def make_stub(name: str) -> click.Command:
    @click.command(name=name, help=f"{name} (待实现)")
    def cmd() -> None:
        click.echo(f"{name} not implemented", err=True)
        raise SystemExit(2)

    return cmd
