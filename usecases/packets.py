from __future__ import annotations

from functools import cache

from constants.packets import Packets
from packets.typing import i32
from packets.typing import PacketHandler
from packets.writer import PacketWriter

PACKETS: dict[Packets, PacketHandler] = {}


@cache
def user_id(id: int) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_USER_ID)
    packet += i32.write(id)
    return packet.serialise()


@cache
def version_update_forced() -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_VERSION_UPDATE_FORCED)
    return packet.serialise()
