"""Tests for the server, CLI, profile gating and pagination wiring (WP03, T021).

Covers FR-008 (pagination), FR-011 (capability gating -> -32601), FR-014/FR-016
(transports/CLI/logging) at the mechanism level. The catalog is empty until feature
WPs land, so pagination is exercised by registering a handful of dummy tools on the
app before connecting the in-memory client (full multipage validation is WP15's job).
"""

from __future__ import annotations

import pytest
from fastmcp import Client
from fastmcp.tools import Tool
from mcp import McpError

from mcpbin import profiles
from mcpbin.errors import INVALID_CURSOR_MESSAGE, INVALID_PARAMS, METHOD_NOT_FOUND
from mcpbin.pagination import PAGE_SIZE
from mcpbin import server as server_mod
from mcpbin.server import TRANSPORTS, _build_http_app, _build_parser, build_app, main


# --------------------------------------------------------------------------- #
# CLI / arg parsing (T015).
# --------------------------------------------------------------------------- #
def test_parser_defaults_are_stdio_and_full():
    args = _build_parser().parse_args([])
    assert args.transport == "stdio"
    assert args.profile == profiles.FULL


@pytest.mark.parametrize("transport", sorted(TRANSPORTS))
def test_parser_accepts_each_transport(transport):
    args = _build_parser().parse_args(["--transport", transport])
    assert args.transport == transport


@pytest.mark.parametrize(
    "profile",
    [profiles.FULL, profiles.TOOLS_ONLY, profiles.NO_SAMPLING, profiles.MINIMAL],
)
def test_parser_accepts_each_profile(profile):
    args = _build_parser().parse_args(["--profile", profile])
    assert args.profile == profile


def test_parser_rejects_unknown_transport():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["--transport", "carrier-pigeon"])


