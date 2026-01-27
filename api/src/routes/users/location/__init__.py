"""Character location tracking module."""

from routes.users.location.dependencies import provide_location_service
from routes.users.location.service import (
    CharacterLocationData,
    CharacterLocationError,
    LocationService,
)

__all__ = [
    "CharacterLocationData",
    "CharacterLocationError",
    "LocationService",
    "provide_location_service",
]
