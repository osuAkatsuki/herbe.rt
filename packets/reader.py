from __future__ import annotations

import struct
from typing import Iterator
from typing import TYPE_CHECKING

from constants.packets import Packets

if TYPE_CHECKING:
    from packets.typing import PacketWrapper


def parse_header(data: bytearray) -> tuple[Packets, int]:
    header = data[:7]
    unpacked_data = struct.unpack("<HxI", header)

    return Packets(unpacked_data[0]), unpacked_data[1]  # packet id, length


class Packet:
    def __init__(self, data: bytearray) -> None:
        self.data = data

        self.packet_id: Packets = Packets(0)
        self.length: int = 0

        self.read_header()

    def read_header(self) -> None:
        self.packet_id, self.length = parse_header(self.data)

    def offset(self, count: int) -> None:
        self.data = self.data[count:]

    def read(self, count: int) -> bytearray:
        data = self.data[:count]
        self.offset(count)

        return data


class PacketArray:
    def __init__(
        self,
        data: bytearray,
        packet_map: dict[Packets, PacketWrapper],
    ) -> None:
        self.data = data
        self.packets: list[Packet] = []
        self.packet_map = packet_map

        self._split_data()

    def __iter__(self) -> Iterator[tuple[Packet, PacketWrapper]]:
        for packet in self.packets:
            handler = self.packet_map[packet.packet_id]

            yield packet, handler

    def _split_data(self) -> None:
        while self.data:
            packet_id, length = parse_header(self.data)

            if packet_id not in self.packet_map.keys():
                self.data = self.data[7 + length :]
                continue

            packet_data = self.data[: 7 + length]
            packet = Packet(packet_data)
            self.packets.append(packet)

            self.data = self.data[7 + length :]
