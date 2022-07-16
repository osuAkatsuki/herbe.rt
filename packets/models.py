from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import packets.typing


class PacketModel:
    ...


class ChangeActionPacket(PacketModel):
    action: packets.typing.u8
    action_text: packets.typing.String
    map_md5: packets.typing.String
    mods: packets.typing.u32
    mode: packets.typing.u8
    map_id: packets.typing.i32


class LogoutPacket(PacketModel):
    _: packets.typing.i32
