from __future__ import annotations

from pydantic import BaseModel


class HardwareInfo(BaseModel):
    running_under_wine: bool

    osu_md5: str
    adapters_md5: str
    uninstall_md5: str
    disk_md5: str

    adapters: list[str]


class OUIEntry(BaseModel):
    registry: str
    assignment: str
    organisation_name: str
    organization_address: str
