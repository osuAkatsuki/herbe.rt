"""
Terminology Reference:

OUI: Organizationally Unique Identifier
    - https://standards-oui.ieee.org/oui/oui.csv
CID: Company ID
    - http://standards-oui.ieee.org/cid/cid.csv
IAB: Individual Address Block
    - http://standards-oui.ieee.org/iab/iab.csv
EUI: Extended Unique Identifier


MA-L: IEEE MAC Address Large (24-bit block size)
MA-M: IEEE MAC Address Large (28-bit block size)
MA-S: IEEE MAC Address Small (36-bit block size)
OUI24: Organizationally Unique Identifier (24-bit block size)
OUI36: Organizationally Unique Identifier (36-bit block size)
IAB: Individual Address Block (36-bit block size)
CID: Company ID Blocks (24-bit block size)
EUI48: Extended Unique Identifier (48-bit block size)
"""
from __future__ import annotations

import csv
import stat
import time
from typing import Optional

import services
from models.hardware import OUIEntry
from objects.path import Path

OUI_CACHE_MAX_AGE = 10 * 24 * 60 * 60  # 10 days before cache expires
OUI_CSV_URL = "https://standards-oui.ieee.org/oui/oui.csv"
OUI_CSV_CACHE = Path.cwd() / ".oui_cache.csv"

OUI_CACHE: dict[str, OUIEntry] = {}


def _valid_cache_file() -> bool:
    stat_result = OUI_CSV_CACHE.stat()
    if not stat_result:
        return False

    if not stat.S_ISREG(stat_result.st_mode):
        return False

    # stat exists & is valid, cache is valid if age < OUI_CACHE_MAX_AGE
    return (time.time() - OUI_CACHE_MAX_AGE) < stat_result.st_mtime


async def fetch_oui(address: str) -> Optional[OUIEntry]:
    if not OUI_CACHE:
        await update_cache()

    if oui := OUI_CACHE.get(address[:6]):
        return oui

    return None


async def update_cache() -> None:
    global OUI_CACHE
    OUI_CACHE = {entry.assignment: entry for entry in await fetch_all()}


async def fetch_all() -> set[OUIEntry]:
    if OUI_CACHE:
        return set(OUI_CACHE.values())

    if _valid_cache_file():
        csv_data = OUI_CSV_CACHE.read_lines()
    else:
        async with services.http.get(OUI_CSV_URL) as resp:
            if resp.status != 200:
                return set()

            csv_data = (await resp.read()).decode().splitlines()[1:]

        OUI_CSV_CACHE.write_text("\n".join(csv_data))

    csv_reader = csv.DictReader(
        csv_data,
        fieldnames=(
            "registry",
            "assignment",
            "organization_name",
            "organization_address",
        ),
    )

    return {OUIEntry(**row) for row in csv_reader}
