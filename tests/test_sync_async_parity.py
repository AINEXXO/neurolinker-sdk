from __future__ import annotations

import asyncio
import inspect
from typing import Any, Dict

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker

# ---------------------------------------------------------------------------
# Methods that are intentionally asymmetric (lifecycle dunder-equivalents).
# ---------------------------------------------------------------------------
ALLOWED_SYNC_ONLY = {"close"}
ALLOWED_ASYNC_ONLY = {"aclose"}


def _walk_public_methods(obj: Any, prefix: str = "") -> Dict[str, inspect.Signature]:
    """Walk all public attributes, returning ``{dotted_name: signature}`` for callables.

    Recurses into attributes whose class lives in the ``neurolinker_sdk`` package
    (Module instances and Resource instances), so we cover the full nested API.
    """
    out: Dict[str, inspect.Signature] = {}
    for name, attr in inspect.getmembers(obj):
        if name.startswith("_"):
            continue
        full = f"{prefix}.{name}" if prefix else name

        if inspect.ismethod(attr) or inspect.iscoroutinefunction(attr):
            try:
                out[full] = inspect.signature(attr)
            except (TypeError, ValueError):
                pass
            continue

        # Recurse into nested SDK objects (Modules, Resources).
        cls = type(attr)
        module_name = getattr(cls, "__module__", "") or ""
        if module_name.startswith("neurolinker_sdk") and not callable(attr):
            out.update(_walk_public_methods(attr, full))

    return out


def _build_surface_maps() -> tuple[Dict[str, inspect.Signature], Dict[str, inspect.Signature]]:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as sync_client:
        sync_map = _walk_public_methods(sync_client)

    async def _async_surface() -> Dict[str, inspect.Signature]:
        async with AsyncNeuroLinker(token="nl_dummy", timeout_s=1.0) as async_client:
            return _walk_public_methods(async_client)

    async_map = asyncio.run(_async_surface())
    return sync_map, async_map


def test_no_methods_only_in_sync_client() -> None:
    sync_map, async_map = _build_surface_maps()
    only_sync = set(sync_map) - set(async_map) - ALLOWED_SYNC_ONLY
    assert not only_sync, (
        f"Methods exist on the sync client but not on the async client: {sorted(only_sync)}. "
        f"Add the async counterpart, or whitelist in ALLOWED_SYNC_ONLY if intentional."
    )


def test_no_methods_only_in_async_client() -> None:
    sync_map, async_map = _build_surface_maps()
    only_async = set(async_map) - set(sync_map) - ALLOWED_ASYNC_ONLY
    assert not only_async, (
        f"Methods exist on the async client but not on the sync client: {sorted(only_async)}. "
        f"Add the sync counterpart, or whitelist in ALLOWED_ASYNC_ONLY if intentional."
    )


def test_shared_methods_have_matching_signatures() -> None:
    sync_map, async_map = _build_surface_maps()
    shared = set(sync_map) & set(async_map)
    mismatched = {
        name: (str(sync_map[name]), str(async_map[name]))
        for name in shared
        if str(sync_map[name]) != str(async_map[name])
    }
    assert not mismatched, (
        "Sync and async clients have methods with diverging signatures:\n"
        + "\n".join(f"  {n}:\n    sync : {s}\n    async: {a}" for n, (s, a) in sorted(mismatched.items()))
    )


def test_surface_is_non_trivial() -> None:
    """Sanity check: parity tests would silently pass on an empty surface."""
    sync_map, async_map = _build_surface_maps()
    assert len(sync_map) >= 30, f"Sync surface looks too small: {len(sync_map)} methods"
    assert len(async_map) >= 30, f"Async surface looks too small: {len(async_map)} methods"
