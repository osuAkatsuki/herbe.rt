from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Literal
from typing import Optional

from fastapi import APIRouter
from fastapi import Header
from fastapi import Request
from fastapi import Response

import api.packets
import repositories.accounts
import repositories.channels
import repositories.hardware
import repositories.icons
import repositories.sessions
import repositories.stats
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
        login_response = await login(body, geolocation)

        return Response(
            content=login_response.body,
            headers={"cho-token": login_response.token},
        )

    session = await repositories.sessions.fetch_by_token(osu_token)
    if not session:
        return Response(content=bytes(usecases.packets.restart_server(0)))

    await api.packets.handle_packet_data(body, session)
    return Response(content=await usecases.sessions.dequeue_data(session.id))


async def login(body: bytes, geolocation: Geolocation) -> LoginResponse:
    start = time.perf_counter_ns()
    login_data = usecases.login.parse_login_data(body)

    osu_version = usecases.version.parse_osu_version(login_data.osu_version)
    # if not osu_version or osu_version.date < (date.today() - DELTA_90_DAYS):
    #     return LoginResponse(
    #         body=usecases.packets.version_update_forced()
    #         + usecases.packets.user_id(-2),
    #     )

    adapter_result = usecases.hardware.parse_adapters(login_data.adapters_str)
    if not adapter_result:
        return LoginResponse(body=usecases.packets.user_id(-5))

    adapters, running_under_wine = adapter_result

    hardware = HardwareInfo(
        running_under_wine=running_under_wine,
        osu_md5=login_data.osu_path_md5,
        adapters_md5=login_data.adapters_md5,
        uninstall_md5=login_data.uninstall_md5,
        disk_md5=login_data.disk_signature_md5,
        adapters=adapters,
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
        login_data.utc_offset,
        login_data.pm_private,
        osu_version,
        hardware,
    )

    # TODO: hardware matches, tourney client sessions
    oui_info = {
        await repositories.hardware.fetch_oui(adapter)
        for adapter in hardware.adapters
        if adapter
    }
    if not all(oui for oui in oui_info if oui is not None):
        logging.warning(f"{session!r} logged in with invalid adapters (no OUI match)")
        ...  # TODO: what to do on invalid hardware?

    data = bytearray()
    data += usecases.packets.protocol_version(19)
    data += usecases.packets.user_id(session.id)
    data += usecases.packets.bancho_privileges(session.bancho_privileges)

    for channel in await repositories.channels.fetch_all():
        if channel.name == "#lobby" or channel.hidden or channel.temp:
            continue

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

    icon = await repositories.icons.fetch_random()
    data += usecases.packets.menu_icon(icon.image_url, icon.click_url)

    data += usecases.packets.friends_list(session.friends)
    data += usecases.packets.silence_end(session.silence_expire)

    stats = await repositories.stats.fetch(session.id, session.status.mode)
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
            target_stats = await repositories.stats.fetch(target.id, target.status.mode)
            data += usecases.packets.user_presence(
                target,
                target_stats,
            ) + usecases.packets.user_stats(
                target,
                target_stats,
            )

    if not session.privileges & Privileges.USER_PUBLIC:
        data += usecases.packets.user_restricted()

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
        f"{session!r} logged in with osu! version {session.client_version!r} from {geolocation.country.acronym.upper()} in {formatted_time}",
    )

    return LoginResponse(body=data, token=session.token)
