from __future__ import annotations

import json
from typing import Optional

import repositories.sessions
import services
import usecases.packets
import usecases.sessions
import utils
from constants.privileges import Privileges
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
    channel_dicts = (await services.redis.hgetall("akatsuki:herbert:channels")).values()
    return {Channel(**json.loads(channel_dict)) for channel_dict in channel_dicts}


async def update(channel: Channel) -> None:
    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:channels:{channel.name}",
    ):
        channel_dump = json.dumps(channel.dict())
        await services.redis.hset(
            name="akatsuki:herbert:channels",
            mapping={
                f"id_{channel.id}": channel_dump,
                f"name_{channel.name}": channel_dump,
            },
        )

        channel_info_packet = usecases.packets.channel_info(channel)
        for target in await repositories.sessions.fetch_all():
            if (
                channel.public_read
                or target.privileges & Privileges.ADMIN_MANAGE_USERS
                or target in channel.members
            ):
                await usecases.sessions.enqueue_data(target.id, channel_info_packet)
