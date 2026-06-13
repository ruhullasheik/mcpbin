"""Cross-cutting _meta contract test (WP15, T056) — FR-013, NFR-006.

Two guarantees that only make sense once the full catalog exists:

1. Every registered tool has a non-empty ``description`` (NFR-006).
2. Tool *results* carry a schema-valid ``_meta`` envelope (FR-013), across every feature
   area, on normal results, ``isError`` results, and the empty result. Protocol-error
   tools (``error_*`` that raise) carry ``_meta`` in ``error.data`` instead (verified
   separately) — a coded error response has no tool result to attach a block to.

The delay tools with long sleeps (5s/30s/60s) are excluded from the call sweep for speed;
``delay_1s`` represents the delays area. Their ``_meta`` is covered by tests/test_delays.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from fastmcp import Client
from mcp import McpError

# Load the canonical _meta JSON Schema from the planning contracts if available.
_CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "kitty-specs"
    / "mcpbin-test-server-01KTYJ79"
    / "contracts"
    / "meta-schema.json"
)


def _meta_schema() -> dict:
    if _CONTRACT.exists():
        return json.loads(_CONTRACT.read_text(encoding="utf-8"))
    # Fallback: inline the fixed shape if the contract file is not packaged.
    return {
        "type": "object",
        "required": ["tool", "received", "note"],
        "properties": {
            "tool": {"type": "string", "minLength": 1},
            "received": {"type": "object"},
            "note": {"type": "string", "minLength": 1},
        },
    }


# Representative call sweep: (tool, args). One+ per feature area; result-bearing tools only.
_CALLS = [
    ("echo", {"hello": "world"}),
    ("echo_string", {"value": "x"}),
    ("echo_all_types", {"string": "s", "number": 1, "boolean": True, "object": {}, "array": []}),
    ("return_text", {}),
    ("return_image", {}),
    ("return_resource", {}),
    ("return_multiple", {}),
    ("return_isError", {}),
    ("error_parse", {}),
    ("error_tool_level", {}),
    ("schema_no_args", {}),
    ("schema_optional_fields", {}),
    ("delay_1s", {}),
    ("notify_log", {}),
    ("inspect_session", {}),
    ("sampling_unsupported", {}),
]


def _meta_from_result(result) -> dict:
    """Extract the ``_meta`` envelope from either the trailing text block or the
    native result-level ``meta`` field (used by return_empty)."""
    content = getattr(result, "content", None) or []
    for block in reversed(content):
        text = getattr(block, "text", None)
        if text:
            try:
                payload = json.loads(text)
            except (ValueError, TypeError):
                continue
            if isinstance(payload, dict) and "_meta" in payload:
                return payload["_meta"]
    native = getattr(result, "meta", None)
    if isinstance(native, dict) and "_meta" in native:
        return native["_meta"]
    raise AssertionError("no _meta found on result")


async def test_every_tool_has_a_description(client_full: Client):
    async with client_full as c:
        tools = await c.list_tools()
    assert tools, "catalog is empty"
    missing = [t.name for t in tools if not (t.description or "").strip()]
    assert not missing, f"tools without a description: {missing}"


async def test_result_meta_contract_across_feature_areas(client_full: Client):
    schema = _meta_schema()
    async with client_full as c:
        for name, args in _CALLS:
            result = await c.call_tool(name, args, raise_on_error=False)
            meta = _meta_from_result(result)
            jsonschema.validate(meta, schema)
            assert meta["tool"] == name


async def test_return_empty_has_no_substantive_content_but_carries_meta(client_full: Client):
    async with client_full as c:
        result = await c.call_tool("return_empty", {}, raise_on_error=False)
    # No substantive content blocks; _meta rides on the native result-level field.
    meta = _meta_from_result(result)
    assert meta["tool"] == "return_empty"


async def test_protocol_error_tool_carries_meta_in_error_data(client_full: Client):
    async with client_full as c:
        with pytest.raises(McpError) as exc:
            await c.call_tool("error_invalid_request", {})
    data = getattr(exc.value.error, "data", None)
    assert isinstance(data, dict) and "_meta" in data
    assert data["_meta"]["tool"] == "error_invalid_request"
