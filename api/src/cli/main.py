from __future__ import annotations

import asyncclick as click

from .collect import collect
from .migrate import migrate
from .preseed import preseed
from .schema import schema


@click.group()
def cli() -> None:
    """Linked EVE CLI."""
    pass


cli.add_command(collect)
cli.add_command(migrate)
cli.add_command(preseed)
cli.add_command(schema)


if __name__ == "__main__":
    cli()
