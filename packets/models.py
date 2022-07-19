from __future__ import annotations

from pydantic import BaseModel
from pydantic import validator

import packets.typing


class PacketModel(BaseModel):
    ...

    class Config:
        arbitrary_types_allowed = True


class ChangeActionPacket(PacketModel):
    action: packets.typing.u8
    action_text: packets.typing.String
    map_md5: packets.typing.String
    mods: packets.typing.u32
    mode: packets.typing.u8
    map_id: packets.typing.i32


class LogoutPacket(PacketModel):
    _: packets.typing.i32


class SendMessagePacket(PacketModel):
    message: packets.typing.Message


class StatusUpdatePacket(PacketModel):
    _: bytes


class StartSpectatingPacket(PacketModel):
    target_id: packets.typing.i32


class StopSpectatingPacket(PacketModel):
    _: bytes


class SpectateFramesPacket(PacketModel):
    frame_bundle: packets.typing.ReplayFrameBundle


class CantSpectatePacket(PacketModel):
    _: bytes


class ChannelPacket(PacketModel):
    channel_name: packets.typing.String


class FriendPacket(PacketModel):
    target_id: packets.typing.i32


class StatsRequestPacket(PacketModel):
    session_ids: packets.typing.i32_list

    @validator("session_ids", pre=True)
    def valid_session_ids(cls, value) -> list[int]:
        assert isinstance(value, list)
        return value


class PresenceRequestPacket(PacketModel):
    session_ids: packets.typing.i32_list

    @validator("session_ids", pre=True)
    def valid_session_ids(cls, value) -> list[int]:
        assert isinstance(value, list)
        return value


class PresenceRequestAllPacket(PacketModel):
    _: bytes


class ToggleDMPacket(PacketModel):
    value: packets.typing.i32


class LobbyPacket(PacketModel):
    _: bytes


class MatchPacket(PacketModel):
    match: packets.typing.OsuMatch


class JoinMatchPacket(PacketModel):
    match_id: packets.typing.i32
    password: packets.typing.String


class LeaveMatchPacket(PacketModel):
    _: bytes


class ChangeSlotPacket(PacketModel):
    slot_id: packets.typing.i32


class MatchReadyPacket(PacketModel):
    _: bytes


class LockSlotPacket(PacketModel):
    slot_id: packets.typing.i32


class ChangeMatchSettingsPacket(PacketModel):
    match: packets.typing.OsuMatch


class StartMatchPacket(PacketModel):
    _: bytes


class MatchScoreUpdatePacket(PacketModel):
    data: bytes


class MatchCompletePacket(PacketModel):
    _: bytes


class MatchLoadCompletePacket(PacketModel):
    _: bytes


class MissingBeatmapPacket(PacketModel):
    _: bytes


class UnreadyPacket(PacketModel):
    _: bytes


class PlayerFailedPacket(PacketModel):
    _: bytes


class HasBeatmapPacket(PacketModel):
    _: bytes


class SkipRequestPacket(PacketModel):
    _: bytes


class TransferHostPacket(PacketModel):
    slot_id: packets.typing.i32


class ChangeTeamPacket(PacketModel):
    _: bytes


class ChangePasswordPacket(PacketModel):
    match: packets.typing.OsuMatch


class MatchInvitePacket(PacketModel):
    target_id: packets.typing.i32


class MatchInfoPacket(PacketModel):
    match_id: packets.typing.i32


class JoinMatchChannelPacket(PacketModel):
    match_id: packets.typing.i32


class LeaveMatchChannelPacket(PacketModel):
    match_id: packets.typing.i32


class UpdatePresencePacket(PacketModel):
    value: packets.typing.i32


class SetAwayMessagePacket(PacketModel):
    message: packets.typing.Message
