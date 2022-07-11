from __future__ import annotations

from starlette.config import Config
from starlette.datastructures import Secret

cfg = Config(".env")

SERVER_DOMAIN: str = cfg("SERVER_DOMAIN")
SERVER_PORT: int = cfg("SERVER_PORT", cast=int)

DB_DSN: Secret = cfg("DB_DSN", cast=Secret)
REDIS_DSN: Secret = cfg("REDIS_DSN", cast=Secret)

LOG_LEVEL: int = cfg("LOG_LEVEL", cast=int, default=30)
