from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Dict, FrozenSet, Optional

from .errors import NeuroLinkerAPIError

DEFAULT_TERMINAL_STATES: FrozenSet[str] = frozenset({"completed", "failed", "pending"})


def _format_timeout_message(
    identifier: str,
    timeout_s: float,
    last: Optional[Dict[str, Any]],
    timeout_context: Optional[Callable[[Optional[Dict[str, Any]]], str]],
) -> str:
    base = f"Timeout waiting for {identifier} after {timeout_s}s. Last status: {last}."
    if timeout_context is None:
        return base
    try:
        extra = timeout_context(last)
    except Exception:
        return base
    return f"{base}{extra}" if extra else base


def wait_for_terminal_status(
    *,
    fetch_status: Callable[[], Dict[str, Any]],
    extract_status: Callable[[Dict[str, Any]], Optional[str]],
    timeout_s: float,
    poll_interval_s: float,
    poll_max_interval_s: float,
    terminal_states: FrozenSet[str] = DEFAULT_TERMINAL_STATES,
    tolerate_404: bool = True,
    identifier: str = "<unknown>",
    timeout_context: Optional[Callable[[Optional[Dict[str, Any]]], str]] = None,
) -> Dict[str, Any]:
    """Poll ``fetch_status`` until a terminal state or timeout."""
    deadline = time.time() + timeout_s
    interval = poll_interval_s
    last: Optional[Dict[str, Any]] = None

    while time.time() < deadline:
        try:
            last = fetch_status()
        except NeuroLinkerAPIError as exc:
            if tolerate_404 and exc.status_code == 404:
                time.sleep(interval)
                interval = min(poll_max_interval_s, interval * 1.5)
                continue
            raise

        status = extract_status(last)
        if status in terminal_states:
            return last

        time.sleep(interval)
        interval = min(poll_max_interval_s, interval * 1.2)

    raise TimeoutError(
        _format_timeout_message(identifier, timeout_s, last, timeout_context)
    )


async def wait_for_terminal_status_async(
    *,
    fetch_status: Callable[[], Awaitable[Dict[str, Any]]],
    extract_status: Callable[[Dict[str, Any]], Optional[str]],
    timeout_s: float,
    poll_interval_s: float,
    poll_max_interval_s: float,
    terminal_states: FrozenSet[str] = DEFAULT_TERMINAL_STATES,
    tolerate_404: bool = True,
    identifier: str = "<unknown>",
    timeout_context: Optional[Callable[[Optional[Dict[str, Any]]], str]] = None,
) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    interval = poll_interval_s
    last: Optional[Dict[str, Any]] = None

    while time.time() < deadline:
        try:
            last = await fetch_status()
        except NeuroLinkerAPIError as exc:
            if tolerate_404 and exc.status_code == 404:
                await asyncio.sleep(interval)
                interval = min(poll_max_interval_s, interval * 1.5)
                continue
            raise

        status = extract_status(last)
        if status in terminal_states:
            return last

        await asyncio.sleep(interval)
        interval = min(poll_max_interval_s, interval * 1.2)

    raise TimeoutError(
        _format_timeout_message(identifier, timeout_s, last, timeout_context)
    )
