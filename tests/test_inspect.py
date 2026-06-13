"""Protocol inspection tests (WP11, T046) — FR-012, FR-013.

Verifies ``inspect_session`` returns the five required fields and that
``requestCount`` increments across calls within a session.
"""

from __future__ import annotations

import json
import re

from fastmcp import Client


def _payload(result) -> dict:
    """First content block is the JSON metadata payload."""
    return json.loads(result.content[0].text)


def _meta(result) -> dict:
    return json.loads(result.content[-1].text)["_meta"]


async def test_inspect_session_returns_all_fields(client_full: Client):
    async with client_full as c:
        await c.list_tools()
        result = await c.call_tool("inspect_session", {})
        payload = _payload(result)
        # inspect_session reports the ACTUAL negotiated protocol version (a diagnostic
        # tool must reflect the real handshake, not a hardcoded target). The installed
        # MCP SDK negotiates a dated version string (e.g. 2025-11-25), which may differ
        # from the PRD's assumed 2025-03-26 (C-005) depending on SDK version.
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", payload["protocolVersion"])
        assert set(payload) == {
            "protocolVersion",
            "clientInfo",
            "negotiatedCapabilities",
            "transport",
            "requestCount",
        }
        assert "name" in payload["clientInfo"]
        # full profile advertises tools/resources/prompts/sampling
        caps = payload["negotiatedCapabilities"]
        assert caps["tools"] and caps["resources"] and caps["prompts"] and caps["sampling"]
        assert _meta(result)["tool"] == "inspect_session"


async def test_request_count_increments_within_session(client_full: Client):
    async with client_full as c:
        await c.list_tools()
        first = _payload(await c.call_tool("inspect_session", {}))["requestCount"]
        second = _payload(await c.call_tool("inspect_session", {}))["requestCount"]
        third = _payload(await c.call_tool("inspect_session", {}))["requestCount"]
        assert second == first + 1
        assert third == second + 1
