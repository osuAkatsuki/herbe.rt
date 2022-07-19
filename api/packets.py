from __future__ import annotations

import importlib
import inspect
import logging
import time
import typing
from typing import Awaitable
from typing import Callable
from typing import Optional
from typing import TypeVar
from typing import Union

import packets.models
import packets.typing
import repositories.channels
import repositories.matches
import repositories.sessions
import repositories.stats
import usecases.channels
import usecases.matches
import usecases.packets
import usecases.sessions
from constants.mode import Mode
from constants.mods import Mods
from constants.packets import Packets
from constants.privileges import Privileges
from models.channel import Channel
from models.match import Match
from models.match import MatchTeam
from models.match import MatchTeamType
from models.match import SlotStatus
from models.user import Session
from packets.models import CantSpectatePacket
from packets.models import ChangeActionPacket
from packets.models import ChangeMatchSettingsPacket
from packets.models import ChangePasswordPacket
from packets.models import ChangeSlotPacket
from packets.models import ChangeTeamPacket
from packets.models import ChannelPacket
from packets.models import FriendPacket
from packets.models import HasBeatmapPacket
from packets.models import JoinMatchChannelPacket
from packets.models import JoinMatchPacket
from packets.models import LeaveMatchChannelPacket
from packets.models import LeaveMatchPacket
from packets.models import LobbyPacket
from packets.models import LockSlotPacket
from packets.models import LogoutPacket
from packets.models import MatchCompletePacket
from packets.models import MatchInfoPacket
from packets.models import MatchInvitePacket
from packets.models import MatchLoadCompletePacket
from packets.models import MatchPacket
from packets.models import MatchReadyPacket
from packets.models import MatchScoreUpdatePacket
from packets.models import MissingBeatmapPacket
from packets.models import PacketModel
from packets.models import PlayerFailedPacket
from packets.models import PresenceRequestAllPacket
from packets.models import PresenceRequestPacket
from packets.models import SendMessagePacket
from packets.models import SetAwayMessagePacket
from packets.models import SkipRequestPacket
from packets.models import SpectateFramesPacket
from packets.models import StartMatchPacket
from packets.models import StartSpectatingPacket
from packets.models import StatsRequestPacket
from packets.models import StatusUpdatePacket
from packets.models import StopSpectatingPacket
from packets.models import ToggleDMPacket
from packets.models import TransferHostPacket
from packets.models import UnreadyPacket
from packets.models import UpdatePresencePacket
from packets.reader import Packet
from packets.reader import PacketArray
from packets.typing import i32
from packets.typing import osuType


PacketWrapper = Callable[[Packet, Session], Awaitable[None]]
PacketModelType = TypeVar("PacketModelType", bound=PacketModel)
PacketHandler = Callable[[PacketModelType, Session], Awaitable[None]]

HANDLERS: dict[Packets, PacketWrapper] = {}
RESTRICTED_HANDLERS: dict[Packets, PacketWrapper] = {}

MODEL_CLASSES: dict[str, type[PacketModel]] = {}
DATA_TYPE_CLASSES: dict[str, type[osuType]] = {}


def is_valid_subclass(_obj: object, subclass: type) -> bool:
    return inspect.isclass(_obj) and issubclass(_obj, subclass)


def is_valid_packet_model(_obj: object) -> bool:
    return is_valid_subclass(_obj, PacketModel)


def is_valid_packet_data_type(_obj: object) -> bool:
    return is_valid_subclass(_obj, osuType)


def get_packet_model_from_name(class_name: str) -> Optional[type[PacketModel]]:
    if _class := MODEL_CLASSES.get(class_name):
        return _class

    class_name_split = class_name.split(".")

    if len(class_name_split) == 1:
        for name, obj in inspect.getmembers(packets.models, is_valid_packet_model):
            if inspect.isclass(obj) and name == class_name:
                assert issubclass(obj, PacketModel)

                MODEL_CLASSES[class_name] = obj
                return obj

    try:
        module = importlib.import_module(".".join(class_name_split[:-1]))
    except ValueError:
        return None

    obj = getattr(module, class_name_split[-1])
    MODEL_CLASSES[class_name] = obj

    return obj


