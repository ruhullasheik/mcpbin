"""Notification tools (FR-009): server-initiated notifications.

Six tools that push server->client notifications so a client can validate it handles
more than request/response:

* ``notify_resource_updated``       -> ``notifications/resources/updated``
* ``notify_resource_list_changed``  -> ``notifications/resources/list_changed``
* ``notify_prompt_list_changed``    -> ``notifications/prompts/list_changed``
* ``notify_tool_list_changed``      -> ``notifications/tools/list_changed``
* ``notify_progress``               -> >=3 ``notifications/progress`` then a result
* ``notify_log``                    -> ``notifications/message`` at debug/info/warning/error

Mechanism (fastmcp 3.4.2)
-------------------------
The request ``Context`` exposes ``report_progress`` and ``log``; the underlying
``ServerSession`` (``context.session``) exposes ``send_resource_updated`` and the
``send_{tool,resource,prompt}_list_changed`` helpers. Progress notifications are only
emitted when the caller supplied a progress token (fastmcp attaches one automatically
when the client is constructed with a ``progress_handler``).
"""

from __future__ import annotations

from typing import Any

import mcp.types as mcp_types
from fastmcp import Context
from fastmcp.tools.tool import ToolResult
from pydantic import AnyUrl

from .._meta import append_meta, build_meta
from ..profiles import Profile

_UPDATED_URI = "mcpbin://text/plain"
_LOG_LEVELS = ("debug", "info", "warning", "error")


def _result(tool: str, note: str) -> ToolResult:
    meta = build_meta(tool, {}, note)
    blocks = append_meta([{"type": "text", "text": f"{tool}: notification(s) sent."}], meta)
    return ToolResult(content=[mcp_types.TextContent(type="text", text=b["text"]) for b in blocks])


def _session(context: Context) -> Any:
    """The underlying ServerSession (carries the send_* notification helpers)."""
    session = getattr(context, "session", None)
    if session is not None:
        return session
    return context.request_context.session


def register(app: Any, profile: Profile, ctx: Any) -> None:
    """Register the 6 notification tools (tools are enabled under every profile)."""

    @app.tool(
        name="notify_resource_updated",
        description="Send a notifications/resources/updated for mcpbin://text/plain.",
    )
    async def notify_resource_updated(context: Context) -> ToolResult:
        await _session(context).send_resource_updated(AnyUrl(_UPDATED_URI))
        return _result("notify_resource_updated", "Sent notifications/resources/updated.")

    @app.tool(
        name="notify_resource_list_changed",
        description="Send a notifications/resources/list_changed.",
    )
    async def notify_resource_list_changed(context: Context) -> ToolResult:
        await _session(context).send_resource_list_changed()
        return _result("notify_resource_list_changed", "Sent notifications/resources/list_changed.")

    @app.tool(
        name="notify_prompt_list_changed",
        description="Send a notifications/prompts/list_changed.",
    )
    async def notify_prompt_list_changed(context: Context) -> ToolResult:
        await _session(context).send_prompt_list_changed()
        return _result("notify_prompt_list_changed", "Sent notifications/prompts/list_changed.")

    @app.tool(
        name="notify_tool_list_changed",
        description="Send a notifications/tools/list_changed.",
    )
    async def notify_tool_list_changed(context: Context) -> ToolResult:
        await _session(context).send_tool_list_changed()
        return _result("notify_tool_list_changed", "Sent notifications/tools/list_changed.")

    @app.tool(
        name="notify_progress",
        description="Send a sequence of at least 3 notifications/progress, then complete.",
    )
    async def notify_progress(context: Context) -> ToolResult:
        for i in range(1, 4):
            await context.report_progress(progress=float(i), total=3.0, message=f"step {i}/3")
        return _result("notify_progress", "Sent 3 notifications/progress, then completed.")

    @app.tool(
        name="notify_log",
        description="Send a notifications/message log at each level: debug, info, warning, error.",
    )
    async def notify_log(context: Context) -> ToolResult:
        for level in _LOG_LEVELS:
            await context.log(message=f"mcpbin {level} log message", level=level)
        return _result("notify_log", "Sent log messages at debug, info, warning and error levels.")


__all__ = ["register"]
