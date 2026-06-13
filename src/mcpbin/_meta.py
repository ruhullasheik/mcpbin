"""The ``_meta`` documentation envelope (FR-013, research R5).

Every mcpbin tool result carries a fixed ``_meta`` object documenting the call.
Its schema is frozen in ``contracts/meta-schema.json`` and is identical across
all tools: ``{"tool", "received", "note"}``.

Representation decision (verify-on-impl, R5)
--------------------------------------------
The installed stack is **fastmcp 3.4.2** / MCP spec **2025-03-26**. Inspection of
``mcp.types`` shows the result types *do* expose a native result-level ``_meta``
field:

    CallToolResult.model_fields["meta"].alias == "_meta"   # also on TextContent

So a native result-level ``_meta`` channel exists. However, the mcpbin **contract**
(``contracts/meta-schema.json`` + ``data-model.md``) and the PRD explicitly define the
envelope as *the final text content block of every tool result* — a text block whose
text is ``json.dumps({"_meta": {...}})``. We therefore make the **trailing text block**
the authoritative representation here so the documented, client-observable shape is
uniform across every tool (including ``isError`` and empty results).

WP05 note (``return_empty``): because a native result-level ``_meta`` field is
available, WP05 *may* additionally surface the envelope via the result-level ``_meta``
field if it wants ``return_empty`` to carry truly zero *substantive* content blocks
while still documenting the response. The trailing-text-block helper below remains the
canonical, tested contract regardless.
"""

from __future__ import annotations

import json
from typing import Any

# fastmcp/MCP normalizes a plain ``{"type": "text", "text": ...}`` dict into a
# ``TextContent`` block, so we keep the helper dependency-free (no fastmcp import)
# and emit the portable dict form. The content list is a list of such blocks.
META_KEY = "_meta"


def build_meta(tool: str, received: dict[str, Any], note: str) -> dict[str, Any]:
    """Build the fixed ``_meta`` envelope.

    Returns exactly ``{"tool", "received", "note"}`` matching
    ``contracts/meta-schema.json``.

    Parameters
    ----------
    tool:
        Name of the tool that was called (required, non-empty).
    received:
        The *exact raw parsed arguments* the server received — even when the tool
        ignores them (e.g. error tools). ``{}`` for no-arg tools.
    note:
        One human-readable sentence explaining why the response looks the way it
        does; references an MCP spec section where relevant.
    """
    return {
        "tool": tool,
        "received": received,
        "note": note,
    }


def append_meta(content: list[Any], meta: dict[str, Any]) -> list[Any]:
    """Append the ``_meta`` envelope as the **final text content block**.

    The trailing block's text is ``json.dumps({"_meta": {...}})`` per the PRD's
    ``_meta`` rules. A new list is returned; the input is not mutated. Present even
    when ``content`` is empty (``return_empty``) or the result is an error.
    """
    block = {
        "type": "text",
        "text": json.dumps({META_KEY: meta}),
    }
    return [*content, block]


__all__ = ["META_KEY", "build_meta", "append_meta"]