def get_packet_data_type_from_name(class_name: str) -> Optional[type[osuType]]:
    if _class := DATA_TYPE_CLASSES.get(class_name):
        return _class

    class_name_split = class_name.split(".")

    if len(class_name_split) == 1:
        for name, obj in inspect.getmembers(packets.typing, is_valid_packet_data_type):
            if inspect.isclass(obj) and name == class_name:
                assert issubclass(obj, osuType)

                DATA_TYPE_CLASSES[class_name] = obj
                return obj

    try:
        module = importlib.import_module(".".join(class_name_split[:-1]))
    except ValueError:
        return None

    obj = getattr(module, class_name_split[-1])
    DATA_TYPE_CLASSES[class_name] = obj

    return obj


def register_packet(
    packet_id: Packets,
    allow_restricted: bool = False,
) -> Callable[[PacketHandler], PacketWrapper]:
    def decorator(handler: PacketHandler) -> PacketWrapper:
        async def wrapper(packet: Packet, session: Session) -> None:
            structure_class_name: str = handler.__annotations__["packet"]
            structure_class = get_packet_model_from_name(
                structure_class_name.strip("'"),
            )
            if not structure_class:
                raise RuntimeError(f"Invalid packet model: {structure_class_name}")

            data: dict[str, Union[bytes, PacketModel]] = {}
            for field, _type in structure_class.__annotations__.items():
                _type = typing.cast(str, _type)

                if _type == "bytes":
                    data[field] = bytes(packet.data)
                    packet.data.clear()
                else:
                    data_type_class = get_packet_data_type_from_name(_type.strip("'"))
                    if not data_type_class:
                        raise RuntimeError(f"Invalid packet data type: {_type}")

                    data[field] = data_type_class.read(packet)

            packet_model = structure_class(**data)
            return await handler(packet_model, session)

        HANDLERS[packet_id] = wrapper
        if allow_restricted:
            RESTRICTED_HANDLERS[packet_id] = wrapper

        return wrapper

    return decorator


async def handle_packet_data(data: bytearray, session: Session) -> None:
    packet_map = HANDLERS
    if not session.privileges & Privileges.USER_PUBLIC:
        packet_map = RESTRICTED_HANDLERS

    should_update = True
    packet_array = PacketArray(data, packet_map)
    for packet, handler in packet_array:
        if packet.packet_id is Packets.OSU_LOGOUT:
            should_update = False

        logging.info(f"Handled packet {packet.packet_id!r} for {session!r}")
        await handler(packet, session)

    if should_update:
        await repositories.sessions.update(session)


@register_packet(Packets.OSU_CHANGE_ACTION, allow_restricted=True)
async def change_action(packet: ChangeActionPacket, session: Session) -> None:
    session.status.action = packet.action
    session.status.action_text = packet.action_text
    session.status.map_md5 = packet.map_md5
    session.status.map_id = packet.map_id
    session.status.mods = packet.mods
    session.status.mode = Mode.from_mods(packet.mode, packet.mods)

    logging.info(f"Updated {session!r}'s status")


@register_packet(Packets.OSU_LOGOUT, allow_restricted=True)
async def user_logout(packet: LogoutPacket, session: Session) -> None:
    if (time.time() - session.login_time) < 1.0:
        # osu! has a weird tendency to log out immediately after login.
        # we've tested the times and they're generally 300-800ms, so
        # we'll block any logout request within 1 second from login.
        return

    await usecases.sessions.logout(session)


IGNORED_CHANNELS = ("#highlight", "#userlog")


