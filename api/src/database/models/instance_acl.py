from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

# ============================================================================
# Character ACL
# ============================================================================

CHARACTER_INSERT_STMT = """\
INSERT INTO instance_acl_character (character_id, character_name, added_by)
VALUES ($1, $2, $3)
ON CONFLICT (character_id) DO NOTHING;
"""

CHARACTER_DELETE_STMT = """\
DELETE FROM instance_acl_character
WHERE character_id = $1;
"""

CHARACTER_LIST_STMT = """\
SELECT
    character_id,
    character_name,
    added_by,
    date_created
FROM instance_acl_character
ORDER BY character_name;
"""

# ============================================================================
# Corporation ACL
# ============================================================================

CORPORATION_INSERT_STMT = """\
INSERT INTO instance_acl_corporation (corporation_id, corporation_name, corporation_ticker, added_by)
VALUES ($1, $2, $3, $4)
ON CONFLICT (corporation_id) DO NOTHING;
"""

CORPORATION_DELETE_STMT = """\
DELETE FROM instance_acl_corporation
WHERE corporation_id = $1;
"""

CORPORATION_LIST_STMT = """\
SELECT
    corporation_id,
    corporation_name,
    corporation_ticker,
    added_by,
    date_created
FROM instance_acl_corporation
ORDER BY corporation_name;
"""

# ============================================================================
# Alliance ACL
# ============================================================================

ALLIANCE_INSERT_STMT = """\
INSERT INTO instance_acl_alliance (alliance_id, alliance_name, alliance_ticker, added_by)
VALUES ($1, $2, $3, $4)
ON CONFLICT (alliance_id) DO NOTHING;
"""

ALLIANCE_DELETE_STMT = """\
DELETE FROM instance_acl_alliance
WHERE alliance_id = $1;
"""

ALLIANCE_LIST_STMT = """\
SELECT
    alliance_id,
    alliance_name,
    alliance_ticker,
    added_by,
    date_created
FROM instance_acl_alliance
ORDER BY alliance_name;
"""

# ============================================================================
# ACL Check Query
# ============================================================================

# Check if user passes ACL (is owner, admin, or any character matches ACL)
CHECK_USER_ACCESS_STMT = """\
SELECT EXISTS(
    -- Check if user is owner
    SELECT 1 FROM instance_settings WHERE owner_id = $1
    UNION
    -- Check if user is admin
    SELECT 1 FROM instance_admin WHERE user_id = $1
    UNION
    -- Check character ACL
    SELECT 1 FROM instance_acl_character iac
    JOIN character c ON c.id = iac.character_id
    WHERE c.user_id = $1
    UNION
    -- Check corporation ACL (any of user's characters in allowed corp)
    SELECT 1 FROM instance_acl_corporation iac
    JOIN character c ON c.corporation_id = iac.corporation_id
    WHERE c.user_id = $1
    UNION
    -- Check alliance ACL (any of user's characters in allowed alliance)
    SELECT 1 FROM instance_acl_alliance iaa
    JOIN character c ON c.alliance_id = iaa.alliance_id
    WHERE c.user_id = $1
);
"""

# Check if a specific character (with affiliations) passes ACL
# Used during signup to check before user exists
CHECK_CHARACTER_ACCESS_STMT = """\
SELECT EXISTS(
    -- Check character directly
    SELECT 1 FROM instance_acl_character WHERE character_id = $1
    UNION
    -- Check corporation
    SELECT 1 FROM instance_acl_corporation WHERE corporation_id = $2
    UNION
    -- Check alliance
    SELECT 1 FROM instance_acl_alliance WHERE alliance_id = $3
);
"""

# Check if user is privileged (owner or admin) - bypasses ACL
CHECK_IS_PRIVILEGED_STMT = """\
SELECT EXISTS(
    SELECT 1 FROM instance_settings WHERE owner_id = $1
    UNION
    SELECT 1 FROM instance_admin WHERE user_id = $1
);
"""

# Check if instance is open (no ACL required)
CHECK_IS_OPEN_STMT = """\
SELECT COALESCE(
    (SELECT is_open FROM instance_settings WHERE id = 1),
    FALSE
);
"""

# Count ACL entries (for status display)
COUNT_ACL_ENTRIES_STMT = """\
SELECT
    (SELECT COUNT(*) FROM instance_acl_character) as character_count,
    (SELECT COUNT(*) FROM instance_acl_corporation) as corporation_count,
    (SELECT COUNT(*) FROM instance_acl_alliance) as alliance_count,
    (SELECT COUNT(*) FROM instance_admin) as admin_count;
"""


# ============================================================================
# Structs
# ============================================================================


class InstanceACLCharacter(msgspec.Struct):
    """Character ACL entry."""

    character_id: int
    added_by: UUID | None = None
    date_created: datetime | None = None


class InstanceACLCharacterWithName(msgspec.Struct):
    """Character ACL entry with name for display."""

    character_id: int
    character_name: str
    added_by: UUID | None = None
    date_created: datetime | None = None


class InstanceACLCorporation(msgspec.Struct):
    """Corporation ACL entry."""

    corporation_id: int
    added_by: UUID | None = None
    date_created: datetime | None = None


class InstanceACLCorporationWithName(msgspec.Struct):
    """Corporation ACL entry with name for display."""

    corporation_id: int
    corporation_name: str
    corporation_ticker: str
    added_by: UUID | None = None
    date_created: datetime | None = None


class InstanceACLAlliance(msgspec.Struct):
    """Alliance ACL entry."""

    alliance_id: int
    added_by: UUID | None = None
    date_created: datetime | None = None


class InstanceACLAllianceWithName(msgspec.Struct):
    """Alliance ACL entry with name for display."""

    alliance_id: int
    alliance_name: str
    alliance_ticker: str
    added_by: UUID | None = None
    date_created: datetime | None = None


class InstanceACLCounts(msgspec.Struct):
    """ACL entry counts for status display."""

    character_count: int
    corporation_count: int
    alliance_count: int
    admin_count: int
