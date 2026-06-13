"""Cross-cutting capability-profile test (WP15, T058) — FR-011.

Verifies all four profiles advertise the documented capability subset and that omitted
capabilities' list methods return JSON-RPC -32601 (not an empty list), with minimal
omitting listChanged.
"""

from __future__ import annotations

import pytest
from fastmcp import Client
from mcp import McpError

from mcpbin.errors import METHOD_NOT_FOUND
from mcpbin.server import build_app


def _client(profile: str) -> Client:
    return Client(build_app(profile, "stdio"))


async def _caps(profile: str):
    async with _client(profile) as c:
        return c.initialize_result.capabilities


async def test_full_advertises_everything():
    caps = await _caps("full")
    assert caps.tools is not None
    assert caps.resources is not None
    assert caps.prompts is not None


async def test_tools_only_gates_resources_and_prompts():
    caps = await _caps("tools-only")
    assert caps.tools is not None
    assert caps.resources is None
    assert caps.prompts is None
    async with _client("tools-only") as c:
        for method in ("list_resources_mcp", "list_prompts_mcp"):
            with pytest.raises(McpError) as exc:
                await getattr(c, method)()
            assert exc.value.error.code == METHOD_NOT_FOUND


async def test_minimal_gates_and_omits_list_changed():
    caps = await _caps("minimal")
    assert caps.tools is not None
    assert caps.resources is None and caps.prompts is None
    # minimal must not advertise listChanged on tools.
    assert getattr(caps.tools, "listChanged", None) in (None, False)
    async with _client("minimal") as c:
        with pytest.raises(McpError) as exc:
            await c.list_resources_mcp()
        assert exc.value.error.code == METHOD_NOT_FOUND


async def test_no_sampling_keeps_lists_but_degrades_sampling():
    caps = await _caps("no-sampling")
    assert caps.resources is not None and caps.prompts is not None
    async with _client("no-sampling") as c:
        # Non-sampling operations work; sampling tool degrades gracefully (isError).
        result = await c.call_tool("sampling_unsupported", {}, raise_on_error=False)
        assert result.is_error is True
