from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

import utils
from constants.action import Action
from constants.mode import Mode
from constants.presence import PresenceFilter
from constants.privileges import BanchoPrivileges
from constants.privileges import Privileges
from models.geolocation import Geolocation
from models.hardware import HardwareInfo
from models.version import OsuVersion


class Account(BaseModel):
    id: int
    name: str
    email: str

    privileges: int

    password_bcrypt: str
    country: str

    friends: set[int]

    clan_id: int
    clan_privileges: int

    silence_end: int
    donor_expire: int
    freeze_end: int

    def __repr__(self) -> str:
        return f"<{self.name} ({self.id})>"

    @property
    def safe_name(self) -> str:
        return utils.make_safe_name(self.name)

    @property
    def bancho_privileges(self) -> int:
        # everyone gets free direct
        privileges = BanchoPrivileges.SUPPORTER

        if self.privileges & Privileges.USER_NORMAL:
            privileges |= BanchoPrivileges.PLAYER

        if self.privileges & Privileges.ADMIN_MANAGE_USERS:
            privileges |= BanchoPrivileges.MODERATOR
        elif self.privileges & Privileges.ADMIN_MANAGE_SETTINGS:
            privileges |= BanchoPrivileges.DEVELOPER

        if self.privileges & Privileges.ADMIN_CAKER:
            privileges |= BanchoPrivileges.OWNER

        return privileges


class Status(BaseModel):
    presence_filter: int
    action: int
    action_text: str
    map_md5: str
    map_id: int
    mods: int
    mode: Mode

    @staticmethod
    def default() -> Status:
        return Status(
            presence_filter=PresenceFilter.NIL,
            action=Action.IDLE,
            action_text="",
            map_md5="",
            map_id=0,
            mods=0,
            mode=Mode.STD,
        )


class LastNp(BaseModel):
    map_id: int
    mode_vn: int


class Session(Account):
    token: str = Field(default_factory=uuid.uuid4)

    geolocation: Geolocation
    utc_offset: int

    status: Status

    channels: set[str]
    spectators: set[int]

    spectating: Optional[int]
    match: Optional[int]

    friend_only_dms: bool
    in_lobby: bool

    away_msg: Optional[str]

    client_version: OsuVersion
    hardware: HardwareInfo

    last_np: Optional[LastNp]

    def __repr__(self) -> str:
        return f"<{self.name} ({self.id})>"

    @property
    def silence_expire(self) -> int:
        if not self.silence_end:
            return 0

        return self.silence_end - int(time.time())

    def dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "token": self.token,
            "geolocation": self.geolocation.dict(),
            "utc_offset": self.utc_offset,
            "status": self.status.dict(),
            "channels": self.channels,
            "spectators": self.spectators,
            "spectating": self.spectating,
            "match": self.match,
            "friend_only_dms": self.friend_only_dms,
            "in_lobby": self.in_lobby,
            "away_msg": self.away_msg,
            "client_version": self.client_version.dict(),
            "hardware": self.hardware.dict(),
            "last_np": self.last_np.dict(),
        }
