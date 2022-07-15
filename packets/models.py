from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from packets.typing import i32
from packets.typing import String
from packets.typing import u32
from packets.typing import u8


class PacketModel(BaseModel):
    ...


class ChangeActionPacket(PacketModel):
    action: u8
    action_text: String
    map_md5: String
    mods: u32
    mode: u8
    map_id: i32
