from __future__ import annotations

from functools import cache
from functools import lru_cache
from typing import Awaitable
from typing import Callable
from typing import TypeVar

from constants.packets import Packets
from models.channel import Channel
from models.match import Match
from models.stats import Stats
from models.user import Session
from packets.models import PacketModel
from packets.typing import f32
from packets.typing import i16
from packets.typing import i32
from packets.typing import i32_list
from packets.typing import i64
from packets.typing import Message
from packets.typing import OsuChannel
from packets.typing import OsuMatch
from packets.typing import String
from packets.typing import u8
from packets.writer import PacketWriter

PacketModelType = TypeVar("PacketModelType", bound=PacketModel)
PacketHandler = Callable[[PacketModelType, Session], Awaitable[None]]
PACKETS: dict[Packets, PacketHandler] = {}


@cache
def user_id(id: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_USER_ID)
    packet += i32.write(id)
    return packet.serialise()


@cache
def version_update_forced() -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_VERSION_UPDATE_FORCED)
    return packet.serialise()


@lru_cache(maxsize=4)
def notification(msg: str) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_NOTIFICATION)
    packet += String.write(msg)
    return packet.serialise()


@cache
def protocol_version(version: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_PROTOCOL_VERSION)
    packet += i32.write(version)
    return packet.serialise()


@cache
def bancho_privileges(priv: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_PRIVILEGES)
    packet += i32.write(priv)
    return packet.serialise()


@cache
def channel_info_end() -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_CHANNEL_INFO_END)
    return packet.serialise()


@cache
def restart_server(time: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_RESTART)
    packet += i32.write(time)
    return packet.serialise()


@cache
def menu_icon(icon_url: str, click_url: str) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_MAIN_MENU_ICON)
    packet += String.write(f"{icon_url}|{click_url}")
    return packet.serialise()


def friends_list(friends_list: list[int]) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_FRIENDS_LIST)
    packet += i32_list.write(friends_list)
    return packet.serialise()


@cache
def silence_end(time: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_SILENCE_END)
    packet += i32.write(time)
    return packet.serialise()


@lru_cache(maxsize=8)
def join_channel(channel: str) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_CHANNEL_JOIN_SUCCESS)
    packet += String.write(channel)
    return packet.serialise()


def channel_info(channel: Channel) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_CHANNEL_INFO)

    if channel.name.startswith("#multi_"):
        channel_name = "#multiplayer"
    elif channel.name.startswith("#spec_"):
        channel_name = "#spectator"
    else:
        channel_name = channel.name

    osu_channel = OsuChannel(channel_name, channel.description, len(channel.members))
    packet += osu_channel.serialise()

    return packet.serialise()


@lru_cache(maxsize=8)
def channel_kick(channel: str) -> bytes:
    if channel.startswith("#multi_"):
        channel_name = "#multiplayer"
    elif channel.startswith("#spec_"):
        channel_name = "#spectator"
    else:
        channel_name = channel

    packet = PacketWriter.from_id(Packets.CHO_CHANNEL_KICK)
    packet += String.write(channel_name)
    return packet.serialise()


def user_presence(session: Session, stats: Stats) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_USER_PRESENCE)

    packet += i32.write(session.id)
    packet += String.write(session.name)
    packet += u8.write(session.utc_offset + 24)
    packet += u8.write(session.geolocation.country.code)
    packet += u8.write(session.bancho_privileges | (session.status.mode.as_vn << 5))
    packet += f32.write(session.geolocation.longitude)
    packet += f32.write(session.geolocation.latitude)
    packet += i32.write(stats.rank)

    return packet.serialise()


def user_stats(session: Session, stats: Stats) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_USER_STATS)

    if stats.pp > 0x7FFF:
        rscore = int(stats.pp)
        pp = 0
    else:
        rscore = stats.ranked_score
        pp = int(stats.pp)

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
def user_restricted() -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_ACCOUNT_RESTRICTED)
    return packet.serialise()


def send_message(message: Message) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_SEND_MESSAGE)
    packet += message.serialise()
    return packet.serialise()


