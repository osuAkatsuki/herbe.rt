from __future__ import annotations

import struct
from typing import Awaitable
from typing import Callable
from typing import Iterator

from constants.packets import Packets
from models.user import Session


def parse_header(data: bytes) -> tuple[Packets, int]:
    header = data[:7]
    unpacked_data = struct.unpack("<HxI", header)

    return Packets(unpacked_data[0]), unpacked_data[1]  # packet id, length


class Packet:
    def __init__(self, data: bytes) -> None:
        self.data = data

        self.packet_id: Packets = Packets(0)
        self.length: int = 0

        self.read_header()

    def read_header(self) -> None:
        self.packet_id, self.length = parse_header(self.data)
        self.offset(7)

    def offset(self, count: int) -> None:
        self.data = self.data[count:]

    def read(self, count: int) -> bytes:
        data = self.data[:count]
        self.offset(count)

        return data


PacketWrapper = Callable[[Packet, Session], Awaitable[None]]


class PacketArray:
    def __init__(
        self,
        data: bytes,
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
        with memoryview(self.data) as data_view:
            while data_view:
                packet_id, length = parse_header(data_view)

                if packet_id not in self.packet_map.keys():
                    data_view = data_view[7 + length :]
                    continue

                packet_data = data_view[: 7 + length]
                packet = Packet(packet_data)
                self.packets.append(packet)

                data_view = data_view[7 + length :]