@register_packet(Packets.OSU_SEND_PUBLIC_MESSAGE)
async def public_message(packet: SendMessagePacket, session: Session) -> None:
    if session.silenced:
        logging.warning(f"{session!r} tried to send a message while silenced")
        return

    msg = packet.message.content.strip()
    if not msg:
        return

    recipient = packet.message.recipient_username
    if recipient in IGNORED_CHANNELS:
        return

    if recipient == "#spectator":
        channel = await repositories.channels.fetch_by_name(
            f"#spec_{session.spectating}",
        )
    else:
        channel = await repositories.channels.fetch_by_name(recipient)

    # TODO: multi channels

    if not channel:
        logging.warning(
            f"{session!r} tried to write to non-existent channel {recipient}",
        )
        return

    if session.id not in channel.members:
        logging.warning(
            f"{session!r} tried to send a message in {recipient} without being in it",
        )
        return

    if (
        not channel.public_write
        and not session.privileges & Privileges.ADMIN_MANAGE_USERS
    ):
        return

    await usecases.channels.send_message(channel, msg, session)
    logging.info(f"{session!r} sent a message to {recipient}: {msg}")


@register_packet(Packets.OSU_REQUEST_STATUS_UPDATE, allow_restricted=True)
async def status_update(packet: StatusUpdatePacket, session: Session) -> None:
    stats = await repositories.stats.fetch(session.id, session.status.mode)
    await usecases.sessions.enqueue_data(
        session.id,
        usecases.packets.user_stats(session, stats),
    )


@register_packet(Packets.OSU_START_SPECTATING)
async def start_spectating(packet: StartSpectatingPacket, session: Session) -> None:
    if not (host_session := await repositories.sessions.fetch_by_id(packet.target_id)):
        logging.warning(
            f"{session!r} tried to spectate user ID {packet.target_id}, but they could not be found",
        )
        return

    if session.spectating and session.spectating != packet.target_id:
        await usecases.sessions.remove_spectator(session.spectating, session)

    await usecases.sessions.add_spectator(host_session, session)


@register_packet(Packets.OSU_STOP_SPECTATING)
async def stop_spectating(packet: StopSpectatingPacket, session: Session) -> None:
    if not session.spectating:
        logging.warning(
            f"{session!r} tried to stop spectating without spectating anyone",
        )
        return

    await usecases.sessions.remove_spectator(session.spectating, session)


@register_packet(Packets.OSU_SPECTATE_FRAMES)
async def spectate_frames(packet: SpectateFramesPacket, session: Session) -> None:
    if not session.spectators:
        logging.warning(
            f"{session!r} sent spectate packets while nobody is spectating them",
        )
        return

    for spectator in session.spectators:
        await usecases.sessions.enqueue_data(
            spectator,
            usecases.packets.spectate_frames(packet.frame_bundle.raw_data),
        )


@register_packet(Packets.OSU_CANT_SPECTATE)
async def cant_spectate(packet: CantSpectatePacket, session: Session) -> None:
    if not session.spectating:
        logging.warning(
            f"{session!r} sent can't spectate packet while not spectating anyone",
        )
        return

    cant_spectate_packet = usecases.packets.cant_spectate(session.id)
    await usecases.sessions.enqueue_data(session.spectating, cant_spectate_packet)

    host_session = await repositories.sessions.fetch_by_id(session.spectating)
    assert host_session is not None

    for spectator in host_session.spectators:
        await usecases.sessions.enqueue_data(spectator, cant_spectate_packet)


@register_packet(Packets.OSU_SEND_PRIVATE_MESSAGE)
async def send_private_message(packet: SendMessagePacket, session: Session) -> None:
    if session.silenced:
        logging.warning(f"{session!r} tried to send a message while silenced")
        return

    msg = packet.message.content.strip()
    if not msg:
        return

    recipient = packet.message.recipient_username
    if not (recipient_session := await repositories.sessions.fetch_by_name(recipient)):
        logging.warning(f"{session!r} tried to DM {recipient} while they are offline")
        return

    if (
        recipient_session.friend_only_dms
        and session.id not in recipient_session.friends
    ):
        await usecases.sessions.enqueue_data(
            session.id,
            usecases.packets.private_message_blocked(recipient),
        )

    if recipient_session.silenced:
        await usecases.sessions.enqueue_data(
            session.id,
            usecases.packets.target_silenced(recipient),
        )

    await usecases.sessions.receive_message(recipient_session, msg, session)