@cache
def logout(user_id: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_USER_LOGOUT)

    packet += i32.write(user_id)
    packet += u8.write(0)  # ?

    return packet.serialise()


@cache
def spectator_joined(user_id: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_FELLOW_SPECTATOR_JOINED)
    packet += i32.write(user_id)
    return packet.serialise()


@cache
def host_spectator_joined(user_id: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_SPECTATOR_JOINED)
    packet += i32.write(user_id)
    return packet.serialise()


@cache
def spectator_left(user_id: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_FELLOW_SPECTATOR_LEFT)
    packet += i32.write(user_id)
    return packet.serialise()


@cache
def host_spectator_left(user_id: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_SPECTATOR_LEFT)
    packet += i32.write(user_id)
    return packet.serialise()


def spectate_frames(frames: bytes) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_SPECTATE_FRAMES)
    packet += frames
    return packet.serialise()


@cache
def cant_spectate(user_id: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_SPECTATOR_CANT_SPECTATE)
    packet += i32.write(user_id)
    return packet.serialise()


@lru_cache(maxsize=8)
def private_message_blocked(recipient_name: str) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_USER_DM_BLOCKED)
    packet += String.write(recipient_name)
    return packet.serialise()


@lru_cache(maxsize=8)
def target_silenced(recipient_name: str) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_TARGET_IS_SILENCED)
    packet += String.write(recipient_name)
    return packet.serialise()


def write_match(match: Match) -> OsuMatch:
    return OsuMatch(
        match.id,
        match.in_progress,
        match.mods,
        match.password if match.password else "",
        match.name,
        match.map_title if match.map_title else "",
        match.map_id if match.map_id else -1,
        match.map_md5 if match.map_md5 else "",
        [slot.session_id for slot in match.slots if slot.session_id],
        match.win_condition,
        match.team_type,
        match.freemod,
        match.seed,
        [slot.status for slot in match.slots],
        [slot.team for slot in match.slots],
        [slot.mods for slot in match.slots],
        match.mode,
        match.host_id,
    )


def update_match(match: Match, send_pw: bool = True) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_UPDATE_MATCH)

    osu_match = write_match(match)

    packet += osu_match.serialise(send_pw)
    return packet.serialise()


def match_start(match: Match) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_MATCH_START)

    osu_match = write_match(match)

    packet += osu_match.serialise()
    return packet.serialise()


def new_match(match: Match) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_NEW_MATCH)

    osu_match = write_match(match)

    packet += osu_match.serialise()
    return packet.serialise()


@cache
def match_join_fail() -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_MATCH_JOIN_FAIL)
    return packet.serialise()


def match_join_success(match: Match) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_MATCH_JOIN_SUCCESS)

    osu_match = write_match(match)

    packet += osu_match.serialise()
    return packet.serialise()


@cache
def dispose_match(match_id: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_DISPOSE_MATCH)
    packet += i32.write(match_id)
    return packet.serialise()


@cache
def match_transfer_host() -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_MATCH_TRANSFER_HOST)
    return packet.serialise()


@cache
def match_complete() -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_MATCH_COMPLETE)
    return packet.serialise()


@cache
def match_all_players_loaded() -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_MATCH_ALL_PLAYERS_LOADED)
    return packet.serialise()


@cache
def match_player_failed(slot_id: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_MATCH_PLAYER_FAILED)
    packet += i32.write(slot_id)
    return packet.serialise()


@cache
def match_player_skipped(user_id: int) -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_MATCH_PLAYER_SKIPPED)
    packet += i32.write(user_id)
    return packet.serialise()


@cache
def match_skip() -> bytes:
    packet = PacketWriter.from_id(Packets.CHO_MATCH_SKIP)
    return packet.serialise()


def match_invite(sender: Session, match: Match, target_name: str) -> bytes:
    invite_text = f"Join my multiplayer match: {match.embed}"

    packet = PacketWriter.from_id(Packets.CHO_MATCH_INVITE)
    packet += Message.write(
        sender.name,
        invite_text,
        target_name,
        sender.id,
    )

    return packet.serialise()
