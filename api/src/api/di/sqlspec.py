from __future__ import annotations

from sqlspec.extensions.litestar import SQLSpecPlugin

from database import sql

sqlspec_plugin = SQLSpecPlugin(sqlspec=sql)
