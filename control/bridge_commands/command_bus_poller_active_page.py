#!/usr/bin/env python3
"""Active-page route overlay for the GitHub command-bus poller.

Explicit route_task_id remains authoritative. Commands without one bind once to
the fresh visible/focused ChatGPT page registered by Tampermonkey. If no fresh
page exists, dispatch fails closed. Pinned-route fallback is available only for
explicit infrastructure recovery commands carrying [ALLOW_PINNED_ROUTE].
"""
from __future__ import annotations

import time
from pathlib import Path

try:
    import command_bus_poller_base as base
except ImportError:  # repository/unit-test mode
    import command_bus_poller as base

ACTIVE_PAGE_FILE = Path.home() / ".local" / "share" / "prediction-chat-bridge" / "active_page.json"
ACTIVE_PAGE_TTL_SECONDS = 8.0
_BASE_RESOLVE_ROUTE = base.resolve_route


def active_page_route() -> dict | None:
    obj = base.load_json(ACTIVE_PAGE_FILE)
    if not isinstance(obj, dict) or obj.get("active") is not True:
        return None
    try:
        updated = float(obj.get("updated_at_unix", 0.0))
    except Exception:
        return None
    if updated <= 0 or time.time() - updated > ACTIVE_PAGE_TTL_SECONDS:
        return None
    return base.validate_route(obj)


def resolve_route(command: dict) -> tuple[dict | None, str]:
    if command.get("route_task_id"):
        return _BASE_RESOLVE_ROUTE(command)

    route = active_page_route()
    if route is not None:
        return route, "active_page"

    notes = str(command.get("notes") or "")
    if "[ALLOW_PINNED_ROUTE]" in notes:
        return _BASE_RESOLVE_ROUTE(command)
    return None, "active_page_required"


# process_one resolves this global from the base module at runtime.
base.resolve_route = resolve_route


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
