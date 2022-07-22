from __future__ import annotations

from starlette.config import Config
from starlette.datastructures import Secret

cfg = Config(".env")


DB_DSN: Secret = cfg("DB_DSN", cast=Secret)
REDIS_DSN: Secret = cfg("REDIS_DSN", cast=Secret)

LOG_LEVEL: int = cfg("LOG_LEVEL", cast=int, default=30)

RESTRICTION_MESSAGE: str = cfg("RESTRICTION_MESSAGE")
FROZEN_MESSAGE: str = cfg("FROZEN_MESSAGE")
