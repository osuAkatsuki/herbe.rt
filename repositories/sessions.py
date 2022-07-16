from __future__ import annotations

import json
import time
from typing import Optional

import repositories.accounts
import repositories.stats
import services
import usecases.packets
import usecases.sessions
import utils
from models.geolocation import Geolocation
from models.hardware import HardwareInfo
from models.user import Account
from models.user import Session
from models.user import Status
from models.version import OsuVersion
from objects.redis_lock import RedisLock


async def fetch_by_id(id: int) -> Optional[Session]:
    session_res = await services.redis.hget("akatsuki:herbert:sessions:id", id)
    if not session_res:
        return None

    session_dict = json.loads(session_res)

    account = await repositories.accounts.fetch_by_id(session_dict["id"])
    assert account is not None

    return Session(**(session_dict | account.dict()))


async def fetch_by_name(name: str) -> Optional[Session]:
    session_res = await services.redis.hget(
        "akatsuki:herbert:sessions:name",
        utils.make_safe_name(name),
    )
    if not session_res:
        return None

    session_dict = json.loads(session_res)

    account = await repositories.accounts.fetch_by_id(session_dict["id"])
    assert account is not None

    return Session(**(session_dict | account.dict()))


async def fetch_by_token(token: str) -> Optional[Session]:
    session_res = await services.redis.hget(
        "akatsuki:herbert:sessions:token",
        token,
    )
    if not session_res:
        return None

    session_dict = json.loads(session_res)

    account = await repositories.accounts.fetch_by_id(session_dict["id"])
    assert account is not None

    return Session(**(session_dict | account.dict()))


async def fetch_all() -> list[Session]:
    sessions = []

    for redis_session in (
        await services.redis.hgetall("akatsuki:herbert:sessions:token")
    ).values():
        session_dict = json.loads(redis_session)
        account = await repositories.accounts.fetch_by_id(session_dict["id"])
        assert account is not None

        sessions.append(Session(**(session_dict | account.dict())))

    return sessions


async def create(
    account: Account,
    geolocation: Geolocation,
    utc_offset: int,
    friend_only_dms: bool,
    client_version: OsuVersion,
    hardware: HardwareInfo,
) -> Session:
    session = Session(
        **account.dict(),
        geolocation=geolocation,
        utc_offset=utc_offset,
        login_time=time.time(),
        status=Status.default(),
        channels=[],
        spectators=[],
        spectating=None,
        match=None,
        friend_only_dms=friend_only_dms,
        in_lobby=False,
        away_msg=None,
        client_version=client_version,
        hardware=hardware,
        last_np=None,
    )

    await update(session)
    return session


async def update(session: Session) -> None:
    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:sessions:{session.id}",
    ):
        session_dump = json.dumps(session.dict())

        for redis_name, redis_key in (
            ("akatsuki:herbert:sessions:id", session.id),
            ("akatsuki:herbert:sessions:name", utils.make_safe_name(session.name)),
            ("akatsuki:herbert:sessions:token", session.token),
        ):
            await services.redis.hset(
                name=redis_name,
                key=redis_key,
                value=session_dump,
            )

    stats = await repositories.stats.fetch(session.id, session.status.mode)
    await enqueue_data(
        usecases.packets.user_stats(session, stats)
        + usecases.packets.user_presence(session, stats),
    )


async def add_to_session_list(session: Session) -> None:
    await update(session)

    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:session_list",
    ):
        await services.redis.lpush(
            "akatsuki:herbert:session_list",
            session.id,
        )


async def remove_from_session_list(session: Session) -> None:
    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:session_list",
    ):
        await services.redis.lrem(
            "akatsuki:herbert:session_list",
            0,
            session.id,
        )


async def enqueue_data(data: bytearray) -> None:
    for session in await fetch_all():
        await usecases.sessions.enqueue_data(session.id, data)


async def delete(session: Session) -> None:
    async with RedisLock(
        services.redis,
        f"akatsuki:herbert:locks:sessions:{session.id}",
    ):
        for redis_name, redis_key in (
            ("akatsuki:herbert:sessions:id", session.id),
            ("akatsuki:herbert:sessions:name", utils.make_safe_name(session.name)),
            ("akatsuki:herbert:sessions:token", session.token),
        ):
            await services.redis.hdel(redis_name, redis_key)

    await remove_from_session_list(session)
