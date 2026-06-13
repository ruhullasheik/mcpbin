"""Response-type tools (FR-002): one tool per MCP content shape.

Six no-argument tools that exercise every MCP content block kind plus the two
result-level flags a client cares about (``isError`` and ``_meta``):

* ``return_text``     – a single ``text`` block.
* ``return_image``    – a single ``image`` block (base64 of the committed 1x1
  ``assets/test.png``, ``mimeType="image/png"``).
* ``return_resource`` – a single ``resource`` block wrapping a valid embedded
  resource object.
* ``return_multiple`` – ≥3 mixed blocks (text + image + resource).
* ``return_empty``    – no substantive content blocks (see the reconciliation note).
* ``return_isError``  – ``isError: true`` + a text block.

Content-block representation (verify-on-impl, fastmcp 3.4.2)
-----------------------------------------------------------
We return :class:`fastmcp.tools.tool.ToolResult` wrapping **typed**
``mcp.types`` content blocks. This is deliberate: fastmcp's ``_convert_to_content``
only preserves a list verbatim when every item is a real ``ContentBlock`` — a list
of plain ``{"type": "text", ...}`` dicts is *aggregated into a single JSON text
block* instead. So the portable-dict form emitted by :func:`mcpbin._meta.append_meta`
is converted to ``TextContent`` here before it reaches ``ToolResult``.

``_meta`` representation and the ``return_empty`` reconciliation (R5 / WP02 / T027)
----------------------------------------------------------------------------------
``_meta.py`` documents two available channels and makes the **trailing text block**
(``append_meta``) the canonical envelope. We follow that for five of the six tools:
the ``_meta`` envelope is the final ``text`` content block, with text
``json.dumps({"_meta": {...}})``.

``return_empty`` is the one tool where the contract (``contracts/tools.md`` ->
"content: []") collides with the mandatory-``_meta`` rule. Per T027: because the
installed MCP result type *does* expose a native result-level ``_meta`` field
(``CallToolResult.model_fields["meta"].alias == "_meta"``, surfaced by
``ToolResult(meta=...)``), ``return_empty`` returns **truly zero content blocks**
and carries its envelope on the native result-level ``_meta`` field. To keep the two
channels byte-identical, the native field holds ``{"_meta": {...}}`` — the same JSON
object the trailing text block serializes for every other tool. This is the only
tool that uses the native channel; all others use the trailing-text-block envelope.
"""

from __future__ import annotations

import base64
import json
from functools import lru_cache
from typing import Any

import mcp.types as mcp_types
from fastmcp.tools import Tool
from fastmcp.tools.tool import ToolResult

from .._meta import META_KEY, append_meta, build_meta

# A stable URI for the embedded resource returned by return_resource / return_multiple.
_RESOURCE_URI = "mcpbin://response_types/sample.txt"
_RESOURCE_TEXT = "embedded resource payload from mcpbin response_types"


@lru_cache(maxsize=1)
def _png_bytes() -> bytes:
    """Return the committed ``assets/test.png`` bytes (cached after first read).

    Loaded at runtime and base64-encoded by the caller — no image library is added
    (C-003); we ship the raw PNG bytes and read them deterministically (NFR-001).
    Resolution prefers ``importlib.resources`` (works for installed wheels) and falls
    back to a path relative to this module (editable / source checkouts).
    """
    try:
        from importlib.resources import files

        resource = files("mcpbin").joinpath("assets", "test.png")
        return resource.read_bytes()
    except (FileNotFoundError, ModuleNotFoundError, ImportError):
        from pathlib import Path

        return (Path(__file__).resolve().parent.parent / "assets" / "test.png").read_bytes()


def _meta_text_block(tool: str, note: str) -> mcp_types.TextContent:
    """Build the trailing ``_meta`` envelope as a typed ``TextContent`` block.

    Uses :func:`mcpbin._meta.append_meta` (the canonical helper) to produce the
    portable ``{"type": "text", "text": json.dumps({"_meta": ...})}`` block, then
    converts it to a typed ``TextContent`` so fastmcp preserves it verbatim.
    """
    meta = build_meta(tool=tool, received={}, note=note)
    block = append_meta([], meta)[-1]  # canonical dict envelope
    return mcp_types.TextContent(**block)


