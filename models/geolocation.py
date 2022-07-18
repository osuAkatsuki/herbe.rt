from __future__ import annotations

from typing import Any
from typing import Optional

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
        return Country(code=code, acronym=acronym)


class Geolocation(BaseModel):
    long: float
    lat: float
    country: Country

    ip: Optional[str] = None

    def dict(
        self,
        *args,
        **kwargs,
    ) -> dict[str, Any]:
        return {
            "long": self.long,
            "lat": self.lat,
            "country": self.country.dict(),
        }
