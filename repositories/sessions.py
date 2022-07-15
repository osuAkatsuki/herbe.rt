from __future__ import annotations

import json
import uuid
from typing import Optional

import repositories.accounts
import services
import utils
from constants.action import Action
from constants.mode import Mode
from constants.mods import Mods
from constants.presence import PresenceFilter
from models.geolocation import Geolocation
from models.hardware import HardwareInfo
from models.user import Account
from models.user import Session
from models.user import Status
from models.version import OsuVersion
from objects.redis_lock import RedisLock


async def fetch_by_id(id: int) -> Optional[Session]:
    session_res = await services.redis.hget("akatsuki:herbert:sessions", f"id_{id}")
    if not session_res:
        return None

    session_dict = json.loads(session_res)

    account = await repositories.accounts.fetch_by_id(session_dict["id"])
    return Session(**(session_dict | account.dict()))


async def fetch_by_name(name: str) -> Optional[Session]:
    session_res = await services.redis.hget(
        "akatsuki:herbert:sessions",
        f"name_{utils.make_safe_name(name)}",
    )
    if not session_res:
        return None

    session_dict = json.loads(session_res)

    account = await repositories.accounts.fetch_by_id(session_dict["id"])
    return Session(**(session_dict | account.dict()))


async def fetch_by_token(token: str) -> Optional[Session]:
    session_res = await services.redis.hget(
        "akatsuki:herbert:sessions",
        f"token_{token}",
    )
    if not session_res:
        return None

    session_dict = json.loads(session_res)

    account = await repositories.accounts.fetch_by_id(session_dict["id"])
    return Session(**(session_dict | account.dict()))


async def fetch_all() -> set[Session]:
    sessions = set()

    session_dicts = {
        json.loads(session_res)
        for session_res in await services.redis.hgetall("akatsuki:herbert:sessions")
    }
    for session_dict in session_dicts:
        account = await repositories.accounts.fetch_by_id(session_dict["id"])
        sessions.add(Session(**(session_dict | account.dict())))

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
        presence_filter=PresenceFilter.NIL,
        status=Status.default(),
        channels=set(),
        spectators=set(),
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
        for key in (
            f"id_{session.id}",
            f"name_{utils.make_safe_name(session.name)}",
            f"token_{session.token}",
        ):
            await services.redis.hset(
                "akatsuki:herbert:sessions",
                key,
                json.dumps(session.dict()),
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
