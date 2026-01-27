from __future__ import annotations

import asyncclick as click


@click.command()
async def migrate() -> None:
    """Run database migrations to latest version."""
    from database import db

    click.echo("Running database migrations...")
    await db.migrate_up("head")
    click.echo("Migrations complete.")
