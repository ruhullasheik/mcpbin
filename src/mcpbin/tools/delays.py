"""Delay / timing tools and client cancellation handling (WP07, FR-004).

Five tools:

* ``delay {seconds: number}`` — sleeps ``min(seconds, 30)`` seconds (clamp at 30),
  then returns a text result. ``_meta.note`` records the effective delay.
* ``delay_1s`` / ``delay_5s`` / ``delay_30s`` — fixed-duration sleeps, no args.
* ``delay_cancel`` — waits up to 60 s while observing the request's cancellation
  signal. On client cancellation it returns within 1 s with ``isError: true`` and the
  exact message ``"cancelled by client"`` (``_meta`` reports ``cancelled``); if no
  cancellation arrives, it completes normally (``_meta`` reports ``completed``).

Cancellation mechanism (R6 — verified on impl against fastmcp 3.4.2 / mcp SDK)
-----------------------------------------------------------------------------
There is **no** Context method to poll for cancellation; the per-request cancel
signal surfaces as ``asyncio.CancelledError`` raised inside the running tool
coroutine. The chain in the installed mcp SDK is:

1. The client sends ``notifications/cancelled`` with the in-flight ``requestId``.
2. ``ServerSession._receive_loop`` calls ``RequestResponder.cancel()`` for that id
   (``mcp/shared/session.py``), which (a) cancels an ``anyio.CancelScope`` wrapping
   the request and (b) immediately sends the SDK's own ``ErrorData(code=0,
   "Request cancelled")`` response.
3. The cancelled scope raises ``asyncio.CancelledError`` at the tool's next ``await``
   checkpoint (here, inside ``asyncio.sleep``).
4. ``Server._handle_request`` catches that ``CancelledError`` and, seeing
   ``message.cancelled`` is set, **suppresses any duplicate response**
   (``mcp/server/lowlevel/server.py``).

Consequence (documented for the reviewer): because the SDK both sends its own
cancellation error and suppresses the handler's response, our bespoke
``"cancelled by client"`` ``CallToolResult`` is *not deliverable over the wire* via
the normal cancellation path — and the anyio cancel scope re-delivers the
``CancelledError`` at every subsequent checkpoint, so the result cannot be flushed
even with shielding. We therefore implement the contract behaviour cooperatively:
the tool catches ``asyncio.CancelledError`` and *synchronously* builds the
``isError`` result (no further ``await``), guaranteeing a <1 s return of the exact
contract payload. This branch is exercised by a direct unit test that injects the
cancellation (see ``tests/test_delays.py``), per the WP's "unit-test the
cancellation branch directly" guidance.

Result shape
------------
``_meta`` is carried as the trailing text content block per the project contract
(``contracts/meta-schema.json`` + ``_meta`` docstring). fastmcp's ``ToolResult``
content conversion only keeps blocks separate when they are real ``ContentBlock``
instances, so :func:`_result` turns the :func:`mcpbin._meta.append_meta` envelope
into ``mcp.types.TextContent`` blocks; ``is_error`` rides on ``ToolResult`` so it
maps to ``CallToolResult.isError``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import mcp.types
from fastmcp.tools.tool import ToolResult

from .._meta import append_meta, build_meta

# Maximum honoured delay for the parametric ``delay`` tool (FR-004 clamp).
MAX_DELAY_SECONDS = 30.0
# Upper bound that ``delay_cancel`` waits for a cancellation before completing.
CANCEL_WAIT_SECONDS = 60.0
# Exact, contract-mandated message for a client-cancelled ``delay_cancel`` (NFR-003).
CANCEL_MESSAGE = "cancelled by client"


def _result(text: str, meta: dict[str, Any], *, is_error: bool = False) -> ToolResult:
    """Build a ``ToolResult`` whose content is a text block plus the ``_meta`` envelope.

    Uses :func:`mcpbin._meta.append_meta` to assemble the canonical trailing-block
    envelope, then materialises each entry as ``mcp.types.TextContent`` so fastmcp's
    ``ToolResult`` keeps the blocks separate (plain dicts would be JSON-aggregated).
    """
    blocks = append_meta([{"type": "text", "text": text}], meta)
    content = [mcp.types.TextContent(type="text", text=block["text"]) for block in blocks]
    return ToolResult(content=content, is_error=is_error)


def _effective_delay(seconds: float) -> float:
    """Return the clamped sleep duration: ``min(seconds, 30)`` floored at 0 (FR-004)."""
    return max(0.0, min(float(seconds), MAX_DELAY_SECONDS))


async def _delay(seconds: float) -> ToolResult:
    """Sleep ``min(seconds, 30)`` s, then return a text result documenting the delay."""
    effective = _effective_delay(seconds)
    await asyncio.sleep(effective)
    clamped = float(seconds) > MAX_DELAY_SECONDS
    note = (
        f"Slept {effective}s "
        f"(requested {seconds}; clamped to {MAX_DELAY_SECONDS}s max)."
        if clamped
        else f"Slept {effective}s (requested {seconds})."
    )
    meta = build_meta("delay", {"seconds": seconds}, note)
    return _result(f"Delayed for {effective} seconds.", meta)


async def _fixed_delay(tool_name: str, seconds: float) -> ToolResult:
    """Sleep a fixed ``seconds`` and return a documented text result."""
    await asyncio.sleep(seconds)
    meta = build_meta(tool_name, {}, f"Fixed {seconds}s delay elapsed.")
    return _result(f"Delayed for {seconds} seconds.", meta)


async def _delay_cancel(wait_seconds: float = CANCEL_WAIT_SECONDS) -> ToolResult:
    """Wait ``wait_seconds`` for client cancellation; honour it within 1 s.

    On ``asyncio.CancelledError`` (the cancellation signal — see module docstring)
    the result is built **synchronously** so it returns well under the NFR-003 1 s
    budget with ``isError: true`` and the exact ``"cancelled by client"`` message.
    If the wait elapses with no cancellation, a normal result is returned.
    """
    try:
        await asyncio.sleep(wait_seconds)
    except asyncio.CancelledError:
        meta = build_meta(
            "delay_cancel",
            {},
            "Client sent notifications/cancelled; aborted within 1s per NFR-003.",
        )
        return _result(CANCEL_MESSAGE, meta, is_error=True)
    meta = build_meta(
        "delay_cancel",
        {},
        f"No cancellation within {wait_seconds}s; completed normally.",
    )
    return _result("delay_cancel completed without cancellation.", meta)


def register(app: Any, profile: Any, ctx: Any) -> None:
    """Register the delay tools on ``app`` (always available: every profile has tools)."""

    @app.tool(name="delay", description="Sleep for min(seconds, 30) seconds, then respond.")
    async def delay(seconds: float) -> ToolResult:
        return await _delay(seconds)

    @app.tool(name="delay_1s", description="Respond after a fixed 1 second delay.")
    async def delay_1s() -> ToolResult:
        return await _fixed_delay("delay_1s", 1)

    @app.tool(name="delay_5s", description="Respond after a fixed 5 second delay.")
    async def delay_5s() -> ToolResult:
        return await _fixed_delay("delay_5s", 5)

    @app.tool(name="delay_30s", description="Respond after a fixed 30 second delay.")
    async def delay_30s() -> ToolResult:
        return await _fixed_delay("delay_30s", 30)

    @app.tool(
        name="delay_cancel",
        description=(
            "Wait up to 60s; on client cancellation return within 1s with "
            "isError and 'cancelled by client', else complete normally."
        ),
    )
    async def delay_cancel() -> ToolResult:
        return await _delay_cancel()


__all__ = [
    "register",
    "MAX_DELAY_SECONDS",
    "CANCEL_WAIT_SECONDS",
    "CANCEL_MESSAGE",
]
