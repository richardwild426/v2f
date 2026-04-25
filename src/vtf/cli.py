import click


@click.group()
@click.version_option(package_name="vtf")
def main() -> None:
    """vtf - 视频内容流水线 CLI"""


if __name__ == "__main__":
    main()
