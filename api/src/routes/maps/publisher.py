"""Event publisher for map SSE events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

import msgspec
from litestar.channels import ChannelsPlugin
from valkey.asyncio import Valkey

from routes.maps.events import MapEvent

if TYPE_CHECKING:
    from routes.maps.dependencies import (
        DeleteLinkResponse,
        DeleteMapResponse,
        DeleteNodeResponse,
        DeleteNoteResponse,
        DeleteSignatureResponse,
        EnrichedLinkInfo,
        EnrichedNodeInfo,
        EnrichedNoteInfo,
        EnrichedSignatureInfo,
        MapInfo,
        NodeCharacterLocation,
    )


class EventPublisher:
    """Publishes map events to SSE channels."""

    def __init__(self, channels: ChannelsPlugin, valkey_client: Valkey) -> None:
        self.channels = channels
        self.valkey = valkey_client

    async def get_next_event_id(self, map_id: UUID) -> str:
        """Get the next event ID for a map using Valkey INCR."""
        key = f"map_event_seq:{map_id}"
        event_num = await self.valkey.incr(key)
        return str(event_num)

    async def _publish(self, map_id: UUID, event: MapEvent) -> None:
        """Publish an event to the map's channel."""
        channel_name = f"map:{map_id}"
        data = msgspec.json.encode(event)

        await self.channels.wait_published(data, channel_name)

    def _struct_to_dict(self, obj: Any) -> dict[str, Any]:
        """Convert a msgspec Struct to a dict for event data."""
        return msgspec.to_builtins(obj)

    # Node events

    async def node_created(
        self,
        map_id: UUID,
        node: EnrichedNodeInfo,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a node_created event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.node_created(
            event_id=event_id,
            map_id=map_id,
            node_data=self._struct_to_dict(node),
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def node_updated(
        self,
        map_id: UUID,
        node: EnrichedNodeInfo,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a node_updated event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.node_updated(
            event_id=event_id,
            map_id=map_id,
            update_data=self._struct_to_dict(node),
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def node_deleted(
        self,
        map_id: UUID,
        response: DeleteNodeResponse,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a node_deleted event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.node_deleted(
            event_id=event_id,
            map_id=map_id,
            node_id=response.node_id,
            user_id=user_id,
        )
        await self._publish(map_id, event)

        # Also publish events for deleted links
        for link_id in response.deleted_link_ids:
            link_event_id = await self.get_next_event_id(map_id)
            link_event = MapEvent.link_deleted(
                event_id=link_event_id,
                map_id=map_id,
                link_id=link_id,
                user_id=user_id,
            )
            await self._publish(map_id, link_event)

        # Also publish events for deleted signatures
        for signature_id in response.deleted_signature_ids:
            sig_event_id = await self.get_next_event_id(map_id)
            sig_event = MapEvent.signature_deleted(
                event_id=sig_event_id,
                map_id=map_id,
                signature_id=signature_id,
                user_id=user_id,
            )
            await self._publish(map_id, sig_event)

    # Link events

    async def link_created(
        self,
        map_id: UUID,
        link: EnrichedLinkInfo,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a link_created event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.link_created(
            event_id=event_id,
            map_id=map_id,
            link_data=self._struct_to_dict(link),
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def link_updated(
        self,
        map_id: UUID,
        link: EnrichedLinkInfo,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a link_updated event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.link_updated(
            event_id=event_id,
            map_id=map_id,
            link_data=self._struct_to_dict(link),
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def link_deleted(
        self,
        map_id: UUID,
        response: DeleteLinkResponse,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a link_deleted event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.link_deleted(
            event_id=event_id,
            map_id=map_id,
            link_id=response.link_id,
            user_id=user_id,
        )
        await self._publish(map_id, event)

    # Map events

    async def map_updated(
        self,
        map_id: UUID,
        map_info: MapInfo,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a map_updated event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.map_updated(
            event_id=event_id,
            map_id=map_id,
            changes=self._struct_to_dict(map_info),
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def map_deleted(
        self,
        map_id: UUID,
        response: DeleteMapResponse,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a map_deleted event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.map_deleted(
            event_id=event_id,
            map_id=map_id,
            deleted_node_ids=response.deleted_node_ids,
            deleted_link_ids=response.deleted_link_ids,
            user_id=user_id,
        )
        await self._publish(map_id, event)

    # Access events

    async def access_character_granted(
        self,
        map_id: UUID,
        character_id: int,
        read_only: bool,
        user_id: UUID | None = None,
    ) -> None:
        """Publish an access_character_granted event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.access_character_granted(
            event_id=event_id,
            map_id=map_id,
            character_id=character_id,
            read_only=read_only,
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def access_character_revoked(
        self,
        map_id: UUID,
        character_id: int,
        user_id: UUID | None = None,
    ) -> None:
        """Publish an access_character_revoked event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.access_character_revoked(
            event_id=event_id,
            map_id=map_id,
            character_id=character_id,
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def access_corporation_granted(
        self,
        map_id: UUID,
        corporation_id: int,
        read_only: bool,
        user_id: UUID | None = None,
    ) -> None:
        """Publish an access_corporation_granted event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.access_corporation_granted(
            event_id=event_id,
            map_id=map_id,
            corporation_id=corporation_id,
            read_only=read_only,
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def access_corporation_revoked(
        self,
        map_id: UUID,
        corporation_id: int,
        user_id: UUID | None = None,
    ) -> None:
        """Publish an access_corporation_revoked event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.access_corporation_revoked(
            event_id=event_id,
            map_id=map_id,
            corporation_id=corporation_id,
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def access_alliance_granted(
        self,
        map_id: UUID,
        alliance_id: int,
        read_only: bool,
        user_id: UUID | None = None,
    ) -> None:
        """Publish an access_alliance_granted event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.access_alliance_granted(
            event_id=event_id,
            map_id=map_id,
            alliance_id=alliance_id,
            read_only=read_only,
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def access_alliance_revoked(
        self,
        map_id: UUID,
        alliance_id: int,
        user_id: UUID | None = None,
    ) -> None:
        """Publish an access_alliance_revoked event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.access_alliance_revoked(
            event_id=event_id,
            map_id=map_id,
            alliance_id=alliance_id,
            user_id=user_id,
        )
        await self._publish(map_id, event)

    # Signature events

    async def signature_created(
        self,
        map_id: UUID,
        signature: EnrichedSignatureInfo,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a signature_created event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.signature_created(
            event_id=event_id,
            map_id=map_id,
            signature_data=self._struct_to_dict(signature),
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def signature_updated(
        self,
        map_id: UUID,
        signature: EnrichedSignatureInfo,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a signature_updated event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.signature_updated(
            event_id=event_id,
            map_id=map_id,
            signature_data=self._struct_to_dict(signature),
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def signature_deleted(
        self,
        map_id: UUID,
        response: DeleteSignatureResponse,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a signature_deleted event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.signature_deleted(
            event_id=event_id,
            map_id=map_id,
            signature_id=response.signature_id,
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def signatures_bulk_updated(
        self,
        map_id: UUID,
        node_id: UUID,
        created_ids: list[UUID],
        updated_ids: list[UUID],
        deleted_ids: list[UUID],
        user_id: UUID | None = None,
    ) -> None:
        """Publish a signatures_bulk_updated event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.signatures_bulk_updated(
            event_id=event_id,
            map_id=map_id,
            node_id=node_id,
            created_ids=created_ids,
            updated_ids=updated_ids,
            deleted_ids=deleted_ids,
            user_id=user_id,
        )
        await self._publish(map_id, event)

    # Note events

    async def note_created(
        self,
        map_id: UUID,
        note: EnrichedNoteInfo,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a note_created event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.note_created(
            event_id=event_id,
            map_id=map_id,
            note_data=self._struct_to_dict(note),
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def note_updated(
        self,
        map_id: UUID,
        note: EnrichedNoteInfo,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a note_updated event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.note_updated(
            event_id=event_id,
            map_id=map_id,
            note_data=self._struct_to_dict(note),
            user_id=user_id,
        )
        await self._publish(map_id, event)

    async def note_deleted(
        self,
        map_id: UUID,
        response: DeleteNoteResponse,
        user_id: UUID | None = None,
    ) -> None:
        """Publish a note_deleted event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.note_deleted(
            event_id=event_id,
            map_id=map_id,
            note_id=response.note_id,
            user_id=user_id,
        )
        await self._publish(map_id, event)

    # Character location events

    async def character_arrived(
        self,
        map_id: UUID,
        node_id: UUID,
        character_data: NodeCharacterLocation,
    ) -> None:
        """Publish a character_arrived event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.character_arrived(
            event_id=event_id,
            map_id=map_id,
            node_id=node_id,
            character_data=self._struct_to_dict(character_data),
        )
        await self._publish(map_id, event)

    async def character_left(
        self,
        map_id: UUID,
        node_id: UUID,
        character_data: NodeCharacterLocation,
    ) -> None:
        """Publish a character_left event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.character_left(
            event_id=event_id,
            map_id=map_id,
            node_id=node_id,
            character_data=self._struct_to_dict(character_data),
        )
        await self._publish(map_id, event)

    async def character_updated(
        self,
        map_id: UUID,
        node_id: UUID,
        character_data: NodeCharacterLocation,
    ) -> None:
        """Publish a character_updated event."""
        event_id = await self.get_next_event_id(map_id)
        event = MapEvent.character_updated(
            event_id=event_id,
            map_id=map_id,
            node_id=node_id,
            character_data=self._struct_to_dict(character_data),
        )
        await self._publish(map_id, event)


async def provide_event_publisher(
    channels: ChannelsPlugin,
    valkey_client: Valkey,
) -> EventPublisher:
    """Provide EventPublisher with injected dependencies."""
    return EventPublisher(channels, valkey_client)
