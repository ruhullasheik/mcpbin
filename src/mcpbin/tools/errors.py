"""Error tools (FR-003) — protocol vs tool-level error distinction.

This feature module registers the 7 ``error_*`` tools that let a client observe the
difference between a **JSON-RPC protocol error** (a coded error *response*, no tool
result) and a **tool-level error** (a normal ``CallToolResult`` with ``isError: true``),
plus the *simulated* ``error_parse`` and the non-standard ``error_unknown_code``.

How a protocol error actually reaches the client (verify-on-impl, fastmcp 3.4.2)
================================================================================
The foundation ``errors.mcp_error`` builds ``mcp.McpError(ErrorData(code, ...))``. The
naive expectation is that ``raise mcp_error(...)`` *inside a tool body* surfaces a coded
protocol error. **It does not** under fastmcp 3.4.2 + mcp SDK (spec 2025-03-26): the
high-level call path (``FastMCP._call_tool``) catches every tool exception and re-raises
it as ``fastmcp.exceptions.ToolError``; the SDK's low-level ``call_tool`` handler then
catches *that* and returns a ``CallToolResult(isError=True)`` whose text is ``str(exc)``.
The JSON-RPC ``code`` is therefore **lost** — a tool that merely ``raise``\\s ``McpError``
becomes indistinguishable from ``error_tool_level``. (Probed directly: the in-memory
client raises ``ToolError`` "Error calling tool ...", *not* ``McpError`` with a code.)

The only exception type the SDK ``call_tool`` handler re-raises is
``UrlElicitationRequiredError``; everything else is masked into an ``isError`` result.
By contrast, the SDK's outer ``_handle_request`` *does* preserve codes — when a
**request handler** raises ``McpError`` it sets ``response = err.error`` and replies with
a coded JSON-RPC error (``server.py`` line ~770). So to surface a genuine coded protocol
error we must raise ``McpError`` *before* the masking ``call_tool`` handler runs.

We do this by **wrapping** the registered ``CallToolRequest`` handler in
:func:`register`: for our protocol-error tool names we raise ``mcp_error(code, ...)``
directly (escaping to ``_handle_request`` -> coded response); every other tool name falls
through to the original handler untouched. The protocol-error tools are *also* registered
as ordinary catalog tools so they appear in ``tools/list`` (part of the 42-tool catalog);
their function bodies are a defensive fallback only — the interceptor handles the call.

Surfacing summary (what the client observes)
--------------------------------------------
* ``error_invalid_request`` / ``error_method_not_found`` / ``error_invalid_params`` /
  ``error_internal`` / ``error_unknown_code`` -> **protocol error**: the client raises
  ``mcp.McpError`` whose ``.error.code`` is the chosen code. No ``CallToolResult`` is
  produced, so the ``_meta`` envelope travels in ``error.data["_meta"]`` (FR-013 holds
  even on protocol errors).
* ``error_parse`` -> **normal result** (no raise): a text block holding a well-formed
  JSON-RPC error object with code ``-32700``, plus the trailing ``_meta`` block whose
  ``note`` explains the simulation (a real parse error precedes routing).
* ``error_tool_level`` -> **normal result** with ``isError: true`` and the trailing
  ``_meta`` block; carries *no* JSON-RPC code.

``error_unknown_code`` decision: surfaced as a **protocol error** (same mechanism as the
standard codes) carrying ``-32000`` — a code *outside* the standard ``-32700..-32603``
range — so a client can observe a non-standard code on the wire consistently with the
other coded errors.
"""

from __future__ import annotations

import json
from typing import Any

import mcp.types
from fastmcp.tools.tool import ToolResult

from .._meta import append_meta, build_meta
from ..errors import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    build_jsonrpc_error,
    mcp_error,
)

# Non-standard JSON-RPC code for ``error_unknown_code`` — deliberately *outside* the
# standard -32700..-32603 range (the JSON-RPC "implementation-defined server error"
# band -32000..-32099 starts here).
UNKNOWN_CODE = -32000

# Standard range bounds (inclusive) for the five reserved JSON-RPC codes mcpbin emits.
STANDARD_CODE_MIN = PARSE_ERROR  # -32700
STANDARD_CODE_MAX = INTERNAL_ERROR  # -32603

# Protocol-error tools: name -> (json-rpc code, message). These surface a real coded
# JSON-RPC error *response* (the client raises ``McpError`` with ``.error.code``), via
# the ``CallToolRequest`` interceptor installed in :func:`register`.
PROTOCOL_ERRORS: dict[str, tuple[int, str]] = {
    "error_invalid_request": (INVALID_REQUEST, "Invalid Request"),
    "error_method_not_found": (METHOD_NOT_FOUND, "Method not found"),
    "error_invalid_params": (INVALID_PARAMS, "Invalid params"),
    "error_internal": (INTERNAL_ERROR, "Internal error"),
    "error_unknown_code": (UNKNOWN_CODE, "Non-standard server error"),
}


def _content_blocks(content: list[dict[str, Any]], meta: dict[str, Any]) -> list[Any]:
    """Build the result content as ``TextContent`` blocks with the trailing ``_meta``.

    ``ToolResult(content=...)`` treats a list of *plain dicts* as opaque structured data
    (it JSON-serialises the whole list into one text block); it only emits discrete
    content blocks for ``mcp.types`` content objects. So we run the canonical
    :func:`append_meta` (which appends the ``{"_meta": ...}`` text block per the contract)
    and then materialise every ``{"type": "text", "text": ...}`` dict as a real
    ``TextContent``.
    """
    blocks = append_meta(content, meta)
    return [mcp.types.TextContent(type="text", text=block["text"]) for block in blocks]


