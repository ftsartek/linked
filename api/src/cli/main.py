from __future__ import annotations

import asyncclick as click

from .collect import collect
from .cron import cron
from .keygen import generate_secret, generate_token_key
from .migrate import migrate
from .preseed import preseed
from .schema import schema


@click.group()
def cli() -> None:
    """Linked EVE CLI."""


cli.add_command(generate_token_key)
cli.add_command(generate_secret)
cli.add_command(collect)
cli.add_command(cron)
cli.add_command(migrate)
cli.add_command(preseed)
cli.add_command(schema)


if __name__ == "__main__":
    cli()
