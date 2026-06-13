"""Tests for the response-type tools (WP05, T028, FR-002/FR-013).

Drives the six tools through the in-memory ``client_full`` fixture and asserts each
returns the expected MCP content type(s), that ``return_image`` carries a real PNG,
that ``return_multiple`` mixes ≥3 distinct types, that ``return_isError`` sets
``isError``, that ``return_empty`` matches the chosen ``_meta`` reconciliation, and
that *every* result carries the ``_meta`` envelope.
"""

from __future__ import annotations

import base64
import json

import mcp.types as mcp_types
import pytest
from fastmcp import Client

PNG_SIGNATURE = b"\x89PNG"

ALL_TOOLS = [
    "return_text",
    "return_image",
    "return_resource",
    "return_multiple",
    "return_empty",
    "return_isError",
]


def _extract_meta(result: mcp_types.CallToolResult) -> dict:
    """Return the ``_meta`` envelope from either representation, or ``{}`` if absent.

    Two channels are valid (see ``tools/response_types.py``):
    * the native result-level ``_meta`` field (used by ``return_empty``), or
    * the trailing ``text`` content block whose JSON is ``{"_meta": {...}}``.
    Both carry an identical ``{"_meta": {tool, received, note}}`` object.
    """
    if result.meta and "_meta" in result.meta:
        return result.meta["_meta"]
    for block in reversed(result.content):
        if isinstance(block, mcp_types.TextContent):
            try:
                payload = json.loads(block.text)
            except (ValueError, TypeError):
                continue
            if isinstance(payload, dict) and "_meta" in payload:
                return payload["_meta"]
    return {}


# --------------------------------------------------------------------------- #
# Registration / discovery.
# --------------------------------------------------------------------------- #
async def test_all_six_tools_registered(client_full: Client):
    async with client_full as c:
        # list_tools() auto-paginates the full catalog; list_tools_mcp() returns only
        # the first 10-item page (fine in isolation, but the integrated catalog spans
        # multiple pages — this must follow all pages to see return_*).
        names = {t.name for t in await c.list_tools()}
    for tool in ALL_TOOLS:
        assert tool in names, f"{tool} not registered"


# --------------------------------------------------------------------------- #
# Per-tool content shapes.
# --------------------------------------------------------------------------- #
async def test_return_text_one_text_block(client_full: Client):
    async with client_full as c:
        result = await c.call_tool_mcp("return_text", {})
    assert result.isError is False
    texts = [b for b in result.content if isinstance(b, mcp_types.TextContent)]
    # One substantive text block + the trailing _meta text block.
    assert len(texts) == 2
    assert all(isinstance(b, mcp_types.TextContent) for b in result.content)


async def test_return_image_is_png(client_full: Client):
    async with client_full as c:
        result = await c.call_tool_mcp("return_image", {})
    images = [b for b in result.content if isinstance(b, mcp_types.ImageContent)]
    assert len(images) == 1
    img = images[0]
    assert img.mimeType == "image/png"
    raw = base64.b64decode(img.data)
    assert raw.startswith(PNG_SIGNATURE), "image data is not a valid PNG"


async def test_return_resource_has_embedded_resource(client_full: Client):
    async with client_full as c:
        result = await c.call_tool_mcp("return_resource", {})
    resources = [b for b in result.content if isinstance(b, mcp_types.EmbeddedResource)]
    assert len(resources) == 1
    embedded = resources[0].resource
    assert str(embedded.uri)  # a valid, non-empty URI
    assert isinstance(embedded, mcp_types.TextResourceContents)
    assert embedded.text


async def test_return_multiple_has_three_distinct_types(client_full: Client):
    async with client_full as c:
        result = await c.call_tool_mcp("return_multiple", {})
    types = {type(b) for b in result.content}
    assert mcp_types.TextContent in types
    assert mcp_types.ImageContent in types
    assert mcp_types.EmbeddedResource in types
    assert len(types) >= 3


async def test_return_empty_has_no_substantive_content(client_full: Client):
    """Chosen reconciliation: truly empty content + native result-level ``_meta``."""
    async with client_full as c:
        result = await c.call_tool_mcp("return_empty", {})
    assert result.isError is False
    # No substantive content blocks: content is empty.
    assert result.content == []
    # The envelope lives on the native result-level _meta field for this tool.
    assert result.meta is not None
    assert "_meta" in result.meta


async def test_return_is_error_sets_is_error(client_full: Client):
    async with client_full as c:
        result = await c.call_tool_mcp("return_isError", {})
    assert result.isError is True
    texts = [b for b in result.content if isinstance(b, mcp_types.TextContent)]
    assert len(texts) >= 1


# --------------------------------------------------------------------------- #
# Universal _meta envelope (FR-013).
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tool", ALL_TOOLS)
async def test_every_result_carries_meta(client_full: Client, tool: str):
    async with client_full as c:
        result = await c.call_tool_mcp(tool, {})
    meta = _extract_meta(result)
    assert meta, f"{tool} result is missing its _meta envelope"
    assert meta["tool"] == tool
    assert "received" in meta
    assert isinstance(meta["note"], str) and meta["note"]
