from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HardwareInfo:
    running_under_wine: bool
    osu_md5: str
    adapters_md5: str
    uninstall_md5: str
    disk_md5: str

    adapters: list[str]
