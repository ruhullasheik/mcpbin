"""Protocol inspection tool (FR-012): ``inspect_session``.

Returns metadata about the current session so a client developer can verify their
handshake and capability negotiation:

``{protocolVersion, clientInfo: {name, version}, negotiatedCapabilities, transport,
requestCount}``

``requestCount`` is a per-session counter that increments on each call within the same
session (it is the one intentionally dynamic field, excluded from determinism checks per
NFR-001).

Sources (fastmcp 3.4.2)
-----------------------
* ``transport`` and the shared :class:`~mcpbin.session.SessionStore` come from the
  mcpbin :class:`~mcpbin.server.ServerContext` passed to :func:`register` as ``ctx``.
* per-request identity comes from the injected fastmcp ``Context``: ``ctx.session_id``
  keys the store; ``ctx.session.client_params`` (the SDK ``InitializeRequestParams``)
  carries ``clientInfo``, ``protocolVersion`` and the client's declared ``capabilities``.
* ``negotiatedCapabilities`` is what mcpbin actually advertises for the active profile
  (derived from the closure ``profile``) — i.e. the server side of the negotiation.
"""

from __future__ import annotations

import json
from typing import Any

import mcp.types as mcp_types
from fastmcp import Context
from fastmcp.tools.tool import ToolResult

from .._meta import append_meta, build_meta
from ..profiles import Profile

# stdio has no per-connection id; use a stable key so the counter still increments
# across calls within the single stdio session.
_STDIO_SESSION_KEY = "stdio-singleton"


def _negotiated_capabilities(profile: Profile) -> dict[str, Any]:
    """The capabilities mcpbin advertises for ``profile`` (server side of negotiation)."""
    return {
        "tools": profile.tools,
        "resources": profile.resources,
        "prompts": profile.prompts,
        "sampling": profile.sampling,
        "pagination": profile.pagination,
        "listChanged": profile.list_changed,
    }


def register(app: Any, profile: Profile, ctx: Any) -> None:
    """Register ``inspect_session`` (tools are enabled under every profile)."""

    @app.tool(
        name="inspect_session",
        description=(
            "Return metadata about the current MCP session: protocolVersion, clientInfo, "
            "negotiatedCapabilities, transport, and a per-session requestCount that "
            "increments across calls. Lets a client verify its handshake succeeded."
        ),
    )
    async def inspect_session(context: Context) -> ToolResult:
        session_id = context.session_id or _STDIO_SESSION_KEY
        request_count = ctx.sessions.increment(session_id)

        protocol_version = "2025-03-26"
        client_info: dict[str, Any] = {"name": None, "version": None}
        try:
            client_params = getattr(context.session, "client_params", None)
            if client_params is not None:
                ci = getattr(client_params, "clientInfo", None)
                if ci is not None:
                    client_info = {
                        "name": getattr(ci, "name", None),
                        "version": getattr(ci, "version", None),
                    }
                protocol_version = getattr(client_params, "protocolVersion", protocol_version)
        except Exception:  # pragma: no cover - defensive; never fail inspection
            pass

        payload = {
            "protocolVersion": protocol_version,
            "clientInfo": client_info,
            "negotiatedCapabilities": _negotiated_capabilities(profile),
            "transport": ctx.transport,
            "requestCount": request_count,
        }
        note = (
            "Live session metadata; requestCount increments per call within this session "
            "(the only non-deterministic field, per NFR-001)."
        )
        meta = build_meta("inspect_session", {}, note)
        blocks = append_meta([{"type": "text", "text": json.dumps(payload)}], meta)
        content = [mcp_types.TextContent(type="text", text=b["text"]) for b in blocks]
        return ToolResult(content=content)


__all__ = ["register"]
