from __future__ import annotations

from typing import Any

import services
from models.geolocation import Country
from models.geolocation import Geolocation

GEOLOCATION: dict[str, Geolocation]


def from_headers(headers: dict[str, str]) -> Geolocation:
    if not (ip := headers.get("CF-Connecting-IP")):
        forwards = headers["X-Forwarded-For"].split(",")

        if len(forwards) != 1:
            ip = forwards[0]
        else:
            ip = headers["X-Real-IP"]

    if not (geoloc := GEOLOCATION.get(ip)):
        city = services.geolocation.city(ip)

        iso_code = city.country.iso_code.lower()
        country = Country.from_iso(iso_code)

        geolocation = Geolocation(
            city.location.longitude,
            city.location.latitude,
            country,
            ip,
        )

        GEOLOCATION[ip] = geoloc

    return geolocation
