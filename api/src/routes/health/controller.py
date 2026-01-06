"""Health check endpoints."""

from __future__ import annotations

from typing import Literal

import msgspec
from litestar import Controller, get
from sqlspec import AsyncDriverAdapterBase
from valkey.asyncio import Valkey


class HealthResponse(msgspec.Struct):
    """Health check response."""

    status: Literal["healthy", "unhealthy"]


class HealthController(Controller):
    """Health check endpoints."""

    path = "/health"
    tags = ["Health"]

    @get("/")
    async def health_check(
        self,
        db_session: AsyncDriverAdapterBase,
        valkey_client: Valkey,
    ) -> HealthResponse:
        """Check health of all components (database and Valkey)."""
        try:
            # Check database
            await db_session.select_value("SELECT 1")

            # Check Valkey
            await valkey_client.ping()

            return HealthResponse(status="healthy")
        except Exception:
            return HealthResponse(status="unhealthy")
