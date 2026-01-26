"""Namespaced Valkey client wrapper."""

from __future__ import annotations

from typing import Any, Self

from valkey.asyncio import Valkey
from valkey.typing import AbsExpiryT, EncodableT, ExpiryT, KeyT, ResponseT

EVENT_NAMESPACE = "MAP_EVENT"


class NamespacedValkey(Valkey):
    """A Valkey client that prepends a namespace prefix to all keys.

    Inherits from Valkey for API compatibility - can be used anywhere
    a Valkey client is expected.

    Example:
        client = NamespacedValkey.from_url(url, namespace="events")
        await client.incr("map_seq:123")  # Actually increments "events:map_seq:123"

        # Nested namespaces
        sub = client.with_namespace("maps")
        await sub.get("info")  # Gets "events:maps:info"
    """

    _namespace: str
    _prefix: str

    def __init__(
        self,
        *args: Any,
        namespace: str = "",
        separator: str = ":",
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._namespace = namespace
        self._prefix = f"{namespace}{separator}" if namespace else ""

    @classmethod
    def from_url(
        cls,
        url: str,
        single_connection_client: bool = False,
        auto_close_connection_pool: bool | None = None,
        namespace: str = "",
        **kwargs: Any,
    ) -> Self:
        """Create a namespaced client from a URL."""
        client = super().from_url(
            url,
            single_connection_client=single_connection_client,
            auto_close_connection_pool=auto_close_connection_pool,
            **kwargs,
        )
        client._namespace = namespace
        client._prefix = f"{namespace}:" if namespace else ""
        return client

    def _prefixed(self, key: KeyT) -> str:
        """Prepend namespace prefix to a key."""
        return f"{self._prefix}{key}"

    def with_namespace(self, namespace: str) -> Self:
        """Create a new client reference with an additional namespace prefix.

        The new namespace is appended to the current prefix.
        Note: Shares the same connection pool as the parent.
        """
        new_ns = f"{self._namespace}:{namespace}" if self._namespace else namespace
        return self.__class__(
            connection_pool=self.connection_pool,
            namespace=new_ns,
        )

    @property
    def namespace(self) -> str:
        """Get the current namespace."""
        return self._namespace

    # Override key-based commands to add prefix
    # Only override methods that are actually used or commonly needed

    async def get(self, name: KeyT) -> ResponseT:
        """Get the value of a key."""
        return await super().get(self._prefixed(name))

    async def set(
        self,
        name: KeyT,
        value: EncodableT,
        ex: ExpiryT | None = None,
        px: ExpiryT | None = None,
        nx: bool = False,
        xx: bool = False,
        keepttl: bool = False,
        get: bool = False,
        exat: AbsExpiryT | None = None,
        pxat: AbsExpiryT | None = None,
    ) -> ResponseT:
        """Set the value of a key."""
        return await super().set(
            self._prefixed(name),
            value,
            ex=ex,
            px=px,
            nx=nx,
            xx=xx,
            keepttl=keepttl,
            get=get,
            exat=exat,
            pxat=pxat,
        )

    async def delete(self, *names: KeyT) -> ResponseT:
        """Delete one or more keys."""
        return await super().delete(*[self._prefixed(n) for n in names])

    async def exists(self, *names: KeyT) -> ResponseT:
        """Return the number of keys that exist."""
        return await super().exists(*[self._prefixed(n) for n in names])

    async def incr(self, name: KeyT, amount: int = 1) -> ResponseT:
        """Increment the value of a key by the given amount."""
        return await super().incr(self._prefixed(name), amount)

    async def incrby(self, name: KeyT, amount: int = 1) -> ResponseT:
        """Increment the value of a key by the given amount."""
        return await super().incrby(self._prefixed(name), amount)

    async def decr(self, name: KeyT, amount: int = 1) -> ResponseT:
        """Decrement the value of a key by the given amount."""
        return await super().decr(self._prefixed(name), amount)

    async def decrby(self, name: KeyT, amount: int = 1) -> ResponseT:
        """Decrement the value of a key by the given amount."""
        return await super().decrby(self._prefixed(name), amount)

    async def expire(
        self,
        name: KeyT,
        time: ExpiryT,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> ResponseT:
        """Set a key's time to live in seconds."""
        return await super().expire(self._prefixed(name), time, nx=nx, xx=xx, gt=gt, lt=lt)

    async def ttl(self, name: KeyT) -> ResponseT:
        """Get the time to live for a key in seconds."""
        return await super().ttl(self._prefixed(name))

    async def pttl(self, name: KeyT) -> ResponseT:
        """Get the time to live for a key in milliseconds."""
        return await super().pttl(self._prefixed(name))

    async def persist(self, name: KeyT) -> ResponseT:
        """Remove the expiration from a key."""
        return await super().persist(self._prefixed(name))

    async def setnx(self, name: KeyT, value: EncodableT) -> ResponseT:
        """Set the value of a key only if it does not exist."""
        return await super().setnx(self._prefixed(name), value)

    async def setex(self, name: KeyT, time: ExpiryT, value: EncodableT) -> ResponseT:
        """Set the value and expiration of a key."""
        return await super().setex(self._prefixed(name), time, value)

    async def getex(
        self,
        name: KeyT,
        ex: ExpiryT | None = None,
        px: ExpiryT | None = None,
        exat: AbsExpiryT | None = None,
        pxat: AbsExpiryT | None = None,
        persist: bool = False,
    ) -> ResponseT:
        """Get the value of a key and optionally set its expiration."""
        return await super().getex(self._prefixed(name), ex=ex, px=px, exat=exat, pxat=pxat, persist=persist)

    async def getdel(self, name: KeyT) -> ResponseT:
        """Get the value of a key and delete it."""
        return await super().getdel(self._prefixed(name))
