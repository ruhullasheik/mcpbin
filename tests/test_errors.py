"""WP06 — error tools conformance tests (T031, FR-003 / FR-013).

Exercises the 7 ``error_*`` tools through the in-memory ``client_full`` fixture and
asserts the *actual surfaced shape* of each error:

* protocol errors raise ``mcp.McpError`` whose ``.error.code`` is the documented code
  (and carry ``_meta`` in ``error.data``);
* ``error_tool_level`` returns a normal ``isError`` result (no raise);
* ``error_parse`` returns a normal result whose text is a ``-32700`` JSON-RPC error
  object, with a ``_meta.note`` mentioning the simulation;
* ``error_unknown_code`` uses a code outside the standard ``-32700..-32603`` range;
* every result (including error results) carries the ``_meta`` envelope.

See ``mcpbin.tools.errors`` for *why* protocol errors must be raised from the wrapped
``CallToolRequest`` handler (fastmcp masks tool-body exceptions into isError results).
"""

from __future__ import annotations

import json

import pytest

from mcp import McpError

from mcpbin.tools.errors import (
    PROTOCOL_ERRORS,
    STANDARD_CODE_MAX,
    STANDARD_CODE_MIN,
    UNKNOWN_CODE,
)

# Reserved standard JSON-RPC codes mcpbin emits (mirrors contracts/protocol.md).
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _text_blocks(result) -> list[str]:
    """Return the text of every text content block in a tool result, in order."""
    texts = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            texts.append(text)
    return texts


def _extract_meta_from_result(result) -> dict:
    """Pull the ``_meta`` envelope out of the final ``{"_meta": ...}`` text block."""
    for text in reversed(_text_blocks(result)):
        try:
            decoded = json.loads(text)
        except (ValueError, TypeError):
            continue
        if isinstance(decoded, dict) and "_meta" in decoded:
            return decoded["_meta"]
    raise AssertionError(f"no _meta text block found in result content: {result.content!r}")


def _assert_meta_shape(meta: dict, tool: str) -> None:
    assert set(["tool", "received", "note"]).issubset(meta.keys())
    assert meta["tool"] == tool
    assert isinstance(meta["received"], dict)
    assert isinstance(meta["note"], str) and meta["note"]


# --------------------------------------------------------------------------- #
# Catalog: all 7 tools are present.
# --------------------------------------------------------------------------- #
async def test_all_error_tools_registered(client_full):
    async with client_full as c:
        names = {t.name for t in await c.list_tools()}
    expected = set(PROTOCOL_ERRORS) | {"error_parse", "error_tool_level"}
    assert expected == {
        "error_invalid_request",
        "error_method_not_found",
        "error_invalid_params",
        "error_internal",
        "error_unknown_code",
        "error_parse",
        "error_tool_level",
    }
    assert expected.issubset(names)


# --------------------------------------------------------------------------- #
# Protocol errors: raise McpError with the documented code + _meta in error.data.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "tool,code",
    [
        ("error_invalid_request", INVALID_REQUEST),
        ("error_method_not_found", METHOD_NOT_FOUND),
        ("error_invalid_params", INVALID_PARAMS),
        ("error_internal", INTERNAL_ERROR),
    ],
)
async def test_protocol_error_surfaces_code(client_full, tool, code):
    async with client_full as c:
        with pytest.raises(McpError) as excinfo:
            await c.call_tool(tool)
    err = excinfo.value.error
    assert err.code == code
    # FR-013: _meta present even on protocol errors (rides in error.data).
    assert err.data is not None, "protocol error should carry data"
    assert "_meta" in err.data
    _assert_meta_shape(err.data["_meta"], tool)


async def test_unknown_code_is_outside_standard_range(client_full):
    async with client_full as c:
        with pytest.raises(McpError) as excinfo:
            await c.call_tool("error_unknown_code")
    err = excinfo.value.error
    assert err.code == UNKNOWN_CODE == -32000
    # The defining property: outside the reserved -32700..-32603 band.
    assert not (STANDARD_CODE_MIN <= err.code <= STANDARD_CODE_MAX)
    assert err.code not in {
        PARSE_ERROR,
        INVALID_REQUEST,
        METHOD_NOT_FOUND,
        INVALID_PARAMS,
        INTERNAL_ERROR,
    }
    assert err.data is not None and "_meta" in err.data
    _assert_meta_shape(err.data["_meta"], "error_unknown_code")


# --------------------------------------------------------------------------- #
# error_parse: SIMULATED — normal result, text is a -32700 JSON-RPC error object.
# --------------------------------------------------------------------------- #
async def test_error_parse_is_simulated_text(client_full):
    async with client_full as c:
        result = await c.call_tool("error_parse")

    # Not a protocol error and not a tool-level error: a normal result.
    assert result.is_error in (False, None)

    # First text block holds a well-formed JSON-RPC error object with code -32700.
    texts = _text_blocks(result)
    envelope = json.loads(texts[0])
    assert envelope["error"]["code"] == PARSE_ERROR == -32700
    assert envelope["error"]["message"]

    # _meta present and its note explains the simulation.
    meta = _extract_meta_from_result(result)
    _assert_meta_shape(meta, "error_parse")
    assert "simulat" in meta["note"].lower()


# --------------------------------------------------------------------------- #
# error_tool_level: isError result (NOT a protocol error) + _meta.
# --------------------------------------------------------------------------- #
async def test_error_tool_level_is_iserror_not_protocol(client_full):
    async with client_full as c:
        # Must NOT raise McpError — it is a tool-level error, surfaced as a result.
        result = await c.call_tool("error_tool_level", raise_on_error=False)

    assert result.is_error is True
    assert _text_blocks(result), "tool-level error should carry >=1 text block"

    meta = _extract_meta_from_result(result)
    _assert_meta_shape(meta, "error_tool_level")


# --------------------------------------------------------------------------- #
# Every error tool carries _meta (protocol errors via error.data, results via block).
# --------------------------------------------------------------------------- #
async def test_every_error_tool_carries_meta(client_full):
    async with client_full as c:
        # Protocol-error tools: _meta in error.data.
        for tool in PROTOCOL_ERRORS:
            with pytest.raises(McpError) as excinfo:
                await c.call_tool(tool)
            meta = excinfo.value.error.data["_meta"]
            _assert_meta_shape(meta, tool)

        # Result-bearing tools: _meta in the trailing text block.
        for tool in ("error_parse", "error_tool_level"):
            result = await c.call_tool(tool, raise_on_error=False)
            _assert_meta_shape(_extract_meta_from_result(result), tool)