@register_packet(Packets.OSU_CHANNEL_JOIN, allow_restricted=True)
async def join_channel(packet: ChannelPacket, session: Session) -> None:
    if packet.channel_name in IGNORED_CHANNELS:
        return

    if packet.channel_name == "#spectator" and session.spectating:
        channel = await repositories.channels.fetch_by_name(
            f"#spec_{session.spectating}",
        )
    else:
        channel = await repositories.channels.fetch_by_name(packet.channel_name)

    if not channel:
        logging.warning(
            f"{session!r} tried to join non-existent channel {packet.channel_name}",
        )
        return

    if session in channel.members:
        logging.warning(
            f"{session!r} tried to join {channel.name}, but they are already in it",
        )
        return

    await usecases.sessions.join_channel(session, channel)


@register_packet(Packets.OSU_CHANNEL_PART, allow_restricted=True)
async def leave_channel(packet: ChannelPacket, session: Session) -> None:
    if packet.channel_name in IGNORED_CHANNELS:
        return

    if packet.channel_name == "#spectator" and session.spectating:
        channel = await repositories.channels.fetch_by_name(
            f"#spec_{session.spectating}",
        )
    else:
        channel = await repositories.channels.fetch_by_name(packet.channel_name)

    if not channel:
        logging.warning(
            f"{session!r} tried to leave non-existent channel {packet.channel_name}",
        )
        return

    if session not in channel.members:
        logging.warning(
            f"{session!r} tried to leave {packet.channel_name}, but they are not in it",
        )
        return

    await usecases.sessions.leave_channel(session, packet.channel_name)


@register_packet(Packets.OSU_FRIEND_ADD)
async def add_friend(packet: FriendPacket, session: Session) -> None:
    target_session = await repositories.sessions.fetch_by_id(packet.target_id)
    if not target_session:
        logging.warning(
            f"{session!r} tried to friend user ID {packet.target_id}, but they are not online",
        )
        return

    await usecases.sessions.add_friend(session, target_session)


@register_packet(Packets.OSU_FRIEND_REMOVE)
async def remove_friend(packet: FriendPacket, session: Session) -> None:
    target_session = await repositories.sessions.fetch_by_id(packet.target_id)
    if not target_session:
        logging.warning(
            f"{session!r} tried to remove user ID {packet.target_id} from their friends list, but they are not online",
        )
        return

    await usecases.sessions.remove_friend(session, target_session)


@register_packet(Packets.OSU_USER_STATS_REQUEST, allow_restricted=True)
async def stats_request(packet: StatsRequestPacket, session: Session) -> None:
    buffer = bytearray()

    for target_session in await repositories.sessions.fetch_all():
        if target_session not in packet.session_ids:
            continue

        if not (
            target_session.privileges & Privileges.USER_PUBLIC
            or target_session.id == session.id
        ):
            continue

        target_stats = await repositories.stats.fetch(
            target_session.id,
            target_session.status.mode,
        )

        buffer += usecases.packets.user_stats(target_session, target_stats)

    await usecases.sessions.enqueue_data(
        session.id,
        buffer,
    )


@register_packet(Packets.OSU_USER_PRESENCE_REQUEST, allow_restricted=True)
async def presence_request(packet: PresenceRequestPacket, session: Session) -> None:
    buffer = bytearray()

    for target_session in await repositories.sessions.fetch_all():
        if target_session not in packet.session_ids:
            continue

        if not (
            target_session.privileges & Privileges.USER_PUBLIC
            or target_session.id == session.id
        ):
            continue

        target_stats = await repositories.stats.fetch(
            target_session.id,
            target_session.status.mode,
        )

        buffer += usecases.packets.user_presence(target_session, target_stats)

    await usecases.sessions.enqueue_data(
        session.id,
        buffer,
    )


