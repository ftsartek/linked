"""Admin API request/response types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# ============================================================================
# Instance Status
# ============================================================================


@dataclass
class InstanceStatusResponse:
    """Instance status information."""

    owner_id: UUID
    owner_name: str | None
    is_open: bool
    character_acl_count: int
    corporation_acl_count: int
    alliance_acl_count: int
    admin_count: int


@dataclass
class UpdateInstanceRequest:
    """Request to update instance settings."""

    is_open: bool


# ============================================================================
# Ownership Transfer
# ============================================================================


@dataclass
class TransferOwnershipRequest:
    """Request to transfer instance ownership."""

    new_owner_id: UUID


# ============================================================================
# Admin Management
# ============================================================================


@dataclass
class AdminInfo:
    """Admin information for display."""

    user_id: UUID
    character_id: int | None
    character_name: str | None
    granted_by: UUID | None
    date_created: datetime | None


@dataclass
class AdminListResponse:
    """List of instance admins."""

    admins: list[AdminInfo]


@dataclass
class AddAdminRequest:
    """Request to add an admin."""

    user_id: UUID


# ============================================================================
# Character ACL
# ============================================================================


@dataclass
class CharacterACLEntry:
    """Character ACL entry for display."""

    character_id: int
    character_name: str
    added_by: UUID | None
    date_created: datetime | None


@dataclass
class CharacterACLListResponse:
    """List of character ACL entries."""

    entries: list[CharacterACLEntry]


@dataclass
class AddCharacterACLRequest:
    """Request to add a character to ACL."""

    character_id: int
    character_name: str


# ============================================================================
# Corporation ACL
# ============================================================================


@dataclass
class CorporationACLEntry:
    """Corporation ACL entry for display."""

    corporation_id: int
    corporation_name: str
    corporation_ticker: str
    added_by: UUID | None
    date_created: datetime | None


@dataclass
class CorporationACLListResponse:
    """List of corporation ACL entries."""

    entries: list[CorporationACLEntry]


@dataclass
class AddCorporationACLRequest:
    """Request to add a corporation to ACL."""

    corporation_id: int
    corporation_name: str
    corporation_ticker: str


# ============================================================================
# Alliance ACL
# ============================================================================


@dataclass
class AllianceACLEntry:
    """Alliance ACL entry for display."""

    alliance_id: int
    alliance_name: str
    alliance_ticker: str
    added_by: UUID | None
    date_created: datetime | None


@dataclass
class AllianceACLListResponse:
    """List of alliance ACL entries."""

    entries: list[AllianceACLEntry]


@dataclass
class AddAllianceACLRequest:
    """Request to add an alliance to ACL."""

    alliance_id: int
    alliance_name: str
    alliance_ticker: str
