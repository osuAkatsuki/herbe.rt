from __future__ import annotations

from typing import Union


def make_safe_name(name: str) -> str:
    return name.lower().replace(" ", "_")


TIME_ORDER_SUFFIXES = ("ns", "μs", "ms", "s")


def format_time(time: Union[int, float]) -> str:
    for suffix in TIME_ORDER_SUFFIXES:
        if time < 1000:
            break

        time /= 1000

    return f"{time:.2f}{suffix}"