@register_packet(Packets.OSU_USER_PRESENCE_REQUEST_ALL)
async def presence_request_all(
    packet: PresenceRequestAllPacket,
    session: Session,
) -> None:
    buffer = bytearray()

    for target_session in await repositories.sessions.fetch_all():
        if not (
            target_session.privileges & Privileges.USER_PUBLIC
            or target_session.id == session.id
        ):
            continue

        target_stats = await repositories.stats.fetch(
            target_session.id,
            target_session.status.mode,
        )

        buffer += usecases.packets.user_presence(target_session, target_stats)

    await usecases.sessions.enqueue_data(
        session.id,
        buffer,
    )


@register_packet(Packets.OSU_TOGGLE_BLOCK_NON_FRIEND_DMS)
async def toggle_dms(packet: ToggleDMPacket, session: Session) -> None:
    session.friend_only_dms = packet.value == 1


@register_packet(Packets.OSU_JOIN_LOBBY)
async def join_lobby(packet: LobbyPacket, session: Session) -> None:
    session.in_lobby = True

    for match in await repositories.matches.fetch_all():
        await usecases.sessions.enqueue_data(
            session.id,
            usecases.packets.new_match(match),
        )


@register_packet(Packets.OSU_PART_LOBBY)
async def leave_lobby(packet: LobbyPacket, session: Session) -> None:
    session.in_lobby = False


@register_packet(Packets.OSU_CREATE_MATCH)
async def create_match(packet: MatchPacket, session: Session) -> None:
    if session.silenced:
        await usecases.sessions.enqueue_data(
            session.id,
            usecases.packets.match_join_fail()
            + usecases.packets.notification(
                "Multiplayer is not available while silenced.",
            ),
        )
        return

    matches = await repositories.matches.fetch_all()
    next_id = max(match.id for match in matches) + 1

    match = Match(
        id=next_id,
        name=packet.match.name,
        host_id=session.id,
        mods=session.status.mods,
        mode=session.status.mode,
        map_id=packet.match.map_id,
        map_md5=packet.match.map_md5,
        map_title=packet.match.map_name,
        freemod=packet.match.freemod,
        password=packet.match.password,
        seed=packet.match.seed,
    )

    match_channel = Channel(
        name=f"#multi_{match.id}",
        description=f"Channel for multiplayer ID {match.id}",
        public_read=True,
        public_write=True,
        temp=True,
        hidden=True,
        members=[],
    )
    await repositories.channels.update(match_channel)

    await usecases.sessions.join_match(session, match, match.password)
    logging.info(f"{session!r} created new multiplayer match {match!r}")


@register_packet(Packets.OSU_JOIN_MATCH)
async def join_match(packet: JoinMatchPacket, session: Session) -> None:
    if session.silenced:
        await usecases.sessions.enqueue_data(
            session.id,
            usecases.packets.match_join_fail()
            + usecases.packets.notification(
                "Multiplayer is not available while silenced.",
            ),
        )
        return

    match = await repositories.matches.fetch_by_id(packet.match_id)
    if not match:
        logging.warning(
            f"{session!r} tried to join non-existent match ID {packet.match_id}",
        )

        await usecases.sessions.enqueue_data(
            session.id,
            usecases.packets.match_join_fail(),
        )
        return

    await usecases.sessions.join_match(session, match, packet.password)


@register_packet(Packets.OSU_PART_MATCH)
async def leave_match(packet: LeaveMatchPacket, session: Session) -> None:
    if not session.match:
        logging.warning(f"{session!r} tried to leave a match without being in one")
        return

    match = await repositories.matches.fetch_by_id(session.match)
    if not match:
        logging.warning(
            f"{session!r} tried to leave non-existent match ID {session.match}",
        )

        return

    await usecases.sessions.leave_match(session, match)


