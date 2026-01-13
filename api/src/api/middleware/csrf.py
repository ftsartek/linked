from __future__ import annotations

from litestar.config.csrf import CSRFConfig

from config import get_settings

settings = get_settings()

csrf_config = CSRFConfig(secret=settings.csrf.secret)
