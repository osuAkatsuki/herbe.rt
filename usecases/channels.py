from __future__ import annotations

import repositories.channels


async def remove_user(channel_name: str, session_id: int) -> None:
    channel = await repositories.channels.fetch_by_name(channel_name)
    if not channel:
        return

    channel.members.remove(session_id)
    await repositories.channels.update(channel)
