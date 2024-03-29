from __future__ import annotations

import logging
from typing import Optional

import repositories.accounts
import repositories.channels
import repositories.matches
import repositories.sessions
import services
import usecases.accounts
import usecases.channels
import usecases.packets
import usecases.sessions
from constants.privileges import Privileges
from models.channel import Channel
from models.match import Match
from models.match import MatchTeam
from models.match import MatchTeamType
from models.match import SlotStatus
from models.user import Session
from objects.redis_lock import RedisLock
from packets.typing import Message


async def enqueue_data(user_id: int, data: bytes) -> None:
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


async def leave_channel(session: Session, channel_name: str) -> None:
    await usecases.channels.remove_user(channel_name, session.id)
    session.channels.remove(channel_name)
    await repositories.sessions.update(session)


async def remove_privilege(session: Session, privilege: int) -> None:
    session.privileges &= ~privilege

    await usecases.accounts.update_privileges(session)
    await repositories.sessions.update(session)


async def logout(session: Session) -> None:
    if session.spectating:
        await remove_spectator(session.spectating, session)

    for channel in session.channels:
        await leave_channel(session, channel)

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


async def add_friend(session: Session, target_session: Session) -> None:
    if target_session.id in session.friends:
        logging.warning(
            f"{session!r} tried to add {target_session!r}, but they are already friends",
        )
        return

    session.friends.append(target_session.id)
    await services.write_database.execute(
        "INSERT INTO users_relationships (user1, user2) VALUES (:session_id, :target_session_id)",
        {"session_id": session.id, "target_session_id": target_session.id},
    )

    logging.info(f"{session!r} added {target_session!r} as a friend")


async def remove_friend(session: Session, target_session: Session) -> None:
    if target_session.id not in session.friends:
        logging.warning(
            f"{session!r} tried to remove {target_session!r}, but they are not friends",
        )
        return

    session.friends.remove(target_session.id)
    await services.write_database.execute(
        "DELETE FROM users_relationships WHERE user1 = :session_id AND user2 = :target_session_id",
        {"session_id": session.id, "target_session_id": target_session.id},
    )

    logging.info(f"{session!r} removed {target_session!r} from their friend list")


async def join_match(
    session: Session,
    match: Match,
    password: Optional[str] = None,
) -> bool:
    if session.match:
        logging.warning(
            f"{session!r} tried to join match ID {match.id} while already being in match ID {session.match}",
        )
        await enqueue_data(session.id, usecases.packets.match_join_fail())
        return False

    if session.id in match.tourney_clients:
        await enqueue_data(session.id, usecases.packets.match_join_fail())
        return False

    if session.id == match.host_id:
        slot_id = 0
    else:
        if match.password and password != match.password:
            await enqueue_data(session.id, usecases.packets.match_join_fail())
            return False

        if slot_id := match.get_next_free_slot_idx() is None:
            await enqueue_data(session.id, usecases.packets.match_join_fail())
            return False

    match_channel = await repositories.channels.fetch_by_name(f"#multi_{match.id}")
    assert match_channel is not None

    await join_channel(session, match_channel)

    if "#lobby" in session.channels:
        await leave_channel(session, "#lobby")

    slot = match.slots[slot_id]

    if match.team_type in (MatchTeamType.TEAM_VS, MatchTeamType.TAG_TEAM_VS):
        slot.team = MatchTeam.RED

    slot.status = SlotStatus.NOT_READY
    slot.session_id = session.id

    session.match = match.id

    await enqueue_data(session.id, usecases.packets.match_join_success(match))
    await repositories.matches.update(match)

    logging.info(f"{session!r} joined match {match!r}")
    return True


async def leave_match(session: Session, match: Match) -> None:
    if not session.match:
        logging.warning(f"{session!r} tried to leave a match without being in one")
        return

    slot = match.get_slot(session.id)
    assert slot is not None

    if slot.status == SlotStatus.LOCKED:
        new_status = SlotStatus.LOCKED
    else:
        new_status = SlotStatus.OPEN

    slot.reset(new_status)

    await leave_channel(session, f"#multi_{match.id}")

    if all(slot.empty for slot in match.slots):
        logging.info(f"Disposing match {match!r}")

        await repositories.matches.delete(match)

        lobby = await repositories.channels.fetch_by_name("#lobby")
        assert lobby is not None

        await usecases.channels.enqueue_data(
            lobby,
            usecases.packets.dispose_match(match.id),
        )
    else:
        if session.id == match.host_id:
            for slot in match.slots:
                if slot.status & SlotStatus.HAS_USER:
                    assert slot.session_id is not None
                    match.host_id = slot.session_id

                    await enqueue_data(
                        slot.session_id,
                        usecases.packets.match_transfer_host(),
                    )

                    break

        if session.id in match.refs:
            match.refs.remove(session.id)

        await repositories.matches.update(match)

    session.match = None

    logging.info(f"{session!r} left match {match!r}")
