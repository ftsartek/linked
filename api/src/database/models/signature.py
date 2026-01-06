from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

import msgspec


class SignatureGroup(StrEnum):
    """EVE Online signature group types."""

    SIGNATURE = "signature"  # Cosmic Signatures (require probing)
    ANOMALY = "anomaly"  # Cosmic Anomalies (visible on scanner)


class SignatureSubgroup(StrEnum):
    """EVE Online signature subgroup types."""

    COMBAT = "combat"  # Combat Site
    DATA = "data"  # Data Site
    GAS = "gas"  # Gas Site
    ORE = "ore"  # Ore Site
    RELIC = "relic"  # Relic Site
    WORMHOLE = "wormhole"  # Wormhole


CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS signature (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES node(id) ON DELETE CASCADE,
    map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    group_type TEXT NOT NULL,
    subgroup TEXT,
    type TEXT,
    link_id UUID REFERENCES link(id) ON DELETE SET NULL,
    wormhole_id INTEGER REFERENCES wormhole(id),
    date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_deleted TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_signature_node_code_unique
ON signature(node_id, code)
WHERE date_deleted IS NULL;

CREATE INDEX IF NOT EXISTS idx_signature_node_id ON signature(node_id);
CREATE INDEX IF NOT EXISTS idx_signature_map_id ON signature(map_id);
CREATE INDEX IF NOT EXISTS idx_signature_link_id ON signature(link_id);
CREATE INDEX IF NOT EXISTS idx_signature_wormhole_id ON signature(wormhole_id);
CREATE INDEX IF NOT EXISTS idx_signature_date_deleted ON signature(date_deleted);

DROP TRIGGER IF EXISTS trigger_signature_updated_at ON signature;
CREATE TRIGGER trigger_signature_updated_at
    BEFORE UPDATE ON signature
    FOR EACH ROW
    EXECUTE FUNCTION trigger_updated_at();
"""

INSERT_STMT = """\
INSERT INTO signature (node_id, map_id, code, group_type, subgroup, type, link_id, wormhole_id)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
RETURNING id;
"""

UPDATE_STMT = """\
UPDATE signature
SET code = COALESCE($2, code),
    group_type = COALESCE($3, group_type),
    subgroup = $4,
    type = $5,
    link_id = $6,
    wormhole_id = $7,
    date_updated = NOW()
WHERE id = $1 AND date_deleted IS NULL
RETURNING id;
"""


class Signature(msgspec.Struct):
    """Represents a cosmic signature or anomaly on a node."""

    node_id: UUID
    map_id: UUID
    code: str
    group_type: SignatureGroup
    subgroup: SignatureSubgroup | None = None
    type: str | None = None
    link_id: UUID | None = None
    wormhole_id: int | None = None
    id: UUID | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None
    date_deleted: datetime | None = None
