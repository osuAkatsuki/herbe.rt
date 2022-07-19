from __future__ import annotations

from typing import Optional

import repositories.channels
import repositories.matches
import usecases.channels
import usecases.packets
from models.match import Match
from models.match import SlotStatus


async def enqueue_data(
    match_id: int,
    data: bytearray,
    lobby: bool = True,
    immune: Optional[list[int]] = None,
) -> None:
    match_channel = await repositories.channels.fetch_by_name(f"#multi_{match_id}")
    assert match_channel is not None

    recipients = match_channel.members
    if immune:
        for immune_id in immune:
            if immune_id in recipients:
                recipients.remove(immune_id)

    await usecases.channels.enqueue_data(match_channel, data, recipients)

    if lobby:
        lobby_channel = await repositories.channels.fetch_by_name(f"#lobby")
        assert lobby_channel is not None

        await usecases.channels.enqueue_data(lobby_channel, data)


async def start(match: Match) -> None:
    missing_map: list[int] = []

    for slot in match.slots:
        if slot.status & SlotStatus.HAS_USER:
            assert slot.session_id is not None

            if slot.status != SlotStatus.NO_MAP:
                slot.status = SlotStatus.PLAYING
            else:
                missing_map.append(slot.session_id)

    match.in_progress = True
    await enqueue_data(
        match.id,
        usecases.packets.match_start(match),
        lobby=False,
        immune=missing_map,
    )
    await repositories.matches.update(match)
