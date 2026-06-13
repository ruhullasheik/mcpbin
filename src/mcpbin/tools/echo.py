"""Echo tools feature module (FR-001, FR-013, FR-016).

Seven tools that return their inputs **unchanged**, each result ending with the
fixed ``_meta`` envelope (``contracts/meta-schema.json``). This is the canonical
example of a feature module honoring the ``register(app, profile, ctx)`` contract
from :mod:`mcpbin.registry`.

Why a custom :class:`~fastmcp.tools.tool.Tool` subclass (not ``Tool.from_function``)
-----------------------------------------------------------------------------------
``Tool.from_function`` derives the input schema from a Python signature and
*coerces* incoming arguments to the annotated types (e.g. ``3`` -> ``3.0`` for a
``float`` parameter). The ``_meta`` contract requires ``received`` to be the *raw
parsed arguments* with **no type coercion** (a number stays the exact number the
client sent, a JSON ``int`` stays an ``int``). A base ``Tool`` subclass with a
hand-written ``run(arguments)`` receives the raw, un-coerced argument dict and
advertises an explicit ``inputSchema``, so every echo tool round-trips its input
byte-for-byte (modulo JSON re-serialization).
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp.tools.tool import Tool, ToolResult
from mcp.types import TextContent

from .._meta import append_meta, build_meta
from ..profiles import Profile

# --------------------------------------------------------------------------- #
# Reusable JSON-Schema fragments for the advertised inputSchema of each tool.
# --------------------------------------------------------------------------- #
_FREE_FORM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": True,
}


def _single_value_schema(value_type: str) -> dict[str, Any]:
    """An object schema requiring a single ``value`` of ``value_type``."""
    return {
        "type": "object",
        "properties": {"value": {"type": value_type}},
        "required": ["value"],
        "additionalProperties": False,
    }


_ALL_TYPES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "string": {"type": "string"},
        "number": {"type": "number"},
        "boolean": {"type": "boolean"},
        "object": {"type": "object"},
        "array": {"type": "array"},
    },
    "required": ["string", "number", "boolean", "object", "array"],
    "additionalProperties": False,
}


class _EchoTool(Tool):
    """A tool that echoes the raw arguments it received, unchanged.

    The result is two text content blocks:

    1. ``json.dumps(arguments)`` — the input returned verbatim, and
    2. the ``_meta`` envelope (always the final block, per the ``_meta`` contract),

    whose ``received`` is the exact, un-coerced argument dict.
    """

    note: str = "Echoes the received arguments back, unchanged, per the echo feature area (FR-001)."

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        meta = build_meta(tool=self.name, received=arguments, note=self.note)
        echoed = {"type": "text", "text": json.dumps(arguments)}
        blocks = append_meta([echoed], meta)
        # fastmcp's result conversion only treats native content objects as
        # discrete blocks; a list of plain dicts collapses into one block. Convert
        # each ``{"type": "text", "text": ...}`` dict to a real ``TextContent`` so
        # the echoed value and the ``_meta`` envelope stay separate blocks.
        content = [TextContent(**block) for block in blocks]
        return ToolResult(content=content)


# (name, description, inputSchema) for each of the 7 echo tools.
_ECHO_TOOLS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    (
        "echo",
        "Echo any arguments back unchanged as JSON text. Accepts a free-form "
        "object with arbitrary properties.",
        _FREE_FORM_SCHEMA,
    ),
    (
        "echo_string",
        "Echo a string value back unchanged.",
        _single_value_schema("string"),
    ),
    (
        "echo_number",
        "Echo a numeric value back unchanged (no int/float coercion).",
        _single_value_schema("number"),
    ),
    (
        "echo_boolean",
        "Echo a boolean value back unchanged.",
        _single_value_schema("boolean"),
    ),
    (
        "echo_object",
        "Echo an object (JSON map) value back unchanged.",
        _single_value_schema("object"),
    ),
    (
        "echo_array",
        "Echo an array (JSON list) value back unchanged.",
        _single_value_schema("array"),
    ),
    (
        "echo_all_types",
        "Echo all five JSON types together (string, number, boolean, object, "
        "array), each returned unchanged.",
        _ALL_TYPES_SCHEMA,
    ),
)


def register(app: Any, profile: Profile, ctx: Any) -> None:
    """Register the 7 echo tools on ``app`` (see :mod:`mcpbin.registry`).

    Tools are available under every profile (``profile.tools`` is always ``True``),
    so registration is unconditional. ``ctx`` is unused by echo tools.
    """
    for name, description, schema in _ECHO_TOOLS:
        app.add_tool(
            _EchoTool(name=name, description=description, parameters=schema)
        )


__all__ = ["register"]
