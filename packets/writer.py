from __future__ import annotations

from packets.typing import i16
from packets.typing import u32
from packets.typing import u8


class PacketWriter:
    def __init__(self, data: bytearray, packet_id: int) -> None:
        self.data = data
        self.packet_id = packet_id

    @classmethod
    def from_id(self, packet_id: int) -> PacketWriter:
        return PacketWriter(bytearray(), packet_id)

    def __iadd__(self, other: bytearray) -> PacketWriter:
        self.write(other)
        return self

    def write(self, data: bytearray) -> None:
        self.data += data

    def serialise(self) -> bytearray:
        return_data = bytearray()

        return_data += i16.write(self.packet_id)
        return_data += u8.write(0)  # padding byte

        # actual packet data
        return_data += u32.write(len(self.data))
        return_data += self.data

        return return_data
