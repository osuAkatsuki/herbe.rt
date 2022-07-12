from __future__ import annotations

from pydantic import BaseModel


class Channel(BaseModel):
    id: int
    name: str
    description: str

    public_read: bool
    public_write: bool
    temp: bool
    hidden: bool

    members: set[int]
