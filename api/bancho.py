from __future__ import annotations

from fastapi import APIRouter
from fastapi import Response

router = APIRouter(default_response_class=Response)


@router.get("/")
def index_request():
    return "herbe.rt"


@router.post("/")
async def bancho_request():
    return b""
