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
import repositories.sessions
import usecases.channels
import usecases.sessions
from constants.mode import Mode
from constants.packets import Packets
from constants.privileges import Privileges
from models.user import Session
from packets.models import ChangeActionPacket
from packets.models import LogoutPacket
from packets.models import PacketModel
from packets.models import SendMessagePacket
from packets.reader import Packet
from packets.reader import PacketArray
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

    # TODO: spec chats, multi chats
    channel = await repositories.channels.fetch_by_name(recipient)
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

    # TODO: commands

    logging.info(f"{session!r} sent a message to {recipient}: {msg}")
