from __future__ import annotations

from models.login import LoginData


def parse_login_data(data: bytearray) -> LoginData:
    (
        username,
        password_md5,
        remainder,
    ) = data.decode().split("\n", maxsplit=2)

    (
        osu_version,
        utc_offset,
        display_city,
        client_hashes,
        pm_private,
    ) = remainder.split("|", maxsplit=4)

    (
        osu_path_md5,
        adapters_str,
        adapters_md5,
        uninstall_md5,
        disk_signature_md5,
    ) = client_hashes[:-1].split(":", maxsplit=4)

    return LoginData(
        username=username,
        password_md5=password_md5.encode(),
        osu_version=osu_version,
        utc_offset=int(utc_offset),
        display_city=display_city == "1",
        pm_private=pm_private == "1",
        osu_path_md5=osu_path_md5,
        adapters_str=adapters_str,
        adapters_md5=adapters_md5,
        uninstall_md5=uninstall_md5,
        disk_signature_md5=disk_signature_md5,
    )
