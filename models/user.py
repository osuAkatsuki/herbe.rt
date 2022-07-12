from __future__ import annotations

import time
from dataclasses import dataclass
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

    @property
    def silence_expire(self) -> int:
        if not self.silence_end:
            return 0

        return self.silence_end - int(time.time())
