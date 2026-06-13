"""FastMCP application, transports, profile gating and pagination wiring (WP03).

This module ties the WP02 primitives (``profiles``, ``registry``, ``session``,
``pagination``, ``errors``) into a runnable FastMCP server with a single CLI entry
point. It is intentionally free of any feature-module imports: feature tools /
resources / prompts add themselves through :func:`mcpbin.registry.register_all`,
so this file stays stable as later WPs land.

Verify-on-impl findings (fastmcp 3.4.2 / mcp SDK, spec 2025-03-26)
=================================================================
These were confirmed by reading the installed fastmcp + mcp source and by probing a
live ``FastMCP`` instance. Later WPs depend on this contract, so the mechanics are
documented here in detail.

Transports (R1)
---------------
``FastMCP.run(transport=...)`` / ``run_async`` accept exactly these strings::

    {"stdio", "http", "sse", "streamable-http"}

``"http"`` is an alias of ``"streamable-http"``. Our CLI exposes ``stdio|sse|http``
(``http`` -> Streamable HTTP) per ``contracts/protocol.md``. ``run`` is synchronous
and wraps ``run_async`` via ``anyio.run``; for HTTP we build the ASGI app ourselves
(see below) so we can also mount the static frontend, then drive uvicorn through
``run_http_async``-equivalent wiring.

Advertised capabilities at ``initialize`` (R2)
----------------------------------------------
The MCP SDK derives ``ServerCapabilities`` *purely from which list handlers are
registered* on the low-level server (``app._mcp_server.request_handlers``) plus the
server's ``notification_options``:

* ``ListToolsRequest`` present     -> advertises ``tools``     (``listChanged`` from
  ``notification_options.tools_changed``)
* ``ListResourcesRequest`` present -> advertises ``resources``
* ``ListPromptsRequest`` present   -> advertises ``prompts``

FastMCP's ``_setup_handlers`` *always* registers all three (even with an empty
catalog), so by default an omitted capability would serve an **empty list** rather
than the spec-mandated ``-32601``. We therefore **delete** the list handler entries
for capabilities the active profile omits (see :func:`_gate_capabilities`). Deleting
the handler simultaneously (a) drops the capability from the advertised
``initialize`` result and (b) makes the SDK return JSON-RPC ``-32601`` "Method not
found" for that method (mcp ``Server._handle_request`` falls through to
``METHOD_NOT_FOUND`` when no handler is registered) — exactly FR-011.

``sampling`` is a *client* capability in MCP; the server's ``ServerCapabilities`` has
no ``sampling`` field. To make the profile's sampling advertisement observable (and
to let WP08's sampling tools/clients detect it), we advertise it under the standard
``capabilities.experimental`` map as ``{"sampling": {}}`` when the profile enables
sampling, via the ``experimental_capabilities`` constructor argument.

``listChanged`` (R2)
--------------------
Controlled by ``app._mcp_server.notification_options.{tools,resources,prompts}_changed``.
``minimal`` must not advertise ``listChanged``; we set those flags to ``False``.
(Note: fastmcp's *stdio* run path hardcodes ``NotificationOptions(tools_changed=True)``
in ``run_stdio_async``; the in-memory client path and our HTTP path both honour the
``_mcp_server.notification_options`` we set here, which is what the conformance tests
and downstream WPs observe.)

Pagination (R3)
---------------
fastmcp ships its own cursor pagination (``_list_page_size`` + ``paginate_sequence``)
but its invalid-cursor message is ``f"Invalid cursor: {cursor}"`` — not the
spec-required ``"invalid or expired cursor"``. We therefore leave ``_list_page_size``
unset (so fastmcp returns the *full* catalog) and **wrap** the three list handlers:
the wrapper asks fastmcp to build the complete MCP result, then re-slices the items
through WP02's :func:`mcpbin.pagination.paginate` (page size 10, opaque base64 cursor,
absent ``nextCursor`` on the final page, ``-32602 "invalid or expired cursor"`` on a
bad cursor). This is catalog-agnostic: it paginates whatever feature modules register.

In-memory test client (T020)
----------------------------
``fastmcp.Client(app)`` uses the in-memory ``FastMCPTransport`` (no subprocess). It
calls ``app._mcp_server.create_initialization_options()`` with no explicit
notification options, so it reflects the ``notification_options`` we set above.
``client.initialize_result.capabilities`` exposes the advertised capabilities;
``client.list_tools_mcp(cursor=...)`` etc. return the raw ``List*Result`` (with
``.nextCursor``); an omitted method raises ``mcp.McpError`` with ``error.code``.

Static frontend + ``/mcp`` (T017)
---------------------------------
For HTTP transports we build the MCP ASGI app via ``app.http_app(path="/mcp")``, which
registers a single Starlette ``Route`` at exactly ``/mcp``. When a frontend is present
we splice that route verbatim into a parent Starlette app alongside ``StaticFiles`` at
``/``. We deliberately do **not** wrap the MCP app in ``Mount("/mcp", ...)``: mounting
strips the matched prefix to an empty path, so the endpoint ends up at ``/mcp/mcp`` and
only ``/mcp/`` (with trailing slash) ever reaches it while bare ``POST /mcp`` falls
through to the ``StaticFiles`` ``/`` mount as a 405. Reusing the route directly keeps
the canonical ``/mcp`` endpoint intact. The parent app **must** inherit
``mcp_app.lifespan`` or the Streamable HTTP session manager is never started.
``frontend/`` is authored by WP14 and may be absent now; :func:`_resolve_frontend_dir`
returns ``None`` and we return the MCP app as-is (already serving ``/mcp``) with a
warning rather than crashing.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import mcp.types

from . import profiles, registry
from .errors import METHOD_NOT_FOUND
from .pagination import PAGE_SIZE, paginate
from .profiles import Profile
from .session import SessionStore

logger = logging.getLogger("mcpbin.server")

SERVER_NAME = "mcpbin"

# CLI transport flag -> fastmcp transport keyword. "http" maps to Streamable HTTP.
TRANSPORTS: dict[str, str] = {
    "stdio": "stdio",
    "sse": "sse",
    "http": "http",  # == fastmcp "streamable-http"
}

# MCP list methods we gate / paginate, keyed by capability flag name.
# Each entry: capability flag -> (request type, result field holding the item list).
_LIST_METHODS: dict[str, tuple[type, str]] = {
    "tools": (mcp.types.ListToolsRequest, "tools"),
    "resources": (mcp.types.ListResourcesRequest, "resources"),
    "prompts": (mcp.types.ListPromptsRequest, "prompts"),
}


# --------------------------------------------------------------------------- #
# Runtime context shared with feature modules.
# --------------------------------------------------------------------------- #
class ServerContext:
    """Opaque runtime context handed to every feature ``register(app, profile, ctx)``.

    Carries the shared :class:`SessionStore` (and the active profile/transport for
    convenience). The registry treats this as opaque; feature modules read what they
    need. Kept here (not in WP02) because it is assembled by the server.
    """

    def __init__(self, profile: Profile, transport: str, sessions: SessionStore) -> None:
        self.profile = profile
        self.transport = transport
        self.sessions = sessions


# --------------------------------------------------------------------------- #
# Capability gating (FR-011).
# --------------------------------------------------------------------------- #
def _gate_capabilities(app: Any, profile: Profile) -> None:
    """Remove list handlers for capabilities the profile omits, and set listChanged.

    Deleting a ``List*Request`` handler both (a) drops the capability from the
    advertised ``initialize`` result and (b) makes the SDK answer that method with
    JSON-RPC ``-32601``. ``minimal`` additionally disables every ``listChanged``
    notification flag.
    """
    handlers = app._mcp_server.request_handlers
    for capability, (request_type, _field) in _LIST_METHODS.items():
        # ``tools`` is always enabled (every profile has tools=True), but gate
        # generically so the rule is data-driven.
        if not profile.has(capability):
            handlers.pop(request_type, None)
            logger.debug(
                "profile %s omits %s; %s will return -%d",
                profile.name,
                capability,
                request_type.__name__,
                -METHOD_NOT_FOUND,
            )

    # listChanged advertisement is driven by the low-level notification options.
    notif = app._mcp_server.notification_options
    notif.tools_changed = profile.list_changed
    notif.resources_changed = profile.list_changed
    notif.prompts_changed = profile.list_changed


# --------------------------------------------------------------------------- #
# Pagination wiring (FR-008).
# --------------------------------------------------------------------------- #
def _wrap_list_handler(app: Any, request_type: type, item_field: str) -> None:
    """Override a list handler to paginate via WP02's :func:`paginate` (page size 10).

    The wrapper delegates to fastmcp's existing handler (which builds the *full* MCP
    result because ``_list_page_size`` is unset), then re-slices ``result.<item_field>``
    with our opaque-cursor codec. A bad cursor surfaces as ``-32602 "invalid or
    expired cursor"`` (raised by ``paginate``); fastmcp's stricter conversions stay
    untouched, so this remains catalog-agnostic.
    """
    inner = app._mcp_server.request_handlers.get(request_type)
    if inner is None:  # gated away; nothing to paginate
        return

    async def handler(req: Any) -> mcp.types.ServerResult:
        # The MCP SDK refreshes its tool-definition cache by invoking the
        # ListToolsRequest handler with ``req=None`` on every ``tools/call``.
        # There is no cursor to honor in that path, so delegate straight to the
        # inner handler (pagination only applies to real list requests).
        if req is None:
            return await inner(req)

        cursor = None
        params = getattr(req, "params", None)
        if params is not None:
            cursor = getattr(params, "cursor", None)

        # Ask fastmcp for the complete (unpaginated) result, then re-paginate.
        # Pass a cursor-stripped request so fastmcp never paginates underneath us.
        full = await inner(_with_cursor(req, request_type, None))
        result = full.root if isinstance(full, mcp.types.ServerResult) else full

        items = list(getattr(result, item_field))
        page, next_cursor = paginate(items, cursor, PAGE_SIZE)

        paged = result.model_copy(update={item_field: page, "nextCursor": next_cursor})
        return mcp.types.ServerResult(paged)

    app._mcp_server.request_handlers[request_type] = handler


def _with_cursor(req: Any, request_type: type, cursor: str | None) -> Any:
    """Return a copy of ``req`` whose ``params.cursor`` is ``cursor``.

    fastmcp's inner handlers tolerate ``params is None`` (treated as cursor=None),
    which is what we want when forcing a full listing.
    """
    if cursor is None:
        # Easiest "no cursor" request: drop params entirely (handlers default to None).
        return request_type(method=req.method, params=None)
    params = req.params.model_copy(update={"cursor": cursor})
    return req.model_copy(update={"params": params})


def _wire_pagination(app: Any, profile: Profile) -> None:
    """Install paginating wrappers for every still-registered list handler."""
    for capability, (request_type, item_field) in _LIST_METHODS.items():
        if profile.has(capability):
            _wrap_list_handler(app, request_type, item_field)


# --------------------------------------------------------------------------- #
# App construction.
# --------------------------------------------------------------------------- #
def build_app(profile_name: str, transport: str) -> Any:
    """Build and return a configured ``FastMCP`` app for ``profile_name``.

    Steps: resolve the profile, create the ``FastMCP`` instance (advertising sampling
    via ``experimental_capabilities`` when enabled), create the :class:`SessionStore`,
    register all feature modules through the registry, gate omitted capabilities to
    ``-32601``, then wire opaque-cursor pagination onto the surviving list handlers.

    ``transport`` is recorded on the context (and validated by the CLI) but does not
    change the app object itself; the same app runs over any transport.
    """
    # Imported lazily so ``import mcpbin`` never hard-requires fastmcp before runtime.
    from fastmcp import FastMCP

    profile = profiles.get_profile(profile_name)

    experimental: dict[str, dict[str, Any]] = {}
    if profile.has("sampling"):
        # MCP has no server-side `sampling` capability field; advertise it under the
        # standard experimental map so clients/tests can observe the profile choice.
        experimental["sampling"] = {}

    app = FastMCP(
        name=SERVER_NAME,
        version=_package_version(),
        experimental_capabilities=experimental or None,
    )

    sessions = SessionStore()
    ctx = ServerContext(profile=profile, transport=transport, sessions=sessions)

    # Feature modules add themselves (catalog-agnostic; no feature imports here).
    registry.register_all(app, profile, ctx)

    # Gate first (may delete handlers), then paginate the survivors.
    _gate_capabilities(app, profile)
    _wire_pagination(app, profile)

    logger.info(
        "built app: profile=%s transport=%s tools=%s resources=%s prompts=%s "
        "sampling=%s pagination=%s listChanged=%s",
        profile.name,
        transport,
        profile.tools,
        profile.resources,
        profile.prompts,
        profile.sampling,
        profile.pagination,
        profile.list_changed,
    )
    return app


def _package_version() -> str:
    """Return the package version string (best-effort)."""
    try:
        from . import __version__

        return __version__
    except Exception:  # noqa: BLE001 - version is cosmetic
        return "0"


# --------------------------------------------------------------------------- #
# Static frontend resolution (T017).
# --------------------------------------------------------------------------- #
def _resolve_frontend_dir() -> Path | None:
    """Return the ``frontend/`` directory to serve, or ``None`` if it is absent.

    Resolution order (defensive — ``frontend/`` is authored by WP14 and may not
    exist yet):

    1. Packaged ``mcpbin/frontend`` (installed wheel data, via importlib.resources).
    2. Repo-root ``frontend/`` relative to this source tree (editable installs).

    Returns ``None`` when neither exists so HTTP transports start without a web UI
    instead of crashing.
    """
    # 1. Packaged data directory.
    try:
        from importlib.resources import files

        packaged = files("mcpbin") / "frontend"
        packaged_path = Path(str(packaged))
        if packaged_path.is_dir():
            return packaged_path
    except (ImportError, ModuleNotFoundError, FileNotFoundError):
        pass

    # 2. Repo-root frontend/ (this file lives at <repo>/src/mcpbin/server.py).
    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root / "frontend"
    if candidate.is_dir():
        return candidate

    return None


def _build_http_app(app: Any) -> Any:
    """Build the ASGI app for HTTP transports: static frontend at ``/`` + MCP at ``/mcp``.

    When a frontend is present, splices the ``/mcp`` route(s) of
    ``app.http_app(path="/mcp")`` directly into a parent Starlette app alongside
    ``StaticFiles`` at ``/`` (so the endpoint stays at exactly ``/mcp`` rather than
    ``/mcp/mcp``). The parent Starlette app inherits the MCP app's lifespan (required
    for the Streamable HTTP session manager). If ``frontend/`` is missing, the MCP app
    rooted at ``/mcp`` is returned as-is (it already serves ``/mcp``).
    """
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from starlette.staticfiles import StaticFiles

    # Build the MCP ASGI app rooted at '/mcp'. ``http_app(path="/mcp")`` registers a
    # single Starlette ``Route`` at exactly '/mcp'.
    mcp_app = app.http_app(path="/mcp", transport="http")

    frontend = _resolve_frontend_dir()
    if frontend is None:
        logger.warning(
            "frontend/ directory not found; serving MCP only (no static UI at '/'). "
            "It is authored by a later work package."
        )
        return mcp_app

    # Frontend present: reuse the MCP app's own '/mcp' route(s) verbatim in the parent
    # app, then add StaticFiles at '/'. We must NOT wrap mcp_app in Mount("/mcp", ...):
    # that double-prefixes the endpoint to '/mcp/mcp' and (because mounting strips the
    # prefix to an empty path) only ever matches '/mcp/' while bare 'POST /mcp' falls
    # through to the StaticFiles '/' mount as a 405. Splicing the route in directly
    # keeps the endpoint at exactly '/mcp'. The parent must inherit mcp_app.lifespan to
    # start the Streamable HTTP session manager.
    parent = Starlette(
        routes=[
            *mcp_app.routes,
            Mount("/", app=StaticFiles(directory=str(frontend), html=True)),
        ],
        lifespan=mcp_app.lifespan,
    )
    logger.info("serving static frontend from %s at '/' and MCP at '/mcp'", frontend)
    return parent


# --------------------------------------------------------------------------- #
# Transport run wiring (T016).
# --------------------------------------------------------------------------- #
def _run(app: Any, transport: str) -> None:
    """Run ``app`` over the selected ``transport`` (blocking)."""
    if transport == "stdio":
        app.run(transport="stdio", show_banner=False)
        return

    if transport == "sse":
        app.run(transport="sse", show_banner=False)
        return

    if transport == "http":
        # Streamable HTTP with a static frontend mounted at '/'. We build the ASGI
        # app ourselves (to add static files) and drive uvicorn directly.
        import fastmcp
        import uvicorn

        http_app = _build_http_app(app)
        host = fastmcp.settings.host
        port = fastmcp.settings.port
        logger.info("starting Streamable HTTP server on http://%s:%d/mcp", host, port)
        uvicorn.run(http_app, host=host, port=port, log_level="info")
        return

    raise ValueError(f"unknown transport: {transport!r}")


# --------------------------------------------------------------------------- #
# CLI (T015).
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse CLI (dependency-free per C-003)."""
    parser = argparse.ArgumentParser(
        prog=SERVER_NAME,
        description='mcpbin — a diagnostic MCP test server ("httpbin for MCP").',
    )
    parser.add_argument(
        "--transport",
        choices=sorted(TRANSPORTS),
        default="stdio",
        help="transport to serve over (default: stdio). 'http' is Streamable HTTP.",
    )
    parser.add_argument(
        "--profile",
        choices=[profiles.FULL, profiles.TOOLS_ONLY, profiles.NO_SAMPLING, profiles.MINIMAL],
        default=profiles.DEFAULT_PROFILE,
        help="capability profile to advertise (default: full).",
    )
    return parser


def _configure_logging() -> None:
    """Configure structured logging to **stderr** (FR-016).

    Idempotent: a no-op if a handler is already configured (e.g. by an embedding host
    or a previous call within tests).
    """
    root = logging.getLogger("mcpbin")
    if root.handlers:
        return
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.propagate = False


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Parse ``--transport``/``--profile``, build and run the app.

    Returns a process exit code (``0`` on a clean shutdown). ``argv`` defaults to
    ``sys.argv[1:]``; passing ``["--help"]`` triggers argparse's help-and-exit.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    _configure_logging()
    logger.info("starting mcpbin: transport=%s profile=%s", args.transport, args.profile)

    app = build_app(args.profile, args.transport)
    try:
        _run(app, args.transport)
    except KeyboardInterrupt:  # pragma: no cover - interactive shutdown
        logger.info("interrupted; shutting down")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["build_app", "main", "ServerContext", "TRANSPORTS", "SERVER_NAME"]