def test_help_exits_zero_and_lists_flags(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--transport" in out
    assert "--profile" in out


# --------------------------------------------------------------------------- #
# build_app smoke (T014).
# --------------------------------------------------------------------------- #
def test_build_app_returns_app_for_each_profile():
    for profile in (
        profiles.FULL,
        profiles.TOOLS_ONLY,
        profiles.NO_SAMPLING,
        profiles.MINIMAL,
    ):
        app = build_app(profile, "stdio")
        assert app is not None


def test_build_app_rejects_unknown_profile():
    with pytest.raises(ValueError):
        build_app("nonexistent", "stdio")


# --------------------------------------------------------------------------- #
# Advertised capabilities (T014, FR-011).
# --------------------------------------------------------------------------- #
async def test_full_advertises_tools_resources_prompts_sampling(client_full: Client):
    async with client_full as c:
        caps = c.initialize_result.capabilities
        assert caps.tools is not None
        assert caps.resources is not None
        assert caps.prompts is not None
        # sampling is a client capability in MCP; the server advertises it via the
        # standard experimental map when the profile enables it.
        assert (caps.experimental or {}).get("sampling") is not None


async def test_no_sampling_omits_sampling_advertisement(client_no_sampling: Client):
    async with client_no_sampling as c:
        caps = c.initialize_result.capabilities
        assert caps.tools is not None
        assert caps.resources is not None
        assert caps.prompts is not None
        assert "sampling" not in (caps.experimental or {})


async def test_minimal_omits_list_changed(client_minimal: Client):
    async with client_minimal as c:
        caps = c.initialize_result.capabilities
        assert caps.tools is not None
        assert caps.tools.listChanged is False
        # minimal advertises neither resources nor prompts.
        assert caps.resources is None
        assert caps.prompts is None


async def test_full_advertises_list_changed(client_full: Client):
    async with client_full as c:
        caps = c.initialize_result.capabilities
        assert caps.tools.listChanged is True


# --------------------------------------------------------------------------- #
# Capability gating -> -32601 (T018, FR-011).
# --------------------------------------------------------------------------- #
async def test_tools_only_gates_resources_and_prompts(client_tools_only: Client):
    async with client_tools_only as c:
        for method in (c.list_resources_mcp, c.list_prompts_mcp):
            with pytest.raises(McpError) as exc:
                await method()
            assert exc.value.error.code == METHOD_NOT_FOUND


async def test_minimal_gates_resources_and_prompts(client_minimal: Client):
    async with client_minimal as c:
        for method in (c.list_resources_mcp, c.list_prompts_mcp):
            with pytest.raises(McpError) as exc:
                await method()
            assert exc.value.error.code == METHOD_NOT_FOUND


async def test_tools_list_is_never_gated(client_tools_only: Client):
    async with client_tools_only as c:
        result = await c.list_tools_mcp()  # must not raise
        assert result.tools is not None


# --------------------------------------------------------------------------- #
# Pagination wiring (T019, FR-008).
# --------------------------------------------------------------------------- #
def _app_with_dummy_tools(count: int):
    """Return a bare ``full``-profile app with *exactly* ``count`` dummy tools.

    Built directly (without ``register_all``) so the tool count is independent of
    the real feature catalog — otherwise these pagination unit tests would break
    the moment a feature WP (echo, etc.) registers additional tools.
    """
    from fastmcp import FastMCP

    app = FastMCP(name="mcpbin-pagination-test")
    for i in range(count):
        app.add_tool(Tool.from_function(lambda: "ok", name=f"dummy_{i:03d}"))
    server_mod._wire_pagination(app, profiles.get_profile(profiles.FULL))
    return app


async def test_pagination_first_page_capped_at_page_size():
    app = _app_with_dummy_tools(PAGE_SIZE + 2)
    async with Client(app) as c:
        result = await c.list_tools_mcp()
        assert len(result.tools) == PAGE_SIZE
        # Opaque cursor present because the catalog exceeds one page.
        assert result.nextCursor
        assert isinstance(result.nextCursor, str)


async def test_pagination_final_page_omits_next_cursor():
    app = _app_with_dummy_tools(PAGE_SIZE + 2)
    async with Client(app) as c:
        page1 = await c.list_tools_mcp()
        page2 = await c.list_tools_mcp(cursor=page1.nextCursor)
        assert len(page2.tools) == 2
        assert page2.nextCursor is None


async def test_pagination_single_page_has_no_cursor():
    app = _app_with_dummy_tools(3)
    async with Client(app) as c:
        result = await c.list_tools_mcp()
        assert len(result.tools) == 3
        assert result.nextCursor is None


async def test_pagination_cursor_is_opaque():
    app = _app_with_dummy_tools(PAGE_SIZE + 1)
    async with Client(app) as c:
        result = await c.list_tools_mcp()
        # Clients must not be able to read the offset trivially: not plain digits.
        assert not result.nextCursor.isdigit()


async def test_pagination_bad_cursor_raises_invalid_params():
    app = _app_with_dummy_tools(PAGE_SIZE + 1)
    async with Client(app) as c:
        with pytest.raises(McpError) as exc:
            await c.list_tools_mcp(cursor="not-a-real-cursor!!")
        assert exc.value.error.code == INVALID_PARAMS
        assert exc.value.error.message == INVALID_CURSOR_MESSAGE


async def test_tool_call_before_list_does_not_crash_paginated_handler():
    """Regression: the MCP SDK refreshes its tool-definition cache by invoking the
    ListToolsRequest handler with ``req=None`` on every ``tools/call``. The paginating
    wrapper must tolerate ``req is None`` instead of dereferencing ``req.method``.
    Calling a tool *before* listing reproduces the original crash.
    """
    app = _app_with_dummy_tools(3)
    async with Client(app) as c:
        result = await c.call_tool("dummy_000", {})
        assert result is not None


# --------------------------------------------------------------------------- #
# HTTP transport route wiring with a frontend present (T017, regression).
# --------------------------------------------------------------------------- #
async def test_http_app_serves_mcp_at_root_path_and_frontend(tmp_path, monkeypatch):
    """With a ``frontend/`` present, ``POST /mcp`` must reach the MCP endpoint
    (not the StaticFiles ``/`` mount) and ``GET /`` must serve the frontend.

    Regression for the ``/mcp`` -> ``/mcp/mcp`` double-prefix bug: building the inner
    MCP app at ``/mcp`` and mounting it under ``Mount("/mcp", ...)`` pushed the real
    endpoint to ``/mcp/mcp``, so StaticFiles answered ``POST /mcp`` with 405.
    """
    import httpx

    # A temporary frontend directory with a recognisable index.html.
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text("<html><body>mcpbin-ui</body></html>")
    monkeypatch.setattr(server_mod, "_resolve_frontend_dir", lambda: frontend)

    app = build_app(profiles.FULL, "http")
    http_app = _build_http_app(app)

    transport = httpx.ASGITransport(app=http_app)
    # The MCP app's lifespan (inherited by the parent) starts the session manager.
    async with http_app.router.lifespan_context(http_app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as hc:
            # GET / serves the frontend.
            root = await hc.get("/")
            assert root.status_code == 200
            assert "mcpbin-ui" in root.text

            # POST /mcp reaches the MCP handler, NOT the StaticFiles "/" mount.
            # StaticFiles would answer 405 (method not allowed); the MCP endpoint
            # rejects an unestablished/invalid Streamable HTTP request with 4xx
            # other than 405 (typically 400/406) or 200.
            mcp_resp = await hc.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
                headers={
                    "content-type": "application/json",
                    "accept": "application/json, text/event-stream",
                },
            )
            assert mcp_resp.status_code != 405, (
                "POST /mcp was handled by StaticFiles (405) instead of the MCP "
                "endpoint -- the /mcp mount is double-prefixed to /mcp/mcp"
            )
            assert mcp_resp.status_code in (200, 400, 406)


def test_http_app_without_frontend_returns_mcp_app_directly(monkeypatch):
    """When ``frontend/`` is absent, ``_build_http_app`` returns the MCP app rooted
    at ``/mcp`` directly (no parent Starlette wrapper)."""
    monkeypatch.setattr(server_mod, "_resolve_frontend_dir", lambda: None)
    app = build_app(profiles.FULL, "http")
    http_app = _build_http_app(app)
    paths = {getattr(r, "path", None) for r in http_app.routes}
    assert "/mcp" in paths
