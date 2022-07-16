from __future__ import annotations

from typing import Sequence

import repositories.channels
import usecases.packets
import usecases.sessions
from models.channel import Channel
from models.user import Session
from packets.typing import Message


async def remove_user(channel_name: str, session_id: int) -> None:
    channel = await repositories.channels.fetch_by_name(channel_name)
    if not channel:
        return

    channel.members.remove(session_id)
    await repositories.channels.update(channel)


async def send_message(
    channel: Channel,
    message_content: str,
    sender: Session,
    to_self: bool = False,
) -> None:
    to_send = channel.members[:]
    if not to_self:
        to_send.remove(sender.id)


async def send_message_selective(
    channel_name: str,
    message_content: str,
    sender: Session,
    recipients: Sequence[int],
) -> None:
    message_packet = usecases.packets.send_message(
        Message(
            sender.name,
            message_content,
            channel_name,
            sender.id,
        ),
    )

    for recipient_id in recipients:
        await usecases.sessions.enqueue_data(recipient_id, message_packet)
