from __future__ import annotations

import services
from models.user import Account


async def update_privileges(account: Account) -> None:
    await services.write_database.execute(
        "UPDATE users SET privileges = :privs WHERE id = :id",
        {"privs": account.privileges, "id": account.id},
    )