@register_packet(Packets.OSU_MATCH_CHANGE_SLOT)
async def change_match_slot(packet: ChangeSlotPacket, session: Session) -> None:
    if not session.match:
        return

    if 0 <= packet.slot_id < 16:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    old_slot = match.get_slot(session.id)
    assert old_slot is not None

    new_slot = match.slots[packet.slot_id]
    if new_slot.status != SlotStatus.OPEN:
        return

    new_slot.copy_from(old_slot)
    old_slot.reset()

    await repositories.matches.update(match)


@register_packet(Packets.OSU_MATCH_READY)
async def match_ready(packet: MatchReadyPacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    slot = match.get_slot(session.id)
    assert slot is not None

    slot.status = SlotStatus.READY
    await repositories.matches.update(match)


@register_packet(Packets.OSU_MATCH_LOCK)
async def lock_slot(packet: LockSlotPacket, session: Session) -> None:
    if not session.match:
        return

    if 0 <= packet.slot_id < 16:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    if session.id is not match.host_id:
        logging.warning(f"{session!r} tried to lock slot as non-host")
        return

    slot = match.get_slot(packet.slot_id)
    assert slot is not None

    if slot.status == SlotStatus.LOCKED:
        slot.status = SlotStatus.OPEN
    else:
        if slot.session_id is session.id:
            # prevent host from kicking themselves
            return

        slot.status = SlotStatus.LOCKED

    await repositories.matches.update(match)


@register_packet(Packets.OSU_MATCH_CHANGE_SETTINGS)
async def change_match_settings(
    packet: ChangeMatchSettingsPacket,
    session: Session,
) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    if session.id is not match.host_id:
        logging.warning(f"{session!r} tried to change match settings as non-host")
        return

    if packet.match.freemod != match.freemod:
        match.freemod = packet.match.freemod

        if packet.match.freemod:
            for slot in match.slots:
                if slot.status & SlotStatus.HAS_USER:
                    slot.mods = match.mods & ~Mods.SPEED_MODS

            match.mods &= Mods.SPEED_MODS
        else:
            host_slot = match.get_host_slot()
            assert host_slot is not None

            host_slot.mods &= Mods.SPEED_MODS
            match.mods |= host_slot.mods

            for slot in match.slots:
                if slot.status & SlotStatus.HAS_USER:
                    slot.mods = Mods.NOMOD

    if packet.match.map_id == -1:
        match.unready_users()
        match.last_map_id = match.map_id

        match.map_id = -1
        match.map_md5 = ""
        match.map_title = ""
    elif match.map_id == -1:
        # TODO: get/validate beatmap from api

        match.map_id = packet.match.map_id
        match.map_md5 = packet.match.map_md5
        match.map_title = packet.match.map_name
        match.mode = packet.match.mode

    if match.team_type != packet.match.team_type:
        if packet.match.team_type in (
            MatchTeamType.HEAD_TO_HEAD,
            MatchTeamType.TAG_COOP,
        ):
            new_type = MatchTeam.NEUTRAL
        else:
            new_type = MatchTeam.RED

        for slot in match.slots:
            if slot.status & SlotStatus.HAS_USER:
                slot.team = new_type

        match.team_type = packet.match.team_type

    match.win_condition = packet.match.win_condition
    match.name = packet.match.name

    await repositories.matches.update(match)


@register_packet(Packets.OSU_MATCH_START)
async def start_match(packet: StartMatchPacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    if session.id is not match.host_id:
        logging.warning(f"{session!r} tried to start match as non-host")
        return

    await usecases.matches.start(match)


@register_packet(Packets.OSU_MATCH_SCORE_UPDATE)
async def update_match_score(packet: MatchScoreUpdatePacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    buffer = bytearray(b"0\x00\x00")
    buffer += i32.write(len(packet.data))
    buffer += packet.data

    slot_idx = match.get_slot_idx(session.id)
    assert slot_idx is not None

    buffer[11] = slot_idx

    not_playing = [
        slot.session_id
        for slot in match.slots
        if slot.status & SlotStatus.HAS_USER
        and slot.status != SlotStatus.PLAYING
        and slot.session_id is not None
    ]
    await usecases.matches.enqueue_data(
        match.id,
        buffer,
        lobby=False,
        immune=not_playing,
    )


@register_packet(Packets.OSU_MATCH_COMPLETE)
async def match_complete(packet: MatchCompletePacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    slot = match.get_slot(session.id)
    assert slot is not None

    slot.status = SlotStatus.COMPLETE
    if any(slot.status == SlotStatus.PLAYING for slot in match.slots):
        return

    not_playing = [
        slot.session_id
        for slot in match.slots
        if slot.status & SlotStatus.HAS_USER
        and slot.status != SlotStatus.COMPLETE
        and slot.session_id is not None
    ]

    match.unready_users(expected=SlotStatus.COMPLETE)
    match.in_progress = False

    await usecases.matches.enqueue_data(
        match.id,
        usecases.packets.match_complete(),
        lobby=False,
        immune=not_playing,
    )
    await repositories.matches.update(match)


@register_packet(Packets.OSU_MATCH_LOAD_COMPLETE)
async def match_load_complete(
    packet: MatchLoadCompletePacket,
    session: Session,
) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    slot = match.get_slot(session.id)
    assert slot is not None

    slot.loaded = True
    if not any(
        slot
        for slot in match.slots
        if slot.status == SlotStatus.PLAYING and not slot.loaded
    ):
        not_playing = [
            slot.session_id
            for slot in match.slots
            if slot.status & SlotStatus.HAS_USER
            and slot.status != SlotStatus.PLAYING
            and slot.session_id is not None
        ]

        await usecases.matches.enqueue_data(
            match.id,
            usecases.packets.match_all_players_loaded(),
            lobby=False,
            immune=not_playing,
        )


@register_packet(Packets.OSU_MATCH_NO_BEATMAP)
async def missing_beatmap(packet: MissingBeatmapPacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    slot = match.get_slot(session.id)
    assert slot is not None

    slot.status = SlotStatus.NO_MAP
    await repositories.matches.update(match, lobby=False)


@register_packet(Packets.OSU_MATCH_NOT_READY)
async def match_unready(packet: UnreadyPacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    slot = match.get_slot(session.id)
    assert slot is not None

    slot.status = SlotStatus.NOT_READY
    await repositories.matches.update(match, lobby=False)


@register_packet(Packets.OSU_MATCH_FAILED)
async def player_failed(packet: PlayerFailedPacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    slot_idx = match.get_slot_idx(session.id)
    assert slot_idx is not None

    not_playing = [
        slot.session_id
        for slot in match.slots
        if slot.status & SlotStatus.HAS_USER
        and slot.status != SlotStatus.PLAYING
        and slot.session_id is not None
    ]

    await usecases.matches.enqueue_data(
        match.id,
        usecases.packets.match_player_failed(slot_idx),
        lobby=False,
        immune=not_playing,
    )
    await repositories.matches.update(match, lobby=False)


@register_packet(Packets.OSU_MATCH_HAS_BEATMAP)
async def has_beatmap(packet: HasBeatmapPacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    slot = match.get_slot(session.id)
    assert slot is not None

    slot.status = SlotStatus.NOT_READY
    await repositories.matches.update(match, lobby=False)


@register_packet(Packets.OSU_MATCH_SKIP_REQUEST)
async def skip_request(packet: SkipRequestPacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    slot = match.get_slot(session.id)
    assert slot is not None

    slot.skipped = True

    await usecases.matches.enqueue_data(
        match.id,
        usecases.packets.match_player_skipped(session.id),
    )

    for slot in match.slots:
        if slot.status == SlotStatus.PLAYING and not slot.skipped:
            return

    not_playing = [
        slot.session_id
        for slot in match.slots
        if slot.status & SlotStatus.HAS_USER
        and slot.status != SlotStatus.PLAYING
        and slot.session_id is not None
    ]

    await usecases.matches.enqueue_data(
        match.id,
        usecases.packets.match_skip(),
        lobby=False,
        immune=not_playing,
    )


@register_packet(Packets.OSU_MATCH_TRANSFER_HOST)
async def transfer_host(packet: TransferHostPacket, session: Session) -> None:
    if not session.match:
        return

    if 0 <= packet.slot_id < 16:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    if session.id is not match.host_id:
        logging.warning(f"{session!r} tried to transfer host as non-host")
        return

    target = match.slots[packet.slot_id].session_id
    if not target:
        logging.warning(f"{session!r} tried to transfer host to empty slot")
        return

    match.host_id = target
    await usecases.sessions.enqueue_data(
        target,
        usecases.packets.match_transfer_host(),
    )

    await repositories.matches.update(match)


@register_packet(Packets.OSU_MATCH_CHANGE_TEAM)
async def change_team(packet: ChangeTeamPacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    slot = match.get_slot(session.id)
    assert slot is not None

    if slot.team == MatchTeam.BLUE:
        slot.team = MatchTeam.RED
    else:
        slot.team = MatchTeam.BLUE

    await repositories.matches.update(match, lobby=False)


@register_packet(Packets.OSU_MATCH_CHANGE_PASSWORD)
async def change_password(packet: ChangePasswordPacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    if session.id is not match.host_id:
        logging.warning(f"{session!r} tried to change match password as non-host")
        return

    match.password = packet.match.password
    await repositories.matches.update(match)


@register_packet(Packets.OSU_MATCH_INVITE)
async def match_invite(packet: MatchInvitePacket, session: Session) -> None:
    if not session.match:
        return

    match = await repositories.matches.fetch_by_id(session.match)
    assert match is not None

    target = await repositories.sessions.fetch_by_id(packet.target_id)
    if not target:
        logging.warning(
            f"{session!r} tried to invite user ID {packet.target_id} to a match while they are offline",
        )
        return

    await usecases.sessions.enqueue_data(
        target.id,
        usecases.packets.match_invite(session, match, target.name),
    )

    logging.info(f"{session!r} invited {target!r} to their match")


@register_packet(Packets.OSU_TOURNAMENT_MATCH_INFO_REQUEST)
async def tourney_match_info(packet: MatchInfoPacket, session: Session) -> None:
    match = await repositories.matches.fetch_by_id(packet.match_id)
    assert match is not None

    await usecases.sessions.enqueue_data(
        session.id,
        usecases.packets.update_match(match, send_pw=False),
    )


@register_packet(Packets.OSU_TOURNAMENT_JOIN_MATCH_CHANNEL)
async def tourney_join_channel(
    packet: JoinMatchChannelPacket,
    session: Session,
) -> None:
    match = await repositories.matches.fetch_by_id(packet.match_id)
    assert match is not None

    if match.get_slot(session.id) is not None:
        return

    match_channel = await repositories.channels.fetch_by_name(
        f"#multi_{packet.match_id}",
    )
    assert match_channel is not None

    if (
        await usecases.sessions.join_channel(session, match_channel)
        and session.id not in match.tourney_clients
    ):
        match.tourney_clients.append(session.id)


@register_packet(Packets.OSU_TOURNAMENT_LEAVE_MATCH_CHANNEL)
async def tourney_leave_channel(
    packet: LeaveMatchChannelPacket,
    session: Session,
) -> None:
    match = await repositories.matches.fetch_by_id(packet.match_id)
    assert match is not None

    if match.get_slot(session.id) is not None:
        return

    await usecases.sessions.leave_channel(session, f"#multi_{packet.match_id}")
    match.tourney_clients.remove(session.id)


@register_packet(Packets.OSU_RECEIVE_UPDATES, allow_restricted=True)
async def update_presence(packet: UpdatePresencePacket, session: Session) -> None:
    if not 0 <= packet.value < 3:
        logging.warning(
            f"{session!r} tried to set their presence filter to {packet.value} (invalid)",
        )
        return

    session.status.presence_filter = packet.value


@register_packet(Packets.OSU_SET_AWAY_MESSAGE)
async def set_away_message(packet: SetAwayMessagePacket, session: Session) -> None:
    session.away_msg = packet.message.content
