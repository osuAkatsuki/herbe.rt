from __future__ import annotations

from typing import Mapping

from models.geolocation import Country
from models.geolocation import Geolocation


def from_headers(headers: Mapping[str, str]) -> Geolocation:
    ip = headers["X-Real-IP"]  # generally cloudflare's CF-Connecting-IP header

    # https://nginx.org/en/docs/http/ngx_http_geoip_module.html
    iso_code = headers["X-Country-Code"]  # $geoip_city_country_code
    latitude = headers["X-Latitude"]  # $geoip_latitude
    longitude = headers["X-Longitude"]  # $geoip_longitude

    country = Country.from_iso(iso_code)

    geolocation = Geolocation(
        longitude=float(longitude),
        latitude=float(latitude),
        country=country,
        ip=ip,
    )

    return geolocation
