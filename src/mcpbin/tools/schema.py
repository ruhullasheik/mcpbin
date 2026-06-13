"""Schema validation tools (FR-005): strict input schemas a client must satisfy.

Six tools that exercise the JSON-Schema shapes a client's tool UI / validation layer
should handle:

* ``schema_required_fields`` – required fields; missing one is a validation error.
* ``schema_optional_fields`` – all optional; omitting them succeeds.
* ``schema_enum``            – a field restricted to an enum; an off-enum value errors.
* ``schema_nested``          – a deeply nested object; accepted and echoed back.
* ``schema_array_items``     – a typed array (``list[int]``); accepted and echoed back.
* ``schema_no_args``         – no declared parameters; succeeds with no arguments.

Validation strategy (fastmcp 3.4.2)
-----------------------------------
These tools are registered via ``@app.tool`` (i.e. ``Tool.from_function``), which
derives a JSON Schema from the typed Python signature / pydantic models and validates
incoming arguments **before** the body runs. So a missing required field or an
off-enum value is rejected by fastmcp's argument validation (surfaced to the client as
a tool error) without the body executing — exactly what FR-005 requires. On success the
body returns a :class:`ToolResult` whose final content block is the ``_meta`` envelope
(``contracts/meta-schema.json``), matching every other mcpbin tool.

Because validation happens before the body, a *rejected* call produces no tool result
(hence no ``_meta``) — consistent with FR-013, which mandates ``_meta`` on tool
*results*, including ``isError`` results, not on pre-dispatch validation failures.
"""

from __future__ import annotations

import json
from typing import Any, Literal

import mcp.types as mcp_types
from fastmcp.tools.tool import ToolResult
from pydantic import BaseModel

from .._meta import append_meta, build_meta
from ..profiles import Profile


def _result(tool: str, received: dict[str, Any], note: str) -> ToolResult:
    """Build a ToolResult echoing ``received`` as JSON text + the trailing ``_meta``.

    ``append_meta`` yields portable dicts; fastmcp only keeps a list of *typed* content
    blocks as discrete blocks (a list of plain dicts collapses into one), so each block
    is materialised as a real :class:`mcp.types.TextContent`.
    """
    meta = build_meta(tool=tool, received=received, note=note)
    blocks = append_meta([{"type": "text", "text": json.dumps(received)}], meta)
    content = [mcp_types.TextContent(type="text", text=b["text"]) for b in blocks]
    return ToolResult(content=content)


# --------------------------------------------------------------------------- #
# Nested-object models for schema_nested (deeply nested: Person -> Address -> Geo).
# --------------------------------------------------------------------------- #
class Geo(BaseModel):
    lat: float
    lng: float


class Address(BaseModel):
    street: str
    city: str
    geo: Geo


class Person(BaseModel):
    name: str
    age: int
    address: Address


def register(app: Any, profile: Profile, ctx: Any) -> None:
    """Register the 6 schema tools (tools are enabled under every profile)."""

    @app.tool(
        name="schema_required_fields",
        description=(
            "Has two REQUIRED fields (name: string, count: integer). Omitting either "
            "is a validation error — validates that the client sends required fields."
        ),
    )
    def schema_required_fields(name: str, count: int) -> ToolResult:
        received = {"name": name, "count": count}
        return _result(
            "schema_required_fields", received, "Both required fields were supplied and validated."
        )

    @app.tool(
        name="schema_optional_fields",
        description=(
            "All fields OPTIONAL (nickname: string=\"anon\", verbose: boolean=false). "
            "Succeeds when they are omitted — validates client handling of optionality."
        ),
    )
    def schema_optional_fields(nickname: str = "anon", verbose: bool = False) -> ToolResult:
        received = {"nickname": nickname, "verbose": verbose}
        return _result(
            "schema_optional_fields", received, "Optional fields defaulted when omitted; call succeeded."
        )

    @app.tool(
        name="schema_enum",
        description=(
            "Field 'color' restricted to the enum {red, green, blue}. A value outside "
            "the enum is a validation error — validates client enum handling."
        ),
    )
    def schema_enum(color: Literal["red", "green", "blue"]) -> ToolResult:
        received = {"color": color}
        return _result("schema_enum", received, "Enum value within {red,green,blue}; validated.")

    @app.tool(
        name="schema_nested",
        description=(
            "Accepts a deeply nested object (person -> address -> geo) and returns it — "
            "validates client handling of nested object schemas."
        ),
    )
    def schema_nested(person: Person) -> ToolResult:
        received = {"person": person.model_dump()}
        return _result("schema_nested", received, "Deeply nested object accepted and echoed back.")

    @app.tool(
        name="schema_array_items",
        description=(
            "Accepts a typed array (items: array of integers) and returns it — validates "
            "client handling of array item types."
        ),
    )
    def schema_array_items(items: list[int]) -> ToolResult:
        received = {"items": items}
        return _result("schema_array_items", received, "Typed integer array accepted and echoed back.")

    @app.tool(
        name="schema_no_args",
        description=(
            "Declares no input parameters; succeeds when called with no arguments — "
            "validates that clients handle tools without a meaningful inputSchema."
        ),
    )
    def schema_no_args() -> ToolResult:
        return _result("schema_no_args", {}, "No arguments required; call succeeded.")


__all__ = ["register"]
