from __future__ import annotations

import asyncio
import contextlib
import logging

import aiohttp
import aioredis
import databases

import settings

http: aiohttp.ClientSession

write_database: databases.Database
read_database: databases.Database

redis: aioredis.Redis

tasks: set[asyncio.Task] = set()

ctx_stack: contextlib.AsyncExitStack = contextlib.AsyncExitStack()


async def connect_services() -> None:
    global http, write_database, read_database, redis

    http = await ctx_stack.enter_async_context(aiohttp.ClientSession())
    write_database = await ctx_stack.enter_async_context(
        databases.Database(settings.WRITE_DB_DSN),
    )
    read_database = await ctx_stack.enter_async_context(
        databases.Database(settings.READ_DB_DSN),
    )
    redis = await ctx_stack.enter_async_context(
        aioredis.from_url(settings.REDIS_DSN),
    )


async def disconnect_services() -> None:
    await cancel_tasks()
    await ctx_stack.aclose()


async def cancel_tasks() -> None:
    logging.info(f"Cancelling {len(tasks)} tasks.")

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    loop = asyncio.get_running_loop()
    for task in tasks:
        if not task.cancelled():
            if exception := task.exception():
                loop.call_exception_handler(
                    {
                        "message": "unhandled exception during loop shutdown",
                        "exception": exception,
                        "task": task,
                    },
                )
