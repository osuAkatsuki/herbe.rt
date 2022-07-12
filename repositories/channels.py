from __future__ import annotations

import json
from typing import Optional

import services
import utils
from models.channel import Channel
from objects.redis_lock import RedisLock


async def fetch_by_id(id: int) -> Optional[Channel]:
    channel_dict = await services.redis.hget("akatsuki:herbert:channels", f"id_{id}")
    if not channel_dict:
        return None

    return Channel(**json.loads(channel_dict))


async def fetch_by_name(name: str) -> Optional[Channel]:
    channel_dict = await services.redis.hget(
        "akatsuki:herbert:channels",
        f"name_{utils.make_safe_name(name)}",
    )
    if not channel_dict:
        return None

    return Channel(**json.loads(channel_dict))


async def fetch_all() -> set[Channel]:
    channel_dicts = await services.redis.hgetall("akatsuki:herbert:channels")
    return {Channel(**json.loads(channel_dict)) for channel_dict in channel_dicts}


async def update(channel: Channel) -> None:
    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:channels:{channel.name}",
    ):
        for key in (f"id_{channel.id}", f"name_{channel.name}"):
            await services.redis.hset(
                "akatsuki:herbert:channels",
                key,
                json.dumps(channel.dict()),
            )
