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
    wormhole_id: int | None = None  # Direct wormhole type (only when link_id is NULL)
    id: UUID | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None
    date_deleted: datetime | None = None
