"""Notification tool tests (WP09, T040) — FR-009.

These build their own clients (not the shared fixtures) so they can attach the
progress/log/message handlers needed to capture server->client notifications.
"""

from __future__ import annotations

import asyncio

from fastmcp import Client

from mcpbin.server import build_app


async def test_list_changed_and_resource_updated_notifications():
    methods: list[str] = []

    async def message_handler(message):
        root = getattr(message, "root", message)
        method = getattr(root, "method", None)
        if method:
            methods.append(method)

    app = build_app("full", "stdio")
    async with Client(app, message_handler=message_handler) as c:
        await c.call_tool("notify_tool_list_changed", {})
        await c.call_tool("notify_resource_list_changed", {})
        await c.call_tool("notify_prompt_list_changed", {})
        await c.call_tool("notify_resource_updated", {})
        await asyncio.sleep(0.05)  # let the handler drain

    assert "notifications/tools/list_changed" in methods
    assert "notifications/resources/list_changed" in methods
    assert "notifications/prompts/list_changed" in methods
    assert "notifications/resources/updated" in methods


async def test_notify_progress_sends_at_least_three():
    events: list[tuple] = []

    async def progress_handler(progress, total, message):
        events.append((progress, total, message))

    app = build_app("full", "stdio")
    async with Client(app, progress_handler=progress_handler) as c:
        await c.call_tool("notify_progress", {})
        await asyncio.sleep(0.05)

    assert len(events) >= 3


async def test_notify_log_covers_all_levels():
    levels: list[str] = []

    async def log_handler(message):
        level = getattr(message, "level", None)
        if level is None and hasattr(message, "params"):
            level = getattr(message.params, "level", None)
        if level:
            levels.append(str(level))

    app = build_app("full", "stdio")
    async with Client(app, log_handler=log_handler) as c:
        await c.call_tool("notify_log", {})
        await asyncio.sleep(0.05)

    for expected in ("debug", "info", "warning", "error"):
        assert any(expected in lvl for lvl in levels), f"missing log level {expected}: {levels}"
