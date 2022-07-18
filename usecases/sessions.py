from __future__ import annotations

import logging

import repositories.accounts
import repositories.channels
import repositories.sessions
import services
import usecases.accounts
import usecases.channels
import usecases.packets
import usecases.sessions
from constants.privileges import Privileges
from models.channel import Channel
from models.user import Session
from objects.redis_lock import RedisLock
from packets.typing import Message


async def enqueue_data(user_id: int, data: bytearray) -> None:
    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:queues:{user_id}",
    ):
        await services.redis.append(f"akatsuki:herbert:queues:{user_id}", bytes(data))


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

    session.channels.append(channel.name)
    await repositories.sessions.update(session)

    channel.members.append(session.id)
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

    logging.info(f"{session!r} joined {channel.name}")
    return True


async def leave_channel(
    session: Session,
    channel_name: str,
    update_session: bool = True,
) -> None:
    await usecases.channels.remove_user(channel_name, session.id)
    session.channels.remove(channel_name)

    if update_session:
        await repositories.sessions.update(session)


async def remove_privilege(session: Session, privilege: int) -> None:
    session.privileges &= ~privilege

    await usecases.accounts.update_privileges(session)
    await repositories.sessions.update(session)


async def logout(session: Session) -> None:
    # TODO: remove spectating once implemented

    for channel in session.channels:
        await leave_channel(session, channel, update_session=False)

    await dequeue_data(session.id)  # clear session data
    await repositories.sessions.delete(session)
    if session.privileges & Privileges.USER_PUBLIC:
        await repositories.sessions.enqueue_data(usecases.packets.logout(session.id))

    logging.info(f"{session!r} logged out")


async def add_spectator(host: Session, spectator: Session) -> None:
    spectator_channel_name = f"#spec_{host.id}"
    if not (
        spectator_channel := await repositories.channels.fetch_by_name(
            spectator_channel_name,
        )
    ):
        spectator_channel = Channel(
            name=spectator_channel_name,
            description=f"Spectator channel for {host.name}",
            public_read=True,
            public_write=True,
            temp=True,
            hidden=True,
            members=[],
        )

        await join_channel(host, spectator_channel)

    await join_channel(spectator, spectator_channel)

    fellow_joined = usecases.packets.spectator_joined(spectator.id)
    for host_spectator in host.spectators:
        await enqueue_data(host_spectator, fellow_joined)
        await enqueue_data(
            spectator.id,
            usecases.packets.spectator_joined(host_spectator),
        )

    await enqueue_data(host.id, usecases.packets.host_spectator_joined(spectator.id))

    host.spectators.append(spectator.id)
    spectator.spectating = host.id

    await repositories.sessions.update(host)
    await repositories.sessions.update(spectator)

    logging.info(f"{spectator!r} started spectating {host!r}")


async def remove_spectator(host_id: int, spectator: Session) -> None:
    host_session = await repositories.sessions.fetch_by_id(host_id)
    if not host_session:
        return

    host_session.spectators.remove(spectator.id)

    spectator_channel = await repositories.channels.fetch_by_name(f"#spec_{host_id}")
    buffer = bytearray()

    if spectator_channel:
        await leave_channel(spectator, spectator_channel.name)

        if not host_session.spectators:
            await leave_channel(host_session, spectator_channel.name)
        else:
            channel_info = usecases.packets.channel_info(spectator_channel)
            buffer += channel_info
            await enqueue_data(host_id, channel_info)

    buffer += usecases.packets.spectator_left(spectator.id)
    for host_spectator in host_session.spectators:
        await enqueue_data(host_spectator, buffer)

    await enqueue_data(host_id, usecases.packets.host_spectator_left(spectator.id))

    await repositories.sessions.update(host_session)
    await repositories.sessions.update(spectator)

    logging.info(f"{spectator!r} stopped spectating {host_session!r}")


async def receive_message(
    session: Session,
    message_content: str,
    sender: Session,
) -> None:
    await enqueue_data(
        session.id,
        usecases.packets.send_message(
            Message(
                sender.name,
                message_content,
                session.name,
                sender.id,
            ),
        ),
    )
