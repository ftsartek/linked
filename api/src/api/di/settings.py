from config import Settings, get_settings


async def provide_settings() -> Settings:
    """Provide application settings for dependency injection."""
    return get_settings()
