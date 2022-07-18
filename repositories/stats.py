from __future__ import annotations

from typing import NamedTuple

import services
from constants.mode import Mode
from models.stats import Stats


async def fetch(user_id: int, mode: Mode) -> Stats:
    db_stats = await services.database.fetch_one(
        (
            "SELECT ranked_score_{m} ranked_score, total_score_{m} total_score, pp_{m} pp, avg_accuracy_{m} accuracy, "
            "playcount_{m} playcount, playtime_{m} playtime, max_combo_{m} max_combo, total_hits_{m} total_hits, "
            "replays_watched_{m} replays_watched "
            "FROM {s} WHERE id = :id"
        ).format(m=mode.stats_prefix, s=mode.stats_table),
        {"id": user_id},
    )
    assert db_stats is not None

    global_rank = await get_redis_rank(user_id, mode)

    return Stats(
        user_id=user_id,
        mode=mode,
        ranked_score=db_stats["ranked_score"],
        total_score=db_stats["total_score"],
        pp=db_stats["pp"],
        rank=global_rank,
        accuracy=db_stats["accuracy"],
        playcount=db_stats["playcount"],
        playtime=db_stats["playtime"],
        max_combo=db_stats["max_combo"],
        total_hits=db_stats["total_hits"],
        replays_watched=db_stats["replays_watched"],
    )


async def get_redis_rank(user_id: int, mode: Mode) -> int:
    redis_global_rank = await services.redis.zrevrank(
        f"ripple:{mode.redis_leaderboard}:{mode.stats_prefix}",
        user_id,
    )

    return int(redis_global_rank) + 1 if redis_global_rank else 0
