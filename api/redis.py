from __future__ import annotations

import asyncio
from typing import Awaitable
from typing import Callable
from typing import Optional
from typing import TypedDict

import aioredis.client

import services

PUBSUB_HANDLER = Callable[[str], Awaitable[None]]
PUBSUBS: dict[str, PUBSUB_HANDLER] = {}


def register_pubsub(channel: str):
    def decorator(handler: PUBSUB_HANDLER):
        PUBSUBS[channel] = handler

    return decorator


class RedisMessage(TypedDict):
    channel: bytes
    data: bytes


async def loop_pubsubs(pubsub: aioredis.client.PubSub) -> None:
    while True:
        try:
            message: Optional[RedisMessage] = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )

            if message is not None:
                if handler := PUBSUBS.get(message["channel"].decode()):
                    await handler(message["data"].decode())

            await asyncio.sleep(0.01)
        except asyncio.TimeoutError:
            pass


async def initialise_pubsubs() -> None:
    pubsub = services.redis.pubsub()
    await pubsub.subscribe(*[channel for channel in PUBSUBS.keys()])

    pubsub_loop = asyncio.create_task(loop_pubsubs(pubsub))
    services.tasks.add(pubsub_loop)
