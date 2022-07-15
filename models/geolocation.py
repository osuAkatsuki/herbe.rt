from __future__ import annotations

from pydantic import BaseModel

from constants.geolocation import OSU_GEOLOC


class Country(BaseModel):
    code: int
    acronym: str

    @classmethod
    def from_iso(cls, acronym: str) -> Country:
        # normalise acronym
        acronym = acronym.lower()

        code = OSU_GEOLOC[acronym]
        return Country(code, acronym)


class Geolocation(BaseModel):
    long: float
    lat: float
    country: Country

    ip: str

    def dict(self) -> str:
        return {
            "long": self.long,
            "lat": self.lat,
            "country": self.country.dict(),
        }
