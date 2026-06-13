"""Shared pytest fixtures for mcpbin (WP03, T020).

Provides in-memory ``fastmcp.Client`` fixtures bound to ``build_app(profile,
"stdio")`` for every capability profile, plus a parametrizable factory. Feature WP
tests **consume** these fixtures and must not modify this file.

In-memory transport notes (fastmcp 3.4.2)
-----------------------------------------
``fastmcp.Client(app)`` selects the in-memory ``FastMCPTransport`` (no subprocess);
it runs ``app._mcp_server`` over an in-memory stream pair, honouring the
``notification_options`` / gated handlers configured by :func:`mcpbin.server.build_app`.
The client is an async context manager: ``async with client_full as c: ...``. After
entry, ``c.initialize_result.capabilities`` exposes advertised capabilities and
``c.list_tools_mcp(cursor=...)`` (and the resources/prompts equivalents) return the
raw ``mcp.types.List*Result`` objects (with ``.nextCursor``). An omitted/gated method
raises ``mcp.McpError`` whose ``error.code`` is the JSON-RPC code.

The factory and per-profile fixtures yield **unconnected** ``Client`` objects so each
test controls the ``async with`` lifecycle (and, importantly, may register a few
dummy tools/resources before connecting to exercise pagination).
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastmcp import Client

from mcpbin import profiles
from mcpbin.server import build_app


def _make_client(profile_name: str) -> Client:
    """Build a fresh in-memory client for ``profile_name`` (stdio transport)."""
    app = build_app(profile_name, "stdio")
    return Client(app)


@pytest.fixture
def client_factory() -> Callable[[str], Client]:
    """Return a factory ``make(profile_name) -> Client`` for ad-hoc profiles.

    Example::

        async def test_x(client_factory):
            async with client_factory("minimal") as c:
                ...
    """
    return _make_client


@pytest.fixture
def client_full() -> Client:
    """In-memory client for the ``full`` profile."""
    return _make_client(profiles.FULL)


@pytest.fixture
def client_tools_only() -> Client:
    """In-memory client for the ``tools-only`` profile."""
    return _make_client(profiles.TOOLS_ONLY)


@pytest.fixture
def client_no_sampling() -> Client:
    """In-memory client for the ``no-sampling`` profile."""
    return _make_client(profiles.NO_SAMPLING)


@pytest.fixture
def client_minimal() -> Client:
    """In-memory client for the ``minimal`` profile."""
    return _make_client(profiles.MINIMAL)
