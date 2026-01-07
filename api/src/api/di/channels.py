from __future__ import annotations

import valkey.asyncio as valkey
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.redis import RedisChannelsStreamBackend

from config import get_settings

settings = get_settings()

channels_valkey = valkey.from_url(settings.valkey_event_url)
channels_plugin = ChannelsPlugin(
    backend=RedisChannelsStreamBackend(
        history=100,
        redis=channels_valkey,  # Valkey is Redis-compatible
        key_prefix="MAP_EVENTS",
    ),
    arbitrary_channels_allowed=True,
    create_ws_route_handlers=False,
)
