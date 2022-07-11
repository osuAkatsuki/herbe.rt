from __future__ import annotations

import re
from datetime import date
from typing import Optional

from models.version import OsuVersion

OSU_VERSION = re.compile(
    r"^b(?P<date>\d{8})(?:\.(?P<revision>\d))?"
    r"(?P<stream>beta|cuttingedge|dev|tourney)?$",
)


def parse_osu_version(osu_version: str) -> Optional[OsuVersion]:
    ver_match = OSU_VERSION.match(osu_version)
    if ver_match is None:
        return None

    osu_ver = OsuVersion(
        date=date(
            year=int(ver_match["date"][0:4]),
            month=int(ver_match["date"][4:6]),
            day=int(ver_match["date"][6:8]),
        ),
        revision=int(ver_match["revision"]) if ver_match["revision"] else 0,
        stream=ver_match["stream"] or "stable",
    )

    return osu_ver
