from __future__ import annotations

from pydantic import BaseModel


class LoginData(BaseModel):
    username: str
    password_md5: bytes
    osu_version: str
    utc_offset: int
    display_city: bool
    pm_private: bool
    osu_path_md5: str
    adapters_str: str
    adapters_md5: str
    uninstall_md5: str
    disk_signature_md5: str


class LoginResponse(BaseModel):
    body: bytes
    token: str = "no"
