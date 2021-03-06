from __future__ import annotations
import datetime

from typing import Any
from typing import Literal

from pydantic import BaseModel


class OsuVersion(BaseModel):
    date: datetime.date

    stream: Literal["stable", "beta", "cuttingedge", "tourney", "dev"] = "stable"
    revision: int = 0

    def __repr__(self) -> str:
        version = self.date.strftime("%Y%m%d")
        if self.revision:
            version += f".{self.revision}"

        if self.stream != "stable":
            version += self.stream

        return f"b{version}"

    def dict(
        self,
        *args,
        **kwargs,
    ) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "stream": self.stream,
            "revision": self.revision,
        }
