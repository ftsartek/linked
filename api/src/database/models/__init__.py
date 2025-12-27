from database.models.region import Region, CREATE_STMT as REGION_CREATE, INSERT_STMT as REGION_INSERT
from database.models.constellation import Constellation, CREATE_STMT as CONSTELLATION_CREATE, INSERT_STMT as CONSTELLATION_INSERT
from database.models.effect import Effect, CREATE_STMT as EFFECT_CREATE, INSERT_STMT as EFFECT_INSERT
from database.models.wormhole import Wormhole, CREATE_STMT as WORMHOLE_CREATE, INSERT_STMT as WORMHOLE_INSERT
from database.models.system import System, CREATE_STMT as SYSTEM_CREATE, INSERT_STMT as SYSTEM_INSERT
from database.models.system_static import SystemStatic, CREATE_STMT as SYSTEM_STATIC_CREATE, INSERT_STMT as SYSTEM_STATIC_INSERT

# Dynamic models
from database.models.user import User, CREATE_STMT as USER_CREATE, INSERT_STMT as USER_INSERT
from database.models.character import Character, CREATE_STMT as CHARACTER_CREATE, INSERT_STMT as CHARACTER_INSERT
from database.models.refresh_token import (
    RefreshToken,
    CREATE_STMT as REFRESH_TOKEN_CREATE,
    UPSERT_STMT as REFRESH_TOKEN_UPSERT,
    SELECT_BY_CHARACTER_STMT as REFRESH_TOKEN_SELECT_BY_CHARACTER,
    DELETE_BY_CHARACTER_STMT as REFRESH_TOKEN_DELETE_BY_CHARACTER,
)
from database.models.corporation import Corporation, CREATE_STMT as CORPORATION_CREATE, INSERT_STMT as CORPORATION_INSERT
from database.models.alliance import Alliance, CREATE_STMT as ALLIANCE_CREATE, INSERT_STMT as ALLIANCE_INSERT
from database.models.map import Map, CREATE_STMT as MAP_CREATE, INSERT_STMT as MAP_INSERT
from database.models.map_user import MapUser, CREATE_STMT as MAP_USER_CREATE, INSERT_STMT as MAP_USER_INSERT
from database.models.map_corporation import MapCorporation, CREATE_STMT as MAP_CORPORATION_CREATE, INSERT_STMT as MAP_CORPORATION_INSERT
from database.models.map_alliance import MapAlliance, CREATE_STMT as MAP_ALLIANCE_CREATE, INSERT_STMT as MAP_ALLIANCE_INSERT
from database.models.node import Node, CREATE_STMT as NODE_CREATE, INSERT_STMT as NODE_INSERT
from database.models.link import Link, CREATE_STMT as LINK_CREATE, INSERT_STMT as LINK_INSERT

__all__ = [
    # Static EVE data
    "Region",
    "REGION_CREATE",
    "REGION_INSERT",
    "Constellation",
    "CONSTELLATION_CREATE",
    "CONSTELLATION_INSERT",
    "Effect",
    "EFFECT_CREATE",
    "EFFECT_INSERT",
    "Wormhole",
    "WORMHOLE_CREATE",
    "WORMHOLE_INSERT",
    "System",
    "SYSTEM_CREATE",
    "SYSTEM_INSERT",
    "SystemStatic",
    "SYSTEM_STATIC_CREATE",
    "SYSTEM_STATIC_INSERT",
    # Dynamic models
    "User",
    "USER_CREATE",
    "USER_INSERT",
    "Character",
    "CHARACTER_CREATE",
    "CHARACTER_INSERT",
    "RefreshToken",
    "REFRESH_TOKEN_CREATE",
    "REFRESH_TOKEN_UPSERT",
    "REFRESH_TOKEN_SELECT_BY_CHARACTER",
    "REFRESH_TOKEN_DELETE_BY_CHARACTER",
    "Corporation",
    "CORPORATION_CREATE",
    "CORPORATION_INSERT",
    "Alliance",
    "ALLIANCE_CREATE",
    "ALLIANCE_INSERT",
    "Map",
    "MAP_CREATE",
    "MAP_INSERT",
    "MapUser",
    "MAP_USER_CREATE",
    "MAP_USER_INSERT",
    "MapCorporation",
    "MAP_CORPORATION_CREATE",
    "MAP_CORPORATION_INSERT",
    "MapAlliance",
    "MAP_ALLIANCE_CREATE",
    "MAP_ALLIANCE_INSERT",
    "Node",
    "NODE_CREATE",
    "NODE_INSERT",
    "Link",
    "LINK_CREATE",
    "LINK_INSERT",
]
