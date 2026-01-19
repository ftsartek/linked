from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlspec.adapters.asyncpg.driver import AsyncpgDriver
from sqlspec.extensions.litestar import SQLSpecPlugin

from database import db_config, sql

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar.datastructures import State
    from litestar.types import Scope

sqlspec_plugin = SQLSpecPlugin(sqlspec=sql)


# TODO: Replace with sqlspec_plugin.provide_request_session_async() once available upstream.
# See: https://github.com/litestar-org/sqlspec - provide_request_session_async will handle
# connection creation from scope automatically.
@asynccontextmanager
async def provide_session_from_scope(state: State, scope: Scope) -> AsyncIterator[AsyncpgDriver]:  # noqa: ARG001
    """Provide an async database session from request scope, creating connection if needed.

    This is a temporary helper until the upstream SQLSpec plugin provides this functionality.
    It acquires a connection from the pool and yields a session, then properly releases
    the connection back to the pool when done.

    Args:
        state: The Litestar application State object.
        scope: The ASGI scope containing the request context (unused, kept for API compatibility).

    Yields:
        An AsyncpgDriver session instance.
    """
    plugin_state = sqlspec_plugin._get_plugin_state(db_config)

    pool = state.get(plugin_state.pool_key)
    if pool is None:
        raise ConnectionError("No connection or pool available to create a session from.")

    connection = await pool.acquire()
    try:
        session = plugin_state.config.driver_type(
            connection=connection,
            statement_config=plugin_state.config.statement_config,
            driver_features=plugin_state.config.driver_features,
        )
        yield session
    finally:
        await pool.release(connection)
