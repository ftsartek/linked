from __future__ import annotations

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS system_static (
    system_id INTEGER REFERENCES system(id) ON DELETE CASCADE,
    wormhole_id INTEGER REFERENCES wormhole(id) ON DELETE CASCADE,
    PRIMARY KEY (system_id, wormhole_id)
);

CREATE INDEX IF NOT EXISTS idx_system_static_wormhole_id ON system_static(wormhole_id);
"""

INSERT_STMT = """\
INSERT INTO system_static (system_id, wormhole_id)
VALUES ($1, $2);"""


class SystemStatic(msgspec.Struct):
    """Join table linking wormhole systems to their static wormhole types."""

    system_id: int
    wormhole_id: int
