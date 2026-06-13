"""Per-connection session state (FR-012, research R9).

``inspect_session`` (WP11) surfaces ``{protocolVersion, clientInfo,
negotiatedCapabilities, transport, requestCount}``; ``requestCount`` increments per
request within a session and is excluded from reproducibility checks (NFR-001).

Verify-on-impl findings (fastmcp 3.4.2)
---------------------------------------
``fastmcp.Context`` exposes a per-connection identity directly:

    ctx.session_id   # stable per connection -> use as the SessionStore key
    ctx.client_id    # client-supplied id
    ctx.transport    # "stdio" | "sse" | "http"-ish transport name

So the store is keyed by ``ctx.session_id``. To stay transport-agnostic and avoid a
hard fastmcp dependency here, :class:`SessionStore` accepts an **opaque string key**;
WP03 wires ``ctx.session_id`` (and sets ``transport``) and WP11 reads the state.

TODO(WP03/WP11): pass ``ctx.session_id`` as the key and populate ``transport`` /
``client_info`` / ``negotiated_capabilities`` / ``protocol_version`` from the
``initialize`` handshake. ``ctx.session_id`` may be ``None`` for some stdio cases —
WP03 should fall back to a per-process constant key when absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    """In-memory state for a single MCP connection.

    Field names mirror the runtime shape; ``inspect_session`` maps them to the
    wire's camelCase (``protocolVersion`` etc.) in WP11.
    """

    protocol_version: str = "2025-03-26"
    client_info: dict[str, Any] | None = None
    negotiated_capabilities: dict[str, Any] = field(default_factory=dict)
    transport: str | None = None
    request_count: int = 0


class SessionStore:
    """Keyed store of :class:`SessionState`, one entry per session id.

    The key is an opaque string (the FastMCP ``session_id`` in production). Kept
    transport-agnostic: nothing here imports fastmcp.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        """Return the state for ``session_id``, creating a fresh one if needed."""
        state = self._sessions.get(session_id)
        if state is None:
            state = SessionState()
            self._sessions[session_id] = state
        return state

    def increment(self, session_id: str) -> int:
        """Increment and return ``request_count`` for ``session_id``.

        Creates the session if it does not yet exist (the first request implicitly
        opens the session).
        """
        state = self.get_or_create(session_id)
        state.request_count += 1
        return state.request_count

    def __contains__(self, session_id: object) -> bool:
        return session_id in self._sessions

    def __len__(self) -> int:
        return len(self._sessions)


__all__ = ["SessionState", "SessionStore"]
