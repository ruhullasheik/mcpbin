"""Echo tools tests (WP04, T024) — FR-001, FR-013.

Exercises the 7 echo tools through the in-memory ``client_full`` fixture (WP03):

* every tool round-trips its input **unchanged** (no type coercion),
* every result ends with a ``_meta`` block whose ``tool`` is the tool name and
  whose ``received`` equals the exact arguments sent, and
* ``echo_all_types`` returns all five JSON types together.

Note on ``_discover``/``list_tools`` before ``call_tool``
--------------------------------------------------------
These tests call ``await c.list_tools()`` before invoking a tool. This mirrors how
real MCP clients behave (they discover the catalog via ``tools/list`` before calling
anything) and populates the low-level server's tool cache. It is also required to
work around a **foundation defect in WP03's server** (``mcpbin.server``): the
pagination wrapper installed on the ``ListToolsRequest`` handler dereferences
``req.method`` unconditionally, but mcp's ``_get_cached_tool_definition`` refreshes a
cold tool cache by invoking that handler with ``None`` — so a tool call made *before*
any ``tools/list`` crashes with ``'NoneType' object has no attribute 'method'``. This
affects every tool (not echo specifically) and should be fixed in ``server.py``
(``_with_cursor`` / the wrapped handler must tolerate ``req is None``).
"""

from __future__ import annotations

import json

import pytest
from fastmcp import Client

# The 7 echo tools the module must register (contracts/tools.md -> echo).
ECHO_TOOL_NAMES = {
    "echo",
    "echo_string",
    "echo_number",
    "echo_boolean",
    "echo_object",
    "echo_array",
    "echo_all_types",
}


async def _call(client: Client, name: str, args: dict):
    """Open the in-memory client, discover tools, then call ``name`` with ``args``.

    Discovery (``list_tools``) precedes the call exactly as a real MCP client would.
    """
    async with client as c:
        await c.list_tools()
        return await c.call_tool(name, args)


def _text_blocks(result) -> list[str]:
    """Return the ``.text`` of every text content block in a call result."""
    return [b.text for b in result.content if getattr(b, "type", None) == "text"]


def _echoed_value(result):
    """The first text block is the echoed input, JSON-decoded."""
    return json.loads(_text_blocks(result)[0])


def _meta(result) -> dict:
    """The final text block is ``{"_meta": {...}}``; return the inner envelope."""
    decoded = json.loads(_text_blocks(result)[-1])
    assert set(decoded.keys()) == {"_meta"}, "final block must be the _meta envelope"
    return decoded["_meta"]


# --------------------------------------------------------------------------- #
# Registration / catalog presence.
# --------------------------------------------------------------------------- #
async def test_all_seven_echo_tools_registered(client_full: Client):
    async with client_full as c:
        names = {t.name for t in await c.list_tools()}
    assert ECHO_TOOL_NAMES <= names


async def test_every_echo_tool_has_a_description(client_full: Client):
    async with client_full as c:
        tools = {t.name: t for t in await c.list_tools() if t.name in ECHO_TOOL_NAMES}
    assert set(tools) == ECHO_TOOL_NAMES
    for name, tool in tools.items():
        assert tool.description, f"{name} must have a description (FR-016)"


# --------------------------------------------------------------------------- #
# Round-trip: input returned unchanged + correct _meta.
# --------------------------------------------------------------------------- #
ROUND_TRIP_CASES = [
    ("echo", {"message": "hello", "n": 7, "flag": True, "nested": {"a": [1, 2]}}),
    ("echo", {}),  # free-form accepts no args too
    ("echo_string", {"value": "hello world"}),
    ("echo_string", {"value": ""}),
    ("echo_number", {"value": 42}),  # int stays int (no coercion to float)
    ("echo_number", {"value": 3.14}),
    ("echo_number", {"value": -0.0}),
    ("echo_boolean", {"value": True}),
    ("echo_boolean", {"value": False}),
    ("echo_object", {"value": {"k": "v", "deep": {"x": [1, {"y": 2}]}}}),
    ("echo_object", {"value": {}}),
    ("echo_array", {"value": [1, "two", False, None, {"k": 1}]}),
    ("echo_array", {"value": []}),
]


@pytest.mark.parametrize("tool,args", ROUND_TRIP_CASES)
async def test_echo_round_trips_input_unchanged(client_full: Client, tool, args):
    result = await _call(client_full, tool, args)

    # 1. Input returned verbatim as the first JSON text block.
    assert _echoed_value(result) == args

    # 2. _meta.tool is the tool name and _meta.received is the exact sent args.
    meta = _meta(result)
    assert meta["tool"] == tool
    assert meta["received"] == args
    assert isinstance(meta["note"], str) and meta["note"]


@pytest.mark.parametrize("tool,args", ROUND_TRIP_CASES)
async def test_echo_meta_is_always_the_final_block(client_full: Client, tool, args):
    result = await _call(client_full, tool, args)
    blocks = _text_blocks(result)
    # At least the echoed value + the _meta envelope.
    assert len(blocks) >= 2
    # Only the final block is the _meta envelope.
    assert "_meta" in json.loads(blocks[-1])
    assert "_meta" not in json.loads(blocks[0])


# --------------------------------------------------------------------------- #
# Type fidelity: numbers/booleans are preserved, never coerced.
# --------------------------------------------------------------------------- #
async def test_echo_number_preserves_int_vs_float(client_full: Client):
    as_int = _echoed_value(await _call(client_full, "echo_number", {"value": 5}))["value"]
    as_float = _echoed_value(
        await _call(client_full, "echo_number", {"value": 5.0})
    )["value"]
    assert as_int == 5 and isinstance(as_int, int)
    assert isinstance(as_float, float)


async def test_echo_boolean_stays_boolean_not_int(client_full: Client):
    value = _echoed_value(
        await _call(client_full, "echo_boolean", {"value": True})
    )["value"]
    assert value is True
    assert isinstance(value, bool)


# --------------------------------------------------------------------------- #
# echo_all_types returns all five JSON types together.
# --------------------------------------------------------------------------- #
async def test_echo_all_types_returns_all_five(client_full: Client):
    args = {
        "string": "s",
        "number": 1.5,
        "boolean": True,
        "object": {"k": "v"},
        "array": [1, 2, 3],
    }
    result = await _call(client_full, "echo_all_types", args)

    echoed = _echoed_value(result)
    assert set(echoed.keys()) == {"string", "number", "boolean", "object", "array"}
    assert echoed == args

    meta = _meta(result)
    assert meta["tool"] == "echo_all_types"
    assert meta["received"] == args
