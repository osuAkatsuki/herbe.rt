from __future__ import annotations

from dataclasses import dataclass

from constants.geolocation import OSU_GEOLOC


@dataclass
class Country:
    code: int
    acronym: str

    @classmethod
    def from_iso(cls, acronym: str) -> Country:
        # normalise acronym
        acronym = acronym.lower()

        code = OSU_GEOLOC[acronym]
        return Country(code, acronym)


@dataclass
class Geolocation:
    long: float = 0.0
    lat: float = 0.0
    country: Country = Country(0, "xx")
    ip: str = ""
