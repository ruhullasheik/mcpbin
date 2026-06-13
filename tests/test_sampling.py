"""Sampling tool tests (WP10, T043) — FR-010.

A sampling-capable client (with a ``sampling_handler``) exercises the round-trip and
captures the outgoing request params; a client WITHOUT sampling verifies graceful
degradation.
"""

from __future__ import annotations

import json

from fastmcp import Client

from mcpbin.server import build_app

CANNED_REPLY = "hello from the canned sampling handler"


class _Recorder:
    """Sampling handler that records the request params and returns a canned reply."""

    def __init__(self) -> None:
        self.calls: list = []

    async def __call__(self, messages, params, context) -> str:
        self.calls.append(params)
        return CANNED_REPLY


def _meta(result) -> dict:
    return json.loads(result.content[-1].text)["_meta"]


def _text(result) -> str:
    return result.content[0].text


def _param(params, *names):
    for n in names:
        val = getattr(params, n, None)
        if val is not None:
            return val
    return None


async def test_sampling_simple_round_trip():
    recorder = _Recorder()
    app = build_app("full", "stdio")
    async with Client(app, sampling_handler=recorder) as c:
        result = await c.call_tool("sampling_simple", {})
    assert _text(result) == CANNED_REPLY
    assert len(recorder.calls) == 1
    assert _meta(result)["tool"] == "sampling_simple"


async def test_sampling_with_system_includes_system_prompt():
    recorder = _Recorder()
    app = build_app("full", "stdio")
    async with Client(app, sampling_handler=recorder) as c:
        await c.call_tool("sampling_with_system", {})
    params = recorder.calls[0]
    system = _param(params, "systemPrompt", "system_prompt")
    assert system and "mcpbin" in system


async def test_sampling_max_tokens_includes_max_tokens():
    recorder = _Recorder()
    app = build_app("full", "stdio")
    async with Client(app, sampling_handler=recorder) as c:
        await c.call_tool("sampling_max_tokens", {})
    params = recorder.calls[0]
    assert _param(params, "maxTokens", "max_tokens") == 42


async def test_sampling_unsupported_degrades_gracefully_without_handler():
    # No sampling_handler -> client does not advertise sampling.
    app = build_app("full", "stdio")
    async with Client(app) as c:
        # raise_on_error=False so we can inspect the graceful isError result rather
        # than have the client raise ToolError for it.
        result = await c.call_tool("sampling_unsupported", {}, raise_on_error=False)
    assert result.is_error is True
    assert "unavailable" in _text(result).lower()
    assert _meta(result)["tool"] == "sampling_unsupported"
