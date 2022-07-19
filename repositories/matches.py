from __future__ import annotations

import json
from typing import Optional

import repositories.channels
import services
import usecases.channels
import usecases.packets
import utils
from models.match import Match
from objects.redis_lock import RedisLock


async def fetch_by_id(id: int) -> Optional[Match]:
    match_dict = await services.redis.hget(
        "akatsuki:herbert:matches:id",
        id,
    )
    if not match_dict:
        return None

    return Match(**json.loads(match_dict))


async def fetch_by_name(name: str) -> Optional[Match]:
    match_dict = await services.redis.hget(
        "akatsuki:herbert:matches:name",
        utils.make_safe_name(name),
    )
    if not match_dict:
        return None

    return Match(**json.loads(match_dict))


async def fetch_all() -> list[Match]:
    match_dicts = (
        await services.redis.hgetall("akatsuki:herbert:matches:name")
    ).values()
    return [Match(**json.loads(match_dict)) for match_dict in match_dicts]


async def update(match: Match, lobby: bool = True) -> None:
    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:matches:{match.id}",
    ):
        match_dump = json.dumps(match.dict())

        for redis_name, redis_key in (
            ("akatsuki:herbert:matches:id", match.id),
            ("akatsuki:herbert:matches:name", utils.make_safe_name(match.name)),
        ):
            await services.redis.hset(
                name=redis_name,
                key=redis_key,
                value=match_dump,
            )

    match_chat = await repositories.channels.fetch_by_name(f"#multi_{match.id}")
    assert match_chat is not None

    await usecases.channels.enqueue_data(
        match_chat,
        usecases.packets.update_match(match, send_pw=True),
    )

    if lobby:
        lobby_chat = await repositories.channels.fetch_by_name(f"#lobby")
        assert lobby_chat is not None

        await usecases.channels.enqueue_data(
            lobby_chat,
            usecases.packets.update_match(match, send_pw=False),
        )


async def delete(match: Match) -> None:
    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:matches:{match.id}",
    ):
        for redis_name, redis_key in (
            ("akatsuki:herbert:matches:id", match.id),
            ("akatsuki:herbert:matches:name", utils.make_safe_name(match.name)),
        ):
            await services.redis.hdel(redis_name, redis_key)
