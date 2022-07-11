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
        return f"b{self.date_str}{self.stream}"

    @cached_property
    def date_str(self) -> str:
        version = self.date.strftime("%Y%m%d")
        if self.revision:
            version += f".{self.revision}"

        return version
