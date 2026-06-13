"""JSON-RPC error helpers (FR-003, research R4).

Verify-on-impl findings (fastmcp 3.4.2 / mcp spec 2025-03-26)
------------------------------------------------------------
The correct way to raise a **protocol-level** JSON-RPC error carrying a chosen
``code`` from inside a tool is the low-level MCP exception:

    from mcp import McpError            # == mcp.shared.exceptions.McpError
    from mcp.types import ErrorData     # fields: code, message, data

    raise McpError(ErrorData(code=-32602, message="...", data=None))

``McpError.__init__(self, error: ErrorData)`` takes a single ``ErrorData`` whose
``code`` becomes the JSON-RPC ``error.code`` on the wire. ``mcp.types`` already
defines the standard code constants (``PARSE_ERROR``, ``INVALID_REQUEST``,
``METHOD_NOT_FOUND``, ``INVALID_PARAMS``, ``INTERNAL_ERROR``) with the same values
re-declared below for locality.

By contrast ``fastmcp.exceptions.ToolError`` produces a **tool-level** error
(``isError: true`` in the result) and carries *no* JSON-RPC code — that path belongs
to ``error_tool_level`` / ``return_isError`` in WP06, not to the coded protocol errors
here. So: coded protocol errors -> ``McpError``; graceful tool-level errors ->
``ToolError`` (used elsewhere).
"""

from __future__ import annotations

from typing import Any

from mcp import McpError
from mcp.types import ErrorData

# Standard JSON-RPC 2.0 error codes (mirrors mcp.types constants for locality).
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Shared message for invalid/expired pagination cursors (used by pagination.py).
INVALID_CURSOR_MESSAGE = "invalid or expired cursor"


def mcp_error(code: int, message: str, data: Any | None = None) -> McpError:
    """Build a coded protocol-level :class:`McpError`.

    Raise the return value (``raise mcp_error(...)``) to surface a JSON-RPC error
    whose ``error.code`` is ``code``. Returning rather than raising keeps the helper
    composable (callers may ``raise mcp_error(...)`` at the exact site, which also
    gives a cleaner traceback).
    """
    return McpError(ErrorData(code=code, message=message, data=data))


def build_jsonrpc_error(code: int, message: str, data: Any | None = None) -> dict[str, Any]:
    """Build a *simulated* JSON-RPC error object as a plain dict.

    Used by ``error_parse`` (WP06): a real parse error happens before routing, so
    that tool returns a well-formed ``-32700`` error *as text content* rather than an
    actual protocol error. This produces the ``{"code", "message", "data"?}`` shape
    that lives under a JSON-RPC ``"error"`` member; ``data`` is omitted when ``None``.
    """
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return error


__all__ = [
    "PARSE_ERROR",
    "INVALID_REQUEST",
    "METHOD_NOT_FOUND",
    "INVALID_PARAMS",
    "INTERNAL_ERROR",
    "INVALID_CURSOR_MESSAGE",
    "mcp_error",
    "build_jsonrpc_error",
]
