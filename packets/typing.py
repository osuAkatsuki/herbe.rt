from __future__ import annotations

import struct
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Collection
from typing import Sequence
from typing import TypeVar

from models.user import Session
from packets.models import PacketModel
from packets.reader import Packet

PacketWrapper = Callable[[Packet, Session], Awaitable[None]]
PacketModelType = TypeVar("PacketModelType", bound=PacketModel)
PacketHandler = Callable[[PacketModelType, Session], Awaitable[None]]


def read_int(data: bytearray, signed: bool = True) -> int:
    return int.from_bytes(data, "little", signed=signed)


def read_float(data: bytearray) -> float:
    return struct.unpack("<f", data)[0]


class osuType:
    @classmethod
    def read(cls, packet: Packet) -> Any:
        ...

    @classmethod
    def write(cls, data: Any) -> bytearray:
        ...


class i8(osuType, int):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(1))

    @classmethod
    def write(cls, data: int) -> bytearray:
        return bytearray(struct.pack("<b", data))


class u8(osuType, int):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(1), signed=False)

    @classmethod
    def write(cls, data: int) -> bytearray:
        return bytearray(struct.pack("<B", data))


class i16(osuType, int):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(2))

    @classmethod
    def write(cls, data: int) -> bytearray:
        return bytearray(struct.pack("<h", data))


class u16(osuType, int):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(2), signed=False)

    @classmethod
    def write(cls, data: int) -> bytearray:
        return bytearray(struct.pack("<H", data))


class i32(osuType, int):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(4))

    @classmethod
    def write(cls, data: int) -> bytearray:
        return bytearray(struct.pack("<i", data))


class i32_list(osuType, Sequence[int]):
    @classmethod
    def read(cls, packet: Packet) -> Collection[int]:
        length = i16.read(packet)
        return struct.unpack(
            f"<{'I' * length}",
            packet.read(length * 4),
        )

    @classmethod
    def write(cls, data: Collection[int]) -> bytearray:
        buffer = bytearray(len(data).to_bytes(2, "little"))

        for item in data:
            buffer += item.to_bytes(4, "little")

        return buffer


class u32(osuType, int):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(4), signed=False)

    @classmethod
    def write(cls, data: int) -> bytearray:
        return bytearray(struct.pack("<I", data))


class f32(osuType, float):
    @classmethod
    def read(cls, packet: Packet) -> float:
        return read_float(packet.read(4))

    @classmethod
    def write(cls, data: float) -> bytearray:
        return bytearray(struct.pack("<f", data))


class i64(osuType, int):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(8))

    @classmethod
    def write(cls, data: int) -> bytearray:
        return bytearray(struct.pack("<q", data))


class f64(osuType, float):
    @classmethod
    def read(cls, packet: Packet) -> float:
        return read_float(packet.read(8))

    @classmethod
    def write(cls, data: float) -> bytearray:
        return bytearray(struct.pack("<d", data))


class String(osuType, str):
    @classmethod
    def read(cls, packet: Packet) -> str:
        if u8.read(packet) != 0x0B:
            return ""

        length = shift = 0

        while True:
            body = u8.read(packet)

            length |= (body & 0b01111111) << shift
            if (body & 0b10000000) == 0:
                break

            shift += 7

        return packet.read(length).decode()

    @classmethod
    def write(cls, data: str) -> bytearray:
        encoded_string = data.encode()
        length = len(encoded_string)

        if length == 0:
            return bytearray(b"\x00")

        buffer = bytearray(b"\x0b")
        val = length

        while True:
            buffer.append(val & 0x7F)
            val >>= 7

            if val != 0:
                buffer[-1] |= 0x80
            else:
                break

        buffer += encoded_string
        return buffer


class Message(osuType):
    def __init__(
        self,
        sender_username: str,
        content: str,
        recipient_username: str,
        sender_id: int,
    ) -> None:
        self.sender_username = sender_username
        self.content = content
        self.recipient_username = recipient_username
        self.sender_id = sender_id

    @classmethod
    def read(cls, packet: Packet) -> Message:
        return Message(
            sender_username=String.read(packet),
            content=String.read(packet),
            recipient_username=String.read(packet),
            sender_id=i32.read(packet),
        )

    @classmethod
    def write(
        cls,
        sender_username: str,
        content: str,
        recipient_username: str,
        sender_id: int,
    ) -> bytearray:
        message = Message(sender_username, content, recipient_username, sender_id)

        return message.serialise()

    def serialise(self) -> bytearray:
        data = bytearray(String.write(self.sender_username))

        data += String.write(self.content)
        data += String.write(self.recipient_username)
        data += i32.write(self.sender_id)

        return data


class OsuChannel(osuType):
    def __init__(
        self,
        name: str,
        topic: str,
        player_count: int,
    ):
        self.name = name
        self.topic = topic
        self.player_count = player_count

    @classmethod
    def read(cls, packet: Packet) -> OsuChannel:
        return OsuChannel(
            name=String.read(packet),
            topic=String.read(packet),
            player_count=i32.read(packet),
        )

    @classmethod
    def write(
        cls,
        name: str,
        topic: str,
        player_count: int,
    ) -> bytearray:
        channel = OsuChannel(name, topic, player_count)

        return channel.serialise()

    def serialise(self) -> bytearray:
        data = bytearray(String.write(self.name))

        data += String.write(self.topic)
        data += i32.write(self.player_count)

        return data
