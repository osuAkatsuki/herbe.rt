from __future__ import annotations

from enum import IntEnum
from typing import Optional
from typing import Union

from pydantic import BaseModel

from constants.mode import Mode
from models.user import Session
from packets.typing import OsuMatch


class SlotStatus(IntEnum):
    OPEN = 1
    LOCKED = 2
    NOT_READY = 4
    READY = 8
    NO_MAP = 16
    PLAYING = 32
    COMPLETE = 64
    QUIT = 128

    HAS_USER = NOT_READY | READY | NO_MAP | PLAYING | COMPLETE


class MatchTeam(IntEnum):
    NEUTRAL = 0
    BLUE = 1
    RED = 2


class MatchWinCondition(IntEnum):
    SCORE = 0
    ACCURACY = 1
    COMBO = 2
    SCOREV2 = 3


class MatchTeamType(IntEnum):
    HEAD_TO_HEAD = 0
    TAG_COOP = 1
    TEAM_VS = 2
    TAG_TEAM_VS = 3


class Slot(BaseModel):
    session_id: Optional[int] = None
    status: SlotStatus = SlotStatus.OPEN
    team: MatchTeam = MatchTeam.NEUTRAL
    mods: int = 0
    loaded: bool = False
    skipped: bool = False

    @property
    def empty(self) -> bool:
        return self.session_id is None

    def copy_from(self, other: Slot) -> None:
        self.session_id = other.session_id
        self.status = other.status
        self.team = other.team
        self.mods = other.mods

    def reset(self, new_status: SlotStatus = SlotStatus.OPEN) -> None:
        self.user = None
        self.status = new_status
        self.team = MatchTeam.NEUTRAL
        self.mods = 0
        self.loaded = False
        self.skipped = False


class Match(BaseModel):
    # required on init
    id: int
    name: str
    host_id: int
    mods: int
    mode: Mode

    # set later

    map_id: Optional[int] = None
    map_md5: Optional[str] = None
    map_title: Optional[str] = None
    last_map_id: Optional[int] = None

    freemod: bool = False

    slots: list[Slot] = [Slot() for _ in range(16)]
    password: Optional[str] = None
    refs: list[int] = []
    team_type: MatchTeamType = MatchTeamType.HEAD_TO_HEAD
    win_condition: MatchWinCondition = MatchWinCondition.SCORE

    in_progress: bool = False
    seed: int = 0  # mania

    tourney_clients: list[int] = []

    def __repr__(self) -> str:
        return f"<{self.name} ({self.id})>"

    def __contains__(self, session: Union[Session, int]) -> bool:
        if isinstance(session, Session):
            session_id = session.id
        else:
            session_id = session

        return session_id in {slot.session_id for slot in self.slots}

    @property
    def url(self) -> str:
        return f"osump://{self.id}/{self.password if self.password else ''}"

    @property
    def embed(self) -> str:
        return f"[{self.url} {self.name}]"

    def get_slot(self, session_id: int) -> Optional[Slot]:
        for slot in self.slots:
            if slot.session_id == session_id:
                return slot

        return None

    def get_slot_idx(self, session_id: int) -> Optional[int]:
        for idx, slot in enumerate(self.slots):
            if slot.session_id == session_id:
                return idx

        return None

    def get_next_free_slot_idx(self) -> Optional[int]:
        for idx, slot in enumerate(self.slots):
            if slot.status == SlotStatus.OPEN:
                return idx

        return None

    def get_host_slot(self) -> Optional[Slot]:
        for slot in self.slots:
            if slot.status & SlotStatus.HAS_USER and slot.session_id == self.host_id:
                return slot

        return None

    def copy(self, other: Match) -> None:
        self.map_id = other.map_id
        self.map_md5 = other.map_md5
        self.map_name = other.map_name
        self.freemod = other.freemod
        self.mode = other.mode
        self.team_type = other.team_type
        self.win_condition = other.win_condition
        self.mods = other.mods
        self.name = other.name

    def unready_users(self, expected: SlotStatus = SlotStatus.READY) -> None:
        for slot in self.slots:
            if slot.status == expected:
                slot.status = SlotStatus.NOT_READY
