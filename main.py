#!/usr/bin/env python3.10
from __future__ import annotations

import logging

import uvicorn  # type: ignore[import]
import uvloop

import settings

uvloop.install()

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(message)s",
)


def main() -> int:
    uvicorn.run(
        "api.init_api:app",
        reload=settings.LOG_LEVEL == 10,  # log level 10 == debug
        log_level=settings.LOG_LEVEL,
        server_header=False,
        date_header=False,
        host="127.0.0.1",
        port=80,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
