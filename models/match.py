from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


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


@dataclass
class Slot:
    user_id: Optional[int] = None
    status: SlotStatus = SlotStatus.OPEN
    team: MatchTeam = MatchTeam.NEUTRAL
    mods: int = 0
    loaded: bool = False
    skipped: bool = False

    @property
    def empty(self) -> bool:
        return self.user_id is None

    def copy_from(self, other: Slot) -> None:
        self.user_id = other.user_id
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
