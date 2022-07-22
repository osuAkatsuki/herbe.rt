from __future__ import annotations

from starlette.config import Config

cfg = Config(".env")

READ_DB_USER = cfg('READ_DB_USER')
READ_DB_PASS = cfg('READ_DB_PASS')
READ_DB_HOST = cfg('READ_DB_HOST')
READ_DB_PORT = cfg('READ_DB_PORT', cast=int)
READ_DB_NAME = cfg('READ_DB_NAME')
READ_DB_DSN = 'postgresql://{}:{}@{}:{}/{}?sslmode=prefer'.format(
    READ_DB_USER, READ_DB_PASS, READ_DB_HOST, READ_DB_PORT, READ_DB_NAME
)

WRITE_DB_USER = cfg('WRITE_DB_USER')
WRITE_DB_PASS = cfg('WRITE_DB_PASS')
WRITE_DB_HOST = cfg('WRITE_DB_HOST')
WRITE_DB_PORT = cfg('WRITE_DB_PORT', cast=int)
WRITE_DB_NAME = cfg('WRITE_DB_NAME')
WRITE_DB_DSN = 'postgresql://{}:{}@{}:{}/{}?sslmode=prefer'.format(
    WRITE_DB_USER, WRITE_DB_PASS, WRITE_DB_HOST, WRITE_DB_PORT, WRITE_DB_NAME
)

REDIS_HOST = cfg('REDIS_HOST')
REDIS_PORT = cfg('REDIS_PORT', cast=int)
REDIS_DSN = 'redis://{}:{}'.format(REDIS_HOST, REDIS_PORT)

LOG_LEVEL = cfg("LOG_LEVEL", cast=int, default=30)

RESTRICTION_MESSAGE = cfg(
    "RESTRICTION_MESSAGE",
    default="Your account is currently in restricted mode.",
)
FROZEN_MESSAGE = cfg(
    "FROZEN_MESSAGE",
    default="Your account is currently frozen, and will be restricted in {time_until_restriction}.",
)
