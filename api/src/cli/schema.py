from __future__ import annotations

from pathlib import Path

import asyncclick as click
import msgspec


@click.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("../web/src/lib/openapi.json"),
    show_default=True,
    help="Output file path",
)
def schema(output: Path) -> None:
    """Export OpenAPI schema to a file."""
    from api.main import app

    schema_dict = app.openapi_schema.to_schema()
    content = msgspec.json.format(
        msgspec.json.encode(schema_dict),
        indent=2,
    )
    output.write_bytes(content)

    click.echo(f"Wrote OpenAPI schema to {output}")
