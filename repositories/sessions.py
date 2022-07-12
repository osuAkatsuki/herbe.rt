from __future__ import annotations

import json
import uuid
from typing import Optional

import services
import utils
from constants.action import Action
from constants.mode import Mode
from constants.mods import Mods
from constants.presence import PresenceFilter
from models.geolocation import Geolocation
from models.session import SessionInfo
from models.user import Account
from models.user import Session
from objects.redis_lock import RedisLock


async def fetch_by_id(id: int) -> Optional[Session]:
    session_dict = await services.redis.hget("akatsuki:herbert:sessions", f"id_{id}")
    if not session_dict:
        return None

    return Session(**json.loads(session_dict))


async def fetch_by_name(name: str) -> Optional[Session]:
    session_dict = await services.redis.hget(
        "akatsuki:herbert:sessions",
        f"name_{utils.make_safe_name(name)}",
    )
    if not session_dict:
        return None

    return Session(**json.loads(session_dict))


async def fetch_by_token(token: str) -> Optional[Session]:
    session_dict = await services.redis.hget(
        "akatsuki:herbert:sessions",
        f"token_{token}",
    )
    if not session_dict:
        return None

    return Session(**json.loads(session_dict))


async def fetch_all() -> set[Session]:
    session_dicts = await services.redis.hgetall("akatsuki:herbert:sessions")
    return {Session(**json.loads(session_dict)) for session_dict in session_dicts}


async def create(
    account: Account,
    geolocation: Geolocation,
    session_info: SessionInfo,
    utc_offset: int,
    friend_only_dms: bool,
) -> Session:
    token = str(uuid.uuid4())

    session = Session(
        **account.dict(),
        token=token,
        current_country_code=geolocation.country.acronym,
        long=geolocation.long,
        lat=geolocation.lat,
        utc_offset=utc_offset,
        presence_filter=PresenceFilter.NIL,
        action=Action.IDLE,
        action_text="",
        map_md5="",
        map_id=0,
        mods=Mods.NOMOD,
        mode=Mode.STD,
        channels=set(),
        spectators=set(),
        spectating=None,
        match=None,
        friend_only_dms=friend_only_dms,
        in_lobby=False,
        away_msg=None,
        osu_version=repr(session_info.client),
        running_under_wine=session_info.hardware.running_under_wine,
        osu_md5=session_info.hardware.osu_md5,
        adapters_md5=session_info.hardware.adapters_md5,
        uninstall_md5=session_info.hardware.uninstall_md5,
        disk_md5=session_info.hardware.disk_md5,
        adapters=session_info.hardware.adapters,
        last_np_id=None,
        last_np_mode=None,
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
