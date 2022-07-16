from __future__ import annotations

import random

import services
from models.icon import MenuIcon


async def fetch_all() -> list[MenuIcon]:
    db_icons = await services.database.fetch_all(
        "SELECT * FROM main_menu_icons WHERE is_current = 1",
    )
    return [
        MenuIcon(image_url=db_icon["file_id"], click_url=db_icon["url"])
        for db_icon in db_icons
    ]


async def fetch_random() -> MenuIcon:
    return random.choice(await fetch_all())
