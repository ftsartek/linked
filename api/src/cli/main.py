import asyncclick as click

from .collect import collect
from .preseed import preseed


@click.group()
def cli() -> None:
    """Linked EVE CLI."""
    pass


cli.add_command(collect)
cli.add_command(preseed)


if __name__ == "__main__":
    cli()
