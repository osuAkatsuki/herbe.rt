from __future__ import annotations

from fastapi import FastAPI

import api.bancho
import api.redis
import services


def init_events(app: FastAPI) -> None:
    @app.on_event("startup")
    async def on_startup() -> None:
        await services.connect_services()
        await api.redis.initialise_pubsubs()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await services.disconnect_services()


def init_api() -> FastAPI:
    app = FastAPI()
    app.include_router(api.bancho.router)

    init_events(app)

    return app


app = init_api()