def _protocol_note(name: str, code: int) -> str:
    """One-sentence ``_meta.note`` for a protocol-error tool."""
    if name == "error_unknown_code":
        return (
            f"Protocol-level JSON-RPC error with the non-standard code {code} (outside "
            f"the reserved -32700..-32603 range); the client receives a coded error "
            f"response (not a tool result), so this _meta rides in error.data."
        )
    return (
        f"Protocol-level JSON-RPC error {code}; the client receives a coded error "
        f"response (McpError.error.code), not a CallToolResult, so this _meta rides "
        f"in error.data (contrast error_tool_level's isError result)."
    )


def _make_protocol_tool(name: str, code: int, message: str) -> Any:
    """Build a catalog stub for a protocol-error tool.

    The body is a defensive fallback: the ``CallToolRequest`` interceptor normally
    raises the coded error before any tool body runs. If the interceptor were ever
    bypassed, raising here keeps behaviour coherent (albeit masked to an isError result
    by fastmcp, per the module docstring).
    """

    def tool_fn() -> ToolResult:
        meta = build_meta(name, {}, _protocol_note(name, code))
        raise mcp_error(code, message, data={"_meta": meta})

    tool_fn.__name__ = name
    tool_fn.__doc__ = f"Raise a JSON-RPC protocol error with code {code}."
    return tool_fn


def _install_protocol_interceptor(app: Any) -> None:
    """Wrap the ``CallToolRequest`` handler to surface coded protocol errors.

    For a name in :data:`PROTOCOL_ERRORS` we raise ``mcp_error(code, ...)`` *before*
    fastmcp's masking ``call_tool`` handler runs, so the SDK's ``_handle_request``
    converts it into a coded JSON-RPC error response. Any other tool name delegates to
    the original handler unchanged. The raw received arguments are captured here
    (pre-validation) for the ``_meta`` envelope carried in ``error.data``.
    """
    import mcp.types as mcp_types

    handlers = app._mcp_server.request_handlers
    inner = handlers.get(mcp_types.CallToolRequest)
    if inner is None:  # pragma: no cover - fastmcp always registers call_tool
        return

    async def handler(req: Any) -> Any:
        name = getattr(req.params, "name", None)
        spec = PROTOCOL_ERRORS.get(name) if name is not None else None
        if spec is not None:
            code, message = spec
            received = dict(getattr(req.params, "arguments", None) or {})
            meta = build_meta(name, received, _protocol_note(name, code))
            raise mcp_error(code, message, data={"_meta": meta})
        return await inner(req)

    handlers[mcp_types.CallToolRequest] = handler


def register(app: Any, profile: Any, ctx: Any) -> None:
    """Register the 7 error tools on ``app`` (FR-003).

    ``tools`` is enabled under every profile, so all error tools register
    unconditionally. ``profile``/``ctx`` are accepted per the registry contract but not
    needed here.
    """
    # --- Simulated parse error: a NORMAL result whose text is a -32700 JSON-RPC error.
    @app.tool(
        name="error_parse",
        description=(
            "Simulated JSON-RPC parse error (-32700) returned as text content "
            "(a real parse error happens before routing, so a tool cannot raise one)."
        ),
    )
    def error_parse() -> ToolResult:
        error_obj = build_jsonrpc_error(PARSE_ERROR, "Parse error")
        envelope = {"jsonrpc": "2.0", "id": None, "error": error_obj}
        note = (
            "Simulated parse error: a real -32700 occurs before JSON-RPC routing and "
            "cannot originate from a tool, so this returns a well-formed JSON-RPC error "
            "object as text content rather than a protocol error."
        )
        content = [{"type": "text", "text": json.dumps(envelope)}]
        meta = build_meta("error_parse", {}, note)
        return ToolResult(content=_content_blocks(content, meta))

    # --- Tool-level error: a NORMAL result with isError=true, NOT a protocol error.
    @app.tool(
        name="error_tool_level",
        description=(
            "Tool-level failure: a normal CallToolResult with isError=true and no "
            "JSON-RPC code (contrast the coded protocol-error tools)."
        ),
    )
    def error_tool_level() -> ToolResult:
        note = (
            "Tool-level error: isError=true on a normal CallToolResult per the MCP "
            "tools spec; this is NOT a JSON-RPC protocol error and carries no "
            "error.code, unlike error_invalid_request and friends."
        )
        content = [
            {"type": "text", "text": "This tool failed at the tool level (isError=true)."}
        ]
        meta = build_meta("error_tool_level", {}, note)
        return ToolResult(content=_content_blocks(content, meta), is_error=True)

    # --- Protocol-error tools: registered for the catalog; surfaced by the interceptor.
    for name, (code, message) in PROTOCOL_ERRORS.items():
        app.tool(
            name=name,
            description=f"Raise a JSON-RPC protocol error with code {code}.",
        )(_make_protocol_tool(name, code, message))

    # Wrap the call handler so the protocol-error names yield coded responses.
    _install_protocol_interceptor(app)


__all__ = [
    "register",
    "PROTOCOL_ERRORS",
    "UNKNOWN_CODE",
    "STANDARD_CODE_MIN",
    "STANDARD_CODE_MAX",
]
