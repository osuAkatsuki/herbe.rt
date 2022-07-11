from __future__ import annotations

from dataclasses import dataclass

from models.hardware import HardwareInfo
from models.version import OsuVersion


@dataclass
class SessionInfo:
    client: OsuVersion
    hardware: HardwareInfo
