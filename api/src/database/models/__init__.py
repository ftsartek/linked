from database.models.alliance import INSERT_STMT as ALLIANCE_INSERT
from database.models.alliance import Alliance
from database.models.character import INSERT_STMT as CHARACTER_INSERT
from database.models.character import Character
from database.models.constellation import (
    INSERT_STMT as CONSTELLATION_INSERT,
)
from database.models.constellation import (
    Constellation,
)
from database.models.corporation import (
    INSERT_STMT as CORPORATION_INSERT,
)
from database.models.corporation import (
    Corporation,
)
from database.models.effect import INSERT_STMT as EFFECT_INSERT
from database.models.effect import Effect
from database.models.link import INSERT_STMT as LINK_INSERT
from database.models.link import Link
from database.models.map import INSERT_STMT as MAP_INSERT
from database.models.map import Map
from database.models.map_alliance import (
    INSERT_STMT as MAP_ALLIANCE_INSERT,
)
from database.models.map_alliance import (
    MapAlliance,
)
from database.models.map_character import INSERT_STMT as MAP_CHARACTER_INSERT
from database.models.map_character import MapCharacter
from database.models.map_corporation import (
    INSERT_STMT as MAP_CORPORATION_INSERT,
)
from database.models.map_corporation import (
    MapCorporation,
)
from database.models.map_subscription import (
    DELETE_STMT as MAP_SUBSCRIPTION_DELETE,
)
from database.models.map_subscription import (
    INSERT_STMT as MAP_SUBSCRIPTION_INSERT,
)
from database.models.map_subscription import (
    MapSubscription,
)
from database.models.node import INSERT_STMT as NODE_INSERT
from database.models.node import Node
from database.models.refresh_token import (
    DELETE_BY_CHARACTER_STMT as REFRESH_TOKEN_DELETE_BY_CHARACTER,
)
from database.models.refresh_token import (
    SELECT_BY_CHARACTER_STMT as REFRESH_TOKEN_SELECT_BY_CHARACTER,
)
from database.models.refresh_token import (
    UPSERT_STMT as REFRESH_TOKEN_UPSERT,
)
from database.models.refresh_token import (
    RefreshToken,
)
from database.models.region import INSERT_STMT as REGION_INSERT
from database.models.region import Region
from database.models.signature import INSERT_STMT as SIGNATURE_INSERT
from database.models.signature import Signature, SignatureGroup, SignatureSubgroup
from database.models.system import INSERT_STMT as SYSTEM_INSERT
from database.models.system import System
from database.models.system_static import (
    INSERT_STMT as SYSTEM_STATIC_INSERT,
)
from database.models.system_static import (
    SystemStatic,
)
from database.models.user import INSERT_STMT as USER_INSERT

# Dynamic models
from database.models.user import User
from database.models.wormhole import INSERT_STMT as WORMHOLE_INSERT
from database.models.wormhole import Wormhole

__all__ = [
    # Static EVE data
    "Region",
    "REGION_INSERT",
    "Constellation",
    "CONSTELLATION_INSERT",
    "Effect",
    "EFFECT_INSERT",
    "Wormhole",
    "WORMHOLE_INSERT",
    "System",
    "SYSTEM_INSERT",
    "SystemStatic",
    "SYSTEM_STATIC_INSERT",
    # Dynamic models
    "User",
    "USER_INSERT",
    "Character",
    "CHARACTER_INSERT",
    "RefreshToken",
    "REFRESH_TOKEN_UPSERT",
    "REFRESH_TOKEN_SELECT_BY_CHARACTER",
    "REFRESH_TOKEN_DELETE_BY_CHARACTER",
    "Corporation",
    "CORPORATION_INSERT",
    "Alliance",
    "ALLIANCE_INSERT",
    "Map",
    "MAP_INSERT",
    "MapCharacter",
    "MAP_CHARACTER_INSERT",
    "MapCorporation",
    "MAP_CORPORATION_INSERT",
    "MapAlliance",
    "MAP_ALLIANCE_INSERT",
    "MapSubscription",
    "MAP_SUBSCRIPTION_INSERT",
    "MAP_SUBSCRIPTION_DELETE",
    "Node",
    "NODE_INSERT",
    "Link",
    "LINK_INSERT",
    "Signature",
    "SignatureGroup",
    "SignatureSubgroup",
    "SIGNATURE_INSERT",
]
