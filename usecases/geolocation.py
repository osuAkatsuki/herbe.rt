from __future__ import annotations

from typing import Mapping

import services
from models.geolocation import Country
from models.geolocation import Geolocation

CACHE: dict[str, Geolocation] = {}


def from_headers(headers: Mapping[str, str]) -> Geolocation:
    if not (ip := headers.get("CF-Connecting-IP")):
        forwards = headers["X-Forwarded-For"].split(",")

        if len(forwards) != 1:
            ip = forwards[0]
        else:
            ip = headers["X-Real-IP"]

    if geolocation := CACHE.get(ip):
        return geolocation

    city = services.geolocation.city(ip)

    assert city.country.iso_code is not None
    assert city.location.longitude is not None
    assert city.location.latitude is not None

    iso_code = city.country.iso_code.lower()
    country = Country.from_iso(iso_code)

    geolocation = Geolocation(
        long=city.location.longitude,
        lat=city.location.latitude,
        country=country,
        ip=ip,
    )

    return geolocation
