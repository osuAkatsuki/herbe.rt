from __future__ import annotations

import logging

import repositories.accounts
import repositories.channels
import repositories.sessions
import services
import usecases.accounts
import usecases.packets
from constants.privileges import Privileges
from models.channel import Channel
from models.user import Session
from objects.redis_lock import RedisLock


async def enqueue_data(user_id: int, data: bytearray) -> None:
    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:queues:{user_id}",
    ):
        await services.redis.append(f"akatsuki:herbert:queues:{user_id}", data)


async def dequeue_data(user_id: int) -> bytes:
    data = b""

    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:queues:{user_id}",
    ):
        redis_data = await services.redis.get(f"akatsuki:herbert:queues:{user_id}")
        if not redis_data:
            return data

        data = bytes(redis_data)
        await services.redis.delete(f"akatsuki:herbert:queues:{user_id}")

    return data


async def join_channel(session: Session, channel: Channel) -> bool:
    if session.id in channel.members:
        return False

    if (
        not channel.public_read
        and not session.privileges & Privileges.ADMIN_MANAGE_USERS
    ):
        return False

    if channel.name == "#lobby" and not session.in_lobby:
        return False

    session.channels.add(channel.name)
    await repositories.sessions.update(session)

    channel.members.add(session.id)
    await repositories.channels.update(channel)

    await enqueue_data(session.id, usecases.packets.join_channel(channel.name))

    channel_info_packet = usecases.packets.channel_info(channel)
    if channel.temp:
        for target_id in channel.members:
            await enqueue_data(target_id, channel_info_packet)
    else:
        for target in await repositories.sessions.fetch_all():
            if (
                not channel.public_read
                and not target.privileges & Privileges.ADMIN_MANAGE_USERS
            ):
                continue

            await enqueue_data(target.id, channel_info_packet)

    logging.info(f"{session} joined {channel.name}")
    return True


async def remove_privilege(session: Session, privilege: int) -> None:
    session.privileges &= ~privilege

    await usecases.accounts.update_privileges(session)
    await repositories.sessions.update(session)
