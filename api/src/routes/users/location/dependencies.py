"""Dependencies for character location routes."""

from __future__ import annotations

from sqlspec import AsyncDriverAdapterBase

from esi_client import ESIClient
from routes.users.location.service import LocationService
from services.encryption import EncryptionService
from services.eve_sso import EveSSOService
from utils.valkey import NamespacedValkey


async def provide_location_service(
    db_session: AsyncDriverAdapterBase,
    encryption_service: EncryptionService,
    sso_service: EveSSOService,
    esi_client: ESIClient,
    location_cache: NamespacedValkey,
) -> LocationService:
    """Provide LocationService with injected dependencies."""
    return LocationService(
        db_session,
        encryption_service,
        sso_service,
        esi_client,
        location_cache,
    )
