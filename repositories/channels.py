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
    channel_dict = await services.redis.hget("akatsuki:herbert:channels:id", id)
    if not channel_dict:
        return None

    return Channel(**json.loads(channel_dict))


async def fetch_by_name(name: str) -> Optional[Channel]:
    channel_dict = await services.redis.hget(
        "akatsuki:herbert:channels:name",
        utils.make_safe_name(name),
    )
    if not channel_dict:
        return None

    return Channel(**json.loads(channel_dict))


async def fetch_all() -> list[Channel]:
    channel_dicts = (
        await services.redis.hgetall("akatsuki:herbert:channels:name")
    ).values()
    return [Channel(**json.loads(channel_dict)) for channel_dict in channel_dicts]


async def update(channel: Channel) -> None:
    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:channels:{channel.name}",
    ):
        channel_dump = json.dumps(channel.dict())

        for redis_name, redis_key in (
            ("akatsuki:herbert:channels:id", channel.id),
            ("akatsuki:herbert:channels:name", channel.name),
        ):
            await services.redis.hset(
                name=redis_name,
                key=redis_key,
                value=channel_dump,
            )

        channel_info_packet = usecases.packets.channel_info(channel)
        for target in await repositories.sessions.fetch_all():
            if (
                channel.public_read
                or target.privileges & Privileges.ADMIN_MANAGE_USERS
                or target in channel.members
            ):
                await usecases.sessions.enqueue_data(target.id, channel_info_packet)


async def initialise_channels() -> None:
    if await fetch_all():
        return

    db_channels = await services.database.fetch_all(
        "SELECT id, name, description, public_read, public_write, temp, hidden FROM bancho_channels",
    )
    for db_channel in db_channels:
        channel_info = {
            "id": db_channel["id"],
            "name": db_channel["name"],
            "description": db_channel["description"],
            "public_read": db_channel["public_read"],
            "public_write": db_channel["public_write"],
            "temp": db_channel["temp"],
            "hidden": db_channel["hidden"],
            "members": [],
        }

        channel = Channel(**channel_info)
        await update(channel)
