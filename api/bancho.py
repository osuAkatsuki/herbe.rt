from __future__ import annotations

import logging
import time
from datetime import date
from datetime import timedelta
from typing import Literal
from typing import Optional

from fastapi import APIRouter
from fastapi import Header
from fastapi import Request
from fastapi import Response

import repositories.accounts
import repositories.channels
import repositories.sessions
import repositories.stats
import settings
import usecases.geolocation
import usecases.hardware
import usecases.login
import usecases.packets
import usecases.password
import usecases.sessions
import usecases.version
import utils
from constants.privileges import Privileges
from models.geolocation import Geolocation
from models.hardware import HardwareInfo
from models.login import LoginResponse
from models.session import SessionInfo
from packets.typing import Message

router = APIRouter(default_response_class=Response)

DELTA_90_DAYS = timedelta(days=90)


@router.get("/")
def index_request():
    return "herbe.rt"


@router.post("/")
async def bancho_request(
    request: Request,
    osu_token: Optional[str] = Header(None),
    user_agent: Literal["osu!"] = Header(...),
):
    body = await request.body()
    geolocation = usecases.geolocation.from_headers(request.headers)

    if not osu_token:
        login_data = await login(body, geolocation)

        return Response(
            content=bytes(login_data.body),
            headers={"cho-token": login_data.token},
        )

    return b""


async def login(body: bytearray, geolocation: Geolocation) -> LoginResponse:
    start = time.perf_counter_ns()
    login_data = usecases.login.parse_login_data(body)

    osu_version = usecases.version.parse_osu_version(login_data.osu_version)
    osu_version.date = date.today()
    if not osu_version or osu_version.date < (date.today() - DELTA_90_DAYS):
        return LoginResponse(
            body=usecases.packets.version_update_forced()
            + usecases.packets.user_id(-2),
        )

    adapter_result = usecases.hardware.parse_adapters(login_data.adapters_str)
    if not adapter_result:
        return LoginResponse(body=usecases.packets.user_id(-5))

    adapters, running_under_wine = adapter_result

    session_info = SessionInfo(
        client=osu_version,
        hardware=HardwareInfo(
            running_under_wine,
            login_data.osu_path_md5,
            login_data.adapters_md5,
            login_data.uninstall_md5,
            login_data.disk_signature_md5,
            adapters,
        ),
    )

    account = await repositories.accounts.fetch_by_name(login_data.username)
    if not account:
        return LoginResponse(body=usecases.packets.user_id(-1))

    if not await usecases.password.verify_password(
        login_data.password_md5,
        account.password_bcrypt,
    ):
        return LoginResponse(body=usecases.packets.user_id(-1))

    if await repositories.sessions.fetch_by_id(account.id) is not None:
        return LoginResponse(
            body=usecases.packets.user_id(-1)
            + usecases.packets.notification("You are already logged in!"),
        )

    session = await repositories.sessions.create(
        account,
        geolocation,
        session_info,
        login_data.utc_offset,
        login_data.pm_private,
    )

    # TODO: hardware matches, tourney client sessions

    data = bytearray(usecases.packets.protocol_version(19))
    data += usecases.packets.user_id(session.id)
    data += usecases.packets.bancho_privileges(session.bancho_privileges)

    for channel in await repositories.channels.fetch_all():
        if (
            not channel.public_read
            and not session.privileges & Privileges.ADMIN_MANAGE_USERS
        ):
            continue

        channel_info_packet = usecases.packets.channel_info(channel)
        data += channel_info_packet

        for target in await repositories.sessions.fetch_all():
            if target is session:
                continue

            if channel.public_read or target.privileges & Privileges.ADMIN_MANAGE_USERS:
                await usecases.sessions.enqueue_data(target.id, channel_info_packet)

        await usecases.sessions.join_channel(session, channel)

    data += usecases.packets.channel_info_end()
    data += usecases.packets.menu_icon("", "")  # TODO
    data += usecases.packets.friends_list(session.friends)
    data += usecases.packets.silence_end(session.silence_expire)

    stats = await repositories.stats.fetch(session.id, session.mode)
    user_data = usecases.packets.user_presence(
        session,
        stats,
    ) + usecases.packets.user_stats(
        session,
        stats,
    )
    data += user_data

    for target in await repositories.sessions.fetch_all():
        if session.privileges & Privileges.USER_PUBLIC:
            await usecases.sessions.enqueue_data(target.id, user_data)

        if not target.privileges & Privileges.USER_PUBLIC:
            target_stats = await repositories.stats.fetch(target.id, target.mode)
            data += usecases.packets.user_presence(
                target,
                target_stats,
            ) + usecases.packets.user_stats(
                target,
                target_stats,
            )

    bot = await repositories.accounts.fetch_by_id(999)

    current_time = int(time.time())
    if not session.privileges & Privileges.USER_PUBLIC:
        data += usecases.packets.user_restricted()
        data += usecases.packets.send_message(
            Message(
                bot.name,
                settings.RESTRICTION_MESSAGE,
                session.name,
                bot.id,
            ),
        )
    elif session.freeze_end > current_time:
        data += usecases.packets.send_message(
            Message(
                bot.name,
                settings.FROZEN_MESSAGE.format(
                    time_until_restriction=timedelta(
                        seconds=session.freeze_end - current_time,
                    ),
                ),
                session.name,
                bot.id,
            ),
        )
    elif session.freeze_end != 0:
        ...  # TODO: restrict

    if session.privileges & Privileges.USER_PENDING_VERIFICATION:
        await usecases.sessions.remove_privilege(
            session,
            Privileges.USER_PENDING_VERIFICATION,
        )

    await repositories.sessions.add_to_session_list(session)

    end = time.perf_counter_ns()
    formatted_time = utils.format_time(end - start)
    data += usecases.packets.notification(
        f"Welcome back to Akatsuki!\nTime elapsed: {formatted_time}",
    )

    logging.info(
        f"{session!r} logged in with osu! version {session_info.client} from {geolocation.country.acronym.upper()} in {formatted_time}",
    )

    return LoginResponse(body=data, token=session.token)
