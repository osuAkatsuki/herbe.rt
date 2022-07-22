from __future__ import annotations

from typing import Optional

import services
import utils
from models.user import Account


async def fetch_by_id(id: int) -> Optional[Account]:
    db_account = await services.read_database.fetch_one(
        "SELECT * FROM users WHERE id = :id",
        {"id": id},
    )
    if not db_account:
        return None

    country = await services.read_database.fetch_val(
        "SELECT country FROM users_stats WHERE id = :id",
        {"id": id},
    )

    friends = await services.read_database.fetch_all(
        "SELECT user2 FROM users_relationships WHERE user1 = :id",
        {"id": id},
    )
    friends_list = [entry["user2"] for entry in friends]

    return Account(
        id=db_account["id"],
        name=db_account["username"],
        email=db_account["email"],
        privileges=db_account["privileges"],
        password_bcrypt=db_account["password_md5"],
        country=country,
        friends=friends_list,
        clan_id=db_account["clan_id"],
        clan_privileges=db_account["clan_privileges"],
        silence_end=db_account["silence_end"],
        donor_expire=db_account["donor_expire"],
        freeze_end=db_account["frozen"],
    )


async def fetch_by_name(name: str) -> Optional[Account]:
    db_account = await services.read_database.fetch_one(
        "SELECT * FROM users WHERE username_safe = :safe_name",
        {"safe_name": utils.make_safe_name(name)},
    )
    if not db_account:
        return None

    country = await services.read_database.fetch_val(
        "SELECT country FROM users_stats WHERE id = :id",
        {"id": db_account["id"]},
    )

    friends = await services.read_database.fetch_all(
        "SELECT user2 FROM users_relationships WHERE user1 = :id",
        {"id": db_account["id"]},
    )
    friends_list = [entry["user2"] for entry in friends]

    return Account(
        id=db_account["id"],
        name=db_account["username"],
        email=db_account["email"],
        privileges=db_account["privileges"],
        password_bcrypt=db_account["password_md5"],
        country=country,
        friends=friends_list,
        clan_id=db_account["clan_id"],
        clan_privileges=db_account["clan_privileges"],
        silence_end=db_account["silence_end"],
        donor_expire=db_account["donor_expire"],
        freeze_end=db_account["frozen"],
    )
