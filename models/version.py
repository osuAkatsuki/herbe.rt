from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import cached_property
from typing import Literal


@dataclass
class OsuVersion:
    date: date

    stream: Literal["stable", "beta", "cuttingedge", "tourney", "dev"] = "stable"
    revision: int = 0

    def __repr__(self) -> str:
        version = self.date.strftime("%Y%m%d")
        if self.revision:
            version += f".{self.revision}"

        if self.stream != "stable":
            version += self.stream

        return f"b{version}"
