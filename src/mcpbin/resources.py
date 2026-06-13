"""MCP resources (FR-006): every resource shape a client should handle.

Registered via the :func:`register` contract and discovered by
:func:`mcpbin.registry.register_all` (guarded ``mcpbin.resources`` import). Under
profiles that omit ``resources`` the registry never calls this module.

Shapes (see ``contracts/resources.md``):

* ``mcpbin://text/plain``     – plain-text resource.
* ``mcpbin://text/markdown``  – markdown resource.
* ``mcpbin://blob/binary``    – binary blob (base64 on the wire).
* ``mcpbin://large/paginated/{n}`` (n = 000..119) – a deliberately large family so
  ``resources/list`` requires multiple opaque-cursor pages (SC-004); these are a
  genuine large resource list, not synthetic padding.
* ``mcpbin://dynamic/{id}``   – URI template; ``alpha``/``beta``/``gamma`` return
  distinct text, any other id is a not-found error (the URI resolves, content does not).
* ``mcpbin://missing``        – listed in ``resources/list`` but always not-found on
  read (simulates a deleted/unavailable resource — distinct from an unknown template id).

Not-found is surfaced by raising :class:`fastmcp.exceptions.ResourceError`, which the
SDK turns into an error response for ``resources/read``.
"""

from __future__ import annotations

from typing import Any

from fastmcp.exceptions import ResourceError
from fastmcp.resources import BinaryResource, TextResource

from .profiles import Profile

# Number of resources in the large paginated family (>100 forces multi-page listing).
_LARGE_FAMILY_COUNT = 120

_PLAIN_TEXT = "mcpbin plain text resource — deterministic content for client testing."
_MARKDOWN_TEXT = "# mcpbin markdown resource\n\nA **deterministic** markdown resource.\n"
_BLOB_BYTES = b"mcpbin-binary-blob-\x00\x01\x02\x03-deterministic"

_DYNAMIC_VALID = {"alpha", "beta", "gamma"}


def register(app: Any, profile: Profile, ctx: Any) -> None:
    """Register all resources (no-op when the profile omits ``resources``)."""
    if not profile.resources:
        return

    app.add_resource(
        TextResource(
            uri="mcpbin://text/plain",
            name="Plain text",
            description="A plain-text resource.",
            mime_type="text/plain",
            text=_PLAIN_TEXT,
        )
    )
    app.add_resource(
        TextResource(
            uri="mcpbin://text/markdown",
            name="Markdown",
            description="A markdown resource.",
            mime_type="text/markdown",
            text=_MARKDOWN_TEXT,
        )
    )
    app.add_resource(
        BinaryResource(
            uri="mcpbin://blob/binary",
            name="Binary blob",
            description="A binary blob, base64-encoded on the wire.",
            mime_type="application/octet-stream",
            data=_BLOB_BYTES,
        )
    )

    # Large family — forces resources/list pagination (page size 10).
    for n in range(_LARGE_FAMILY_COUNT):
        app.add_resource(
            TextResource(
                uri=f"mcpbin://large/paginated/{n:03d}",
                name=f"Paginated item {n:03d}",
                description="One entry of the large paginated resource list.",
                mime_type="text/plain",
                text=f"Large paginated resource #{n:03d} — deterministic content.",
            )
        )

    # URI template: alpha/beta/gamma resolve; any other id is not-found.
    @app.resource(
        "mcpbin://dynamic/{id}",
        name="Dynamic template",
        description="URI-template resource; valid ids are alpha, beta, gamma.",
        mime_type="text/plain",
    )
    def dynamic(id: str) -> str:
        if id not in _DYNAMIC_VALID:
            raise ResourceError(
                f"resource not found: mcpbin://dynamic/{id} "
                f"(valid ids: {', '.join(sorted(_DYNAMIC_VALID))})"
            )
        return f"Dynamic resource '{id}' — deterministic content for mcpbin://dynamic/{id}."

    # Listed but always not-found on read.
    @app.resource(
        "mcpbin://missing",
        name="Missing",
        description="Listed in resources/list but always returns not-found on read.",
        mime_type="text/plain",
    )
    def missing() -> str:
        raise ResourceError(
            "resource not found: mcpbin://missing (simulates a deleted/unavailable resource)"
        )


__all__ = ["register"]
