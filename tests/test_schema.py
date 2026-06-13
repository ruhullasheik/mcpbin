"""Schema validation tools tests (WP08, T037) — FR-005, FR-013.

Exercises the 6 schema tools through the in-memory ``client_full`` fixture (WP03):
required/optional/enum/nested/array/no-args behavior + the ``_meta`` envelope on
successful results. Invalid calls (missing required, off-enum) must be rejected.
"""

from __future__ import annotations

import json

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcp import McpError

SCHEMA_TOOL_NAMES = {
    "schema_required_fields",
    "schema_optional_fields",
    "schema_enum",
    "schema_nested",
    "schema_array_items",
    "schema_no_args",
}

# A call rejected by fastmcp argument validation surfaces as one of these.
INVALID_CALL_ERRORS = (ToolError, McpError, Exception)


def _meta_of(result) -> dict:
    """Extract the trailing ``_meta`` envelope from a tool result's content blocks."""
    last = result.content[-1]
    payload = json.loads(last.text)
    return payload["_meta"]


async def test_all_schema_tools_registered(client_full: Client):
    async with client_full as c:
        names = {t.name for t in await c.list_tools()}
    assert SCHEMA_TOOL_NAMES <= names


async def test_required_fields_present_succeeds_and_has_meta(client_full: Client):
    async with client_full as c:
        await c.list_tools()
        result = await c.call_tool("schema_required_fields", {"name": "x", "count": 3})
        meta = _meta_of(result)
        assert meta["tool"] == "schema_required_fields"
        assert meta["received"] == {"name": "x", "count": 3}


async def test_required_fields_missing_errors(client_full: Client):
    async with client_full as c:
        await c.list_tools()
        with pytest.raises(INVALID_CALL_ERRORS):
            await c.call_tool("schema_required_fields", {"name": "x"})  # missing count


async def test_optional_fields_omitted_succeeds(client_full: Client):
    async with client_full as c:
        await c.list_tools()
        result = await c.call_tool("schema_optional_fields", {})
        meta = _meta_of(result)
        assert meta["tool"] == "schema_optional_fields"


async def test_enum_valid_value_succeeds(client_full: Client):
    async with client_full as c:
        await c.list_tools()
        result = await c.call_tool("schema_enum", {"color": "green"})
        assert _meta_of(result)["received"] == {"color": "green"}


async def test_enum_invalid_value_errors(client_full: Client):
    async with client_full as c:
        await c.list_tools()
        with pytest.raises(INVALID_CALL_ERRORS):
            await c.call_tool("schema_enum", {"color": "purple"})


async def test_nested_object_round_trips(client_full: Client):
    person = {
        "name": "Ada",
        "age": 36,
        "address": {"street": "1 Analytical Way", "city": "London", "geo": {"lat": 51.5, "lng": -0.1}},
    }
    async with client_full as c:
        await c.list_tools()
        result = await c.call_tool("schema_nested", {"person": person})
        assert _meta_of(result)["received"]["person"] == person


async def test_array_items_round_trips(client_full: Client):
    async with client_full as c:
        await c.list_tools()
        result = await c.call_tool("schema_array_items", {"items": [1, 2, 3]})
        assert _meta_of(result)["received"]["items"] == [1, 2, 3]


async def test_no_args_succeeds(client_full: Client):
    async with client_full as c:
        await c.list_tools()
        result = await c.call_tool("schema_no_args", {})
        assert _meta_of(result)["tool"] == "schema_no_args"
