from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from typing import Optional

from pydantic import BaseModel

import utils
from constants.mode import Mode
from constants.privileges import BanchoPrivileges
from constants.privileges import Privileges


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


class Session(Account):
    token: str

    # geolocation
    current_country_code: str
    long: float
    lat: float
    utc_offset: int

    # status
    presence_filter: int
    action: int
    action_text: str
    map_md5: str
    map_id: int
    mods: int
    mode: Mode

    channels: set[str]
    spectators: set[int]

    spectating: Optional[int]
    match: Optional[int]

    friend_only_dms: bool
    in_lobby: bool

    away_msg: Optional[str]

    # session "info"
    osu_version: str
    running_under_wine: bool
    osu_md5: str
    adapters_md5: str
    uninstall_md5: str
    disk_md5: str
    adapters: list[str]

    last_np_id: Optional[int]
    last_np_mode: Optional[int]

    def __repr__(self) -> str:
        return f"<{self.name} ({self.id})>"

    def dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "token": self.token,
            "current_country_code": self.current_country_code,
            "long": self.long,
            "lat": self.lat,
            "utc_offset": self.utc_offset,
            "presence_filter": self.presence_filter,
            "action": self.action,
            "action_text": self.action_text,
            "map_md5": self.map_md5,
            "map_id": self.map_id,
            "mods": self.mods,
            "mode": self.mode.value,
            "channels": self.channels,
            "spectators": self.spectators,
            "spectating": self.spectating,
            "match": self.match,
            "friend_only_dms": self.friend_only_dms,
            "in_lobby": self.in_lobby,
            "away_msg": self.away_msg,
            "osu_version": self.osu_version,
            "running_under_wine": self.running_under_wine,
            "osu_md5": self.osu_md5,
            "adapters_md5": self.adapters_md5,
            "uninstall_md5": self.uninstall_md5,
            "disk_md5": self.disk_md5,
            "adapters": self.adapters,
            "last_np_id": self.last_np_id,
            "last_np_mode": self.last_np_mode,
        }

    @property
    def silence_expire(self) -> int:
        if not self.silence_end:
            return 0

        return self.silence_end - int(time.time())