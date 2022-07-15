from __future__ import annotations

from functools import cache
from functools import lru_cache

from constants.packets import Packets
from models.channel import Channel
from models.stats import Stats
from models.user import Session
from packets.typing import f32
from packets.typing import i16
from packets.typing import i32
from packets.typing import i32_list
from packets.typing import i64
from packets.typing import Message
from packets.typing import OsuChannel
from packets.typing import PacketHandler
from packets.typing import String
from packets.typing import u8
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


@lru_cache(maxsize=4)
def notification(msg: str) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_NOTIFICATION)
    packet += String.write(msg)
    return packet.serialise()


@cache
def protocol_version(version: int) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_PROTOCOL_VERSION)
    packet += i32.write(version)
    return packet.serialise()


@cache
def bancho_privileges(priv: int) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_PRIVILEGES)
    packet += i32.write(priv)
    return packet.serialise()


@cache
def channel_info_end() -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_CHANNEL_INFO_END)
    return packet.serialise()


@cache
def restart_server(time: int) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_RESTART)
    packet += i32.write(time)
    return packet.serialise()


@cache
def menu_icon(icon_url: str, click_url: str) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_MAIN_MENU_ICON)
    packet += String.write(f"{icon_url}|{click_url}")
    return packet.serialise()


def friends_list(friends_list: set[int]) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_FRIENDS_LIST)
    packet += i32_list.write(friends_list)
    return packet.serialise()


@cache
def silence_end(time: int) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_SILENCE_END)
    packet += i32.write(time)
    return packet.serialise()


@lru_cache(maxsize=8)
def join_channel(channel: str) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_CHANNEL_JOIN_SUCCESS)
    packet += String.write(channel)
    return packet.serialise()


def channel_info(channel: Channel) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_CHANNEL_INFO)

    osu_channel = OsuChannel(channel.name, channel.description, len(channel.members))
    packet += osu_channel.serialise()

    return packet.serialise()


@lru_cache(maxsize=8)
def channel_kick(channel: str) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_CHANNEL_KICK)
    packet += String.write(channel)
    return packet.serialise()


def user_presence(session: Session, stats: Stats) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_USER_PRESENCE)

    packet += i32.write(session.id)
    packet += String.write(session.name)
    packet += u8.write(session.utc_offset + 24)
    packet += u8.write(session.geolocation.country.code)
    packet += u8.write(session.bancho_privileges | (session.status.mode.as_vn << 5))
    packet += f32.write(session.geolocation.long)
    packet += f32.write(session.geolocation.lat)
    packet += i32.write(stats.rank)

    return packet.serialise()


def user_stats(session: Session, stats: Stats) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_USER_STATS)

    if stats.pp > 0x7FFF:
        rscore = stats.pp
        pp = 0
    else:
        rscore = stats.ranked_score
        pp = stats.pp

    packet += i32.write(session.id)
    packet += u8.write(session.status.action)
    packet += String.write(session.status.action_text)
    packet += String.write(session.status.map_md5)
    packet += i32.write(session.status.mods)
    packet += u8.write(session.status.mode.as_vn)
    packet += i32.write(session.status.map_id)
    packet += i64.write(rscore)
    packet += f32.write(stats.accuracy / 100.0)
    packet += i32.write(stats.playcount)
    packet += i64.write(stats.total_score)
    packet += i32.write(stats.rank)
    packet += i16.write(pp)

    return packet.serialise()


@cache
def user_restricted() -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_ACCOUNT_RESTRICTED)
    return packet.serialise()


def send_message(message: Message) -> bytearray:
    packet = PacketWriter.from_id(Packets.CHO_SEND_MESSAGE)
    packet += message.serialise()
    return packet.serialise()
