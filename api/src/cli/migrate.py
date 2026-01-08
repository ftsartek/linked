from __future__ import annotations
from pathlib import Path

import asyncclick as click

from database import db


@click.command()
async def migrate() -> None:
    """Run database migrations to latest version."""
    click.echo("Running database migrations...")
    await db.migrate_up("head")
    click.echo("Migrations complete.")
