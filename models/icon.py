from __future__ import annotations

from pydantic import BaseModel


class MenuIcon(BaseModel):
    image_url: str
    click_url: str
