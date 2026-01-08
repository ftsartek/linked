from __future__ import annotations

import asyncclick as click

from config.settings import get_settings

from .collect import collect
from .cron import cron
from .migrate import migrate
from .preseed import preseed
from .schema import schema


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Linked EVE CLI."""
    ctx.obj = get_settings()


cli.add_command(collect)
cli.add_command(cron)
cli.add_command(migrate)
cli.add_command(preseed)
cli.add_command(schema)


if __name__ == "__main__":
    cli()
