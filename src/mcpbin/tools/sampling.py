"""Sampling tools (FR-010): server->client ``sampling/createMessage`` round-trips.

* ``sampling_simple``       – minimal createMessage; returns the client's reply text.
* ``sampling_with_system``  – includes a ``systemPrompt``.
* ``sampling_max_tokens``   – includes ``maxTokens``.
* ``sampling_unsupported``  – when the client does not advertise sampling, returns a
  graceful ``isError`` result (no crash).

Graceful degradation: every sampling tool first checks the client's advertised
capability via ``session.check_client_capability``; if sampling is absent it returns an
``isError`` result explaining sampling is unavailable. This also covers the
``no-sampling``/``tools-only``/``minimal`` profiles and any client without a sampling
handler. Mechanism (fastmcp 3.4.2): the request ``Context.sample(messages, *,
system_prompt=..., max_tokens=...)`` performs the createMessage call to the client.
"""

from __future__ import annotations

from typing import Any

import mcp.types as mcp_types
from fastmcp import Context
from fastmcp.tools.tool import ToolResult

from .._meta import append_meta, build_meta
from ..profiles import Profile


def _result(tool: str, note: str, text: str, *, is_error: bool = False) -> ToolResult:
    meta = build_meta(tool, {}, note)
    blocks = append_meta([{"type": "text", "text": text}], meta)
    content = [mcp_types.TextContent(type="text", text=b["text"]) for b in blocks]
    return ToolResult(content=content, is_error=is_error)


def _sampling_supported(context: Context) -> bool:
    """True when the connected client advertises the sampling capability."""
    try:
        return bool(
            context.session.check_client_capability(
                mcp_types.ClientCapabilities(sampling=mcp_types.SamplingCapability())
            )
        )
    except Exception:  # pragma: no cover - defensive
        return False


async def _sample_text(context: Context, prompt: str, **kwargs: Any) -> str:
    result = await context.sample(prompt, **kwargs)
    return getattr(result, "text", None) or str(result)


_UNAVAILABLE = "Sampling is unavailable: the client did not advertise the sampling capability."


def register(app: Any, profile: Profile, ctx: Any) -> None:
    """Register the 4 sampling tools (tools are enabled under every profile)."""

    @app.tool(
        name="sampling_simple",
        description="Issue a minimal sampling/createMessage to the client and return its reply.",
    )
    async def sampling_simple(context: Context) -> ToolResult:
        if not _sampling_supported(context):
            return _result("sampling_simple", "Graceful degradation.", _UNAVAILABLE, is_error=True)
        text = await _sample_text(context, "Reply with a short friendly greeting.")
        return _result("sampling_simple", "Issued sampling/createMessage; returned the reply.", text)

    @app.tool(
        name="sampling_with_system",
        description="Issue sampling/createMessage including a systemPrompt.",
    )
    async def sampling_with_system(context: Context) -> ToolResult:
        if not _sampling_supported(context):
            return _result("sampling_with_system", "Graceful degradation.", _UNAVAILABLE, is_error=True)
        text = await _sample_text(
            context,
            "Introduce yourself in one sentence.",
            system_prompt="You are mcpbin, a diagnostic MCP test server.",
        )
        return _result("sampling_with_system", "Issued createMessage with a systemPrompt.", text)

    @app.tool(
        name="sampling_max_tokens",
        description="Issue sampling/createMessage with a specific maxTokens.",
    )
    async def sampling_max_tokens(context: Context) -> ToolResult:
        if not _sampling_supported(context):
            return _result("sampling_max_tokens", "Graceful degradation.", _UNAVAILABLE, is_error=True)
        text = await _sample_text(context, "Count to three.", max_tokens=42)
        return _result("sampling_max_tokens", "Issued createMessage with maxTokens=42.", text)

    @app.tool(
        name="sampling_unsupported",
        description=(
            "Demonstrates graceful handling when the client lacks sampling: returns an "
            "isError result rather than failing the call."
        ),
    )
    async def sampling_unsupported(context: Context) -> ToolResult:
        if not _sampling_supported(context):
            return _result(
                "sampling_unsupported",
                "Client lacks sampling capability; returned a graceful error per FR-010.",
                _UNAVAILABLE,
                is_error=True,
            )
        return _result(
            "sampling_unsupported",
            "Client advertises sampling; this tool documents the graceful-degradation path.",
            "Sampling is available; use sampling_simple/with_system/max_tokens to exercise it.",
        )


__all__ = ["register"]
