from __future__ import annotations

from pydantic import BaseModel

from constants.mode import Mode


class Stats(BaseModel):
    user_id: int
    mode: Mode

    ranked_score: int
    total_score: int
    pp: float
    rank: int
    accuracy: float
    playcount: int
    playtime: int
    max_combo: int
    total_hits: int
    replays_watched: int
