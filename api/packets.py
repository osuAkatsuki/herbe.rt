from __future__ import annotations

import inspect
from typing import Any
from typing import Callable
from typing import Optional

import packets.models
import packets.typing
from constants.packets import Packets
from constants.privileges import Privileges
from models.user import Session
from packets.models import PacketModel
from packets.reader import Packet
from packets.reader import PacketArray
from packets.typing import osuType
from packets.typing import PacketHandler
from packets.typing import PacketWrapper


HANDLERS: dict[Packets, PacketWrapper] = {}
RESTRICTED_HANDLERS: dict[Packets, PacketWrapper] = {}

MODEL_CLASSES: dict[str, type[PacketModel]] = {}
DATA_TYPE_CLASSES: dict[str, type[osuType]] = {}


def is_valid_packet_model(_obj: object) -> bool:
    return inspect.isclass(_obj) and issubclass(_obj, PacketModel)


def is_valid_packet_data_type(_obj: object) -> bool:
    return inspect.isclass(_obj) and issubclass(_obj, osuType)


def get_packet_model_from_name(class_name: str) -> Optional[type[PacketModel]]:
    if _class := MODEL_CLASSES.get(class_name):
        return _class

    for name, obj in inspect.getmembers(packets.models, is_valid_packet_model):
        if inspect.isclass(obj) and name == class_name:
            assert issubclass(obj, PacketModel)

            MODEL_CLASSES[class_name] = obj
            return obj

    return None


def get_packet_data_type_from_name(class_name: str) -> Optional[type[osuType]]:
    if _class := DATA_TYPE_CLASSES.get(class_name):
        return _class

    for name, obj in inspect.getmembers(packets.typing, is_valid_packet_data_type):
        if inspect.isclass(obj) and name == class_name:
            assert issubclass(obj, osuType)

            DATA_TYPE_CLASSES[class_name] = obj
            return obj

    return None


def register_packet(
    packet_id: Packets,
    allow_restricted: bool = False,
) -> Callable[[PacketHandler], PacketWrapper]:
    def decorator(handler: PacketHandler) -> PacketWrapper:
        async def wrapper(packet: Packet, session: Session) -> None:
            structure_class_name = handler.__annotations__["packet"]
            structure_class = get_packet_model_from_name(structure_class_name)
            if not structure_class:
                raise RuntimeError(f"Invalid packet model: {structure_class_name}")

            data: dict[str, Any] = {}
            for field, _type in structure_class.__annotations__.items():
                if _type == "bytes":
                    data[field] = bytes(packet.data)
                    packet.data.clear()
                else:
                    data_type_class = get_packet_data_type_from_name(_type)
                    if not data_type_class:
                        raise RuntimeError(f"Invalid packet data type: {_type}")

                    data[field] = data_type_class.read(packet)

            packet_model = structure_class()
            packet_model.__dict__ |= data

            return await handler(packet_model, session)

        HANDLERS[packet_id] = wrapper
        if allow_restricted:
            RESTRICTED_HANDLERS[packet_id] = wrapper

        return wrapper

    return decorator


async def handle_request(data: bytes, session: Session) -> None:
    packet_map = HANDLERS
    if not session.privileges & Privileges.USER_PUBLIC:
        packet_map = RESTRICTED_HANDLERS

    packet_array = PacketArray(bytearray(data), packet_map)
    for packet, handler in packet_array:
        await handler(packet, session)
