from __future__ import annotations

import msgspec

INSERT_STMT = """\
INSERT INTO system_static (system_id, wormhole_id)
VALUES ($1, $2);"""


class SystemStatic(msgspec.Struct):
    """Join table linking wormhole systems to their static wormhole types."""

    system_id: int
    wormhole_id: int
