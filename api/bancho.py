from __future__ import annotations

import time
from datetime import date
from datetime import timedelta
from typing import Literal
from typing import Optional

from fastapi import APIRouter
from fastapi import Header
from fastapi import Request
from fastapi import Response

import usecases.geolocation
import usecases.hardware
import usecases.login
import usecases.packets
import usecases.version
from models.geolocation import Geolocation
from models.hardware import HardwareInfo
from models.login import LoginData
from models.login import LoginResponse
from models.session import SessionInfo

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
            content=login_data.body,
            headers={"cho-token": login_data.token},
        )

    return b""


async def login(body: bytearray, geolocation: Geolocation) -> LoginResponse:
    start = time.perf_counter_ns()
    login_data = usecases.login.parse_login_data(body)

    osu_version = usecases.version.parse_osu_version(login_data.osu_version)
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