def _meta_envelope(tool: str, note: str) -> dict[str, Any]:
    """Build the native result-level ``_meta`` payload for ``return_empty``.

    Mirrors the trailing-text-block JSON exactly: ``{"_meta": {tool, received, note}}``
    so both representations are byte-identical.
    """
    return {META_KEY: build_meta(tool=tool, received={}, note=note)}


def _image_block() -> mcp_types.ImageContent:
    """Build an ``image`` content block from the committed PNG (base64, image/png)."""
    data = base64.b64encode(_png_bytes()).decode("ascii")
    return mcp_types.ImageContent(type="image", data=data, mimeType="image/png")


def _resource_block() -> mcp_types.EmbeddedResource:
    """Build a ``resource`` content block wrapping a valid embedded text resource."""
    return mcp_types.EmbeddedResource(
        type="resource",
        resource=mcp_types.TextResourceContents(
            uri=_RESOURCE_URI,
            mimeType="text/plain",
            text=_RESOURCE_TEXT,
        ),
    )


# --------------------------------------------------------------------------- #
# Tool implementations (each returns a ToolResult).
# --------------------------------------------------------------------------- #
def return_text() -> ToolResult:
    """One ``text`` block + trailing ``_meta`` text block."""
    note = "Single text content block per MCP content type 'text'."
    return ToolResult(
        content=[
            mcp_types.TextContent(type="text", text="Hello from mcpbin return_text."),
            _meta_text_block("return_text", note),
        ]
    )


def return_image() -> ToolResult:
    """One ``image`` block (base64 of assets/test.png) + trailing ``_meta`` block."""
    note = "Single image content block; data is base64 of committed assets/test.png."
    return ToolResult(content=[_image_block(), _meta_text_block("return_image", note)])


def return_resource() -> ToolResult:
    """One ``resource`` block with a valid embedded resource + trailing ``_meta``."""
    note = "Single resource content block wrapping an embedded text resource."
    return ToolResult(
        content=[_resource_block(), _meta_text_block("return_resource", note)]
    )


def return_multiple() -> ToolResult:
    """Three mixed blocks (text + image + resource) + trailing ``_meta`` block."""
    note = "Multiple mixed content blocks: text, image, and embedded resource."
    return ToolResult(
        content=[
            mcp_types.TextContent(type="text", text="Mixed content blocks follow:"),
            _image_block(),
            _resource_block(),
            _meta_text_block("return_multiple", note),
        ]
    )


def return_empty() -> ToolResult:
    """No substantive content blocks; ``_meta`` carried on the native result-level field.

    Reconciliation (T027): the installed MCP result type exposes a native
    result-level ``_meta`` field, so this tool returns ``content: []`` (matching the
    contract) and documents the response via that native channel instead of a text
    block. The native field holds the same ``{"_meta": {...}}`` object every other
    tool serializes into its trailing text block.
    """
    note = (
        "Empty content (content: []); the _meta envelope is carried on the native "
        "result-level _meta field because the MCP result type supports it (R5/T027)."
    )
    return ToolResult(content=[], meta=_meta_envelope("return_empty", note))


def return_isError() -> ToolResult:
    """``isError: true`` + a text block + trailing ``_meta`` block (tool-level error)."""
    note = "Tool-level error: isError=true on a normal result (not a protocol error)."
    return ToolResult(
        content=[
            mcp_types.TextContent(
                type="text", text="This is a tool-level error result."
            ),
            _meta_text_block("return_isError", note),
        ],
        is_error=True,
    )


_TOOLS = (
    return_text,
    return_image,
    return_resource,
    return_multiple,
    return_empty,
    return_isError,
)


def register(app: Any, profile: Any, ctx: Any) -> None:
    """Register the six response-type tools on ``app`` (always available: tools=True).

    Honors the registry contract ``register(app, profile, ctx)``. These tools take no
    arguments and exist under every profile, so there is nothing to gate here.
    """
    for fn in _TOOLS:
        app.add_tool(Tool.from_function(fn, name=fn.__name__))


__all__ = ["register"]
