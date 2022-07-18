from __future__ import annotations

import struct
from abc import abstractmethod
from typing import Any
from typing import Collection
from typing import Optional
from typing import Sequence

from packets.reader import Packet


def read_int(data: bytearray, signed: bool = True) -> int:
    return int.from_bytes(data, "little", signed=signed)


def read_float(data: bytearray) -> float:
    return struct.unpack("<f", data)[0]


class osuType:
    @classmethod
    @abstractmethod
    def read(cls, packet: Packet) -> Any:
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


SCOREFRAME_FMT = struct.Struct("<iBHHHHHHiHH?BB?")


class ScoreFrame(osuType):
    def __init__(
        self,
        time: int,
        id: int,
        num300: int,
        num100: int,
        num50: int,
        num_geki: int,
        num_katu: int,
        num_miss: int,
        total_score: int,
        current_combo: int,
        max_combo: int,
        perfect: bool,
        current_hp: int,
        tag_byte: int,
        score_v2: bool,
        combo_portion: Optional[float] = None,
        bonus_portion: Optional[float] = None,
    ):
        self.time = time
        self.id = id
        self.num300 = num300
        self.num100 = num100
        self.num50 = num50
        self.num_geki = num_geki
        self.num_katu = num_katu
        self.num_miss = num_miss
        self.total_score = total_score
        self.current_combo = current_combo
        self.max_combo = max_combo
        self.perfect = perfect
        self.current_hp = current_hp
        self.tag_byte = tag_byte

        self.score_v2 = score_v2

        self.combo_portion: Optional[float] = combo_portion
        self.bonus_portion: Optional[float] = bonus_portion

    @classmethod
    def read(cls, packet: Packet) -> ScoreFrame:
        # this is for speed, maybe ill write this out properly later
        data = packet.read(29)
        score_frame = ScoreFrame(*SCOREFRAME_FMT.unpack_from(data))

        if score_frame.score_v2:
            score_frame.combo_portion = f64.read(packet)
            score_frame.bonus_portion = f64.read(packet)

        return score_frame

    @classmethod
    def write(
        cls,
        time: int,
        id: int,
        num300: int,
        num100: int,
        num50: int,
        num_geki: int,
        num_katu: int,
        num_miss: int,
        total_score: int,
        current_combo: int,
        max_combo: int,
        perfect: bool,
        current_hp: int,
        tag_byte: int,
        score_v2: bool,
        combo_portion: Optional[float] = None,
        bonus_portion: Optional[float] = None,
    ):
        score_frame = ScoreFrame(
            time,
            id,
            num300,
            num100,
            num50,
            num_geki,
            num_katu,
            num_miss,
            total_score,
            current_combo,
            max_combo,
            perfect,
            current_hp,
            tag_byte,
            score_v2,
            combo_portion,
            bonus_portion,
        )

        return score_frame.serialise()

    def serialise(self) -> bytearray:
        return bytearray(
            SCOREFRAME_FMT.pack(
                self.time,
                self.id,
                self.num300,
                self.num100,
                self.num50,
                self.num_geki,
                self.num_katu,
                self.num_miss,
                self.total_score,
                self.current_combo,
                self.max_combo,
                self.perfect,
                self.current_hp,
                self.tag_byte,
                self.score_v2,
            ),
        )


class ReplayFrame(osuType):
    def __init__(
        self,
        button_state: int,
        taiko_byte: int,
        x: float,
        y: float,
        time: int,
    ):
        self.button_state = button_state
        self.taiko_byte = taiko_byte
        self.x = x
        self.y = y
        self.time = time

    @classmethod
    def read(cls, packet: Packet) -> ReplayFrame:
        return ReplayFrame(
            button_state=u8.read(packet),
            taiko_byte=u8.read(packet),
            x=f32.read(packet),
            y=f32.read(packet),
            time=i32.read(packet),
        )

    @classmethod
    def write(
        cls,
        button_state: int,
        taiko_byte: int,
        x: float,
        y: float,
        time: int,
    ):
        frame = ReplayFrame(button_state, taiko_byte, x, y, time)
        return frame.serialise()

    def serialise(self) -> bytearray:
        data = bytearray(u8.write(self.button_state))

        data += u8.write(self.taiko_byte)
        data += u8.write(self.taiko_byte)
        data += f32.write(self.x)
        data += f32.write(self.y)
        data += i32.write(self.time)

        return data


class ReplayFrameBundle(osuType):
    def __init__(
        self,
        frames: list[ReplayFrame],
        score_frame: ScoreFrame,
        action: int,
        extra: int,  # ?
        sequence: int,  # ?
        raw_data: bytearray,
    ) -> None:
        self.frames = frames
        self.score_frame = score_frame
        self.action = action
        self.extra = extra
        self.sequence = sequence
        self.raw_data = raw_data

    @classmethod
    def read(cls, packet: Packet) -> ReplayFrameBundle:
        raw_data = packet.data[: packet.length]  # slice to copy

        extra = i32.read(packet)
        frame_count = u16.read(packet)
        frames = [ReplayFrame.read(packet) for _ in range(frame_count)]
        action = u8.read(packet)
        score_frame = ScoreFrame.read(packet)
        sequence = u16.read(packet)

        return ReplayFrameBundle(frames, score_frame, action, extra, sequence, raw_data)

    @classmethod
    def write(
        cls,
        frames: list[ReplayFrame],
        score_frame: ScoreFrame,
        action: int,
        extra: int,  # ?
        sequence: int,  # ?
        raw_data: bytearray,
    ) -> bytearray:
        frame_bundle = ReplayFrameBundle(
            frames,
            score_frame,
            action,
            extra,
            sequence,
            raw_data,
        )

        return frame_bundle.serialise()

    def serialise(self) -> bytearray:
        data = bytearray(i32.write(self.extra))

        data += u16.write(len(self.frames))
        for frame in self.frames:
            data += frame.serialise()

        data += self.score_frame.serialise()
        data += u16.write(self.sequence)
        data += u8.write(self.action)

        return data
