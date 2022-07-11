from __future__ import annotations

from typing import Optional


def parse_adapters(adapters_str: str) -> Optional[tuple[list[str], bool]]:
    running_under_wine = adapters_str == "runningunderwine"
    adapters = [adapter for adapter in adapters_str[:-1].split(".")]

    if not (running_under_wine or any(adapters)):
        return None

    return adapters, running_under_wine
