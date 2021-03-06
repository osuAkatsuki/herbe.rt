from __future__ import annotations

from typing import Optional
from typing import Sequence

import repositories.channels
import repositories.sessions
import usecases.packets
import usecases.sessions
from constants.privileges import Privileges
from models.channel import Channel
from models.user import Session
from packets.typing import Message


async def remove_user(channel_name: str, session_id: int) -> None:
    channel = await repositories.channels.fetch_by_name(channel_name)
    if not channel:
        return

    channel.members.remove(session_id)
    if not channel.members:
        await repositories.channels.delete(channel)

        channel_info_packet = usecases.packets.channel_info(channel)

        if channel.temp:
            for target_id in channel.members:
                await usecases.sessions.enqueue_data(target_id, channel_info_packet)
        else:
            for target_session in await repositories.sessions.fetch_all():
                if (
                    channel.public_read
                    or target_session.privileges & Privileges.ADMIN_MANAGE_USERS
                    or target_session in channel.members
                ):
                    await usecases.sessions.enqueue_data(
                        target_session.id,
                        channel_info_packet,
                    )
    else:
        await repositories.channels.update(channel)


async def enqueue_data(
    channel: Channel,
    data: bytes,
    recipient_ids: Optional[Sequence[int]] = None,
) -> None:
    if recipient_ids is None:
        recipient_ids = channel.members

    for recipient_id in recipient_ids:
        await usecases.sessions.enqueue_data(recipient_id, data)


async def send_message(
    channel: Channel,
    message_content: str,
    sender: Session,
    to_self: bool = False,
) -> None:
    to_send = channel.members[:]
    if not to_self:
        to_send.remove(sender.id)

    await send_message_selective(channel, message_content, sender, to_send)


async def send_message_selective(
    channel: Channel,
    message_content: str,
    sender: Session,
    recipients: Sequence[int],
) -> None:
    if channel.name.startswith("#multi_"):
        channel_name = "#multiplayer"
    elif channel.name.startswith("#spec_"):
        channel_name = "#spectator"
    else:
        channel_name = channel.name

    message_packet = usecases.packets.send_message(
        Message(
            sender.name,
            message_content,
            channel_name,
            sender.id,
        ),
    )

    await enqueue_data(channel, message_packet, recipients)
