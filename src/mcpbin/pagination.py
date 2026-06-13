"""Opaque cursor pagination codec (FR-008, research R3).

Pure functions — **no fastmcp import** — so the codec is trivially unit-testable and
its byte-level semantics are guaranteed regardless of FastMCP defaults.

Contract (``contracts/protocol.md``):
- Page size = 10 for ``tools/list``, ``resources/list``, ``prompts/list``.
- ``cursor`` omitted -> first page (offset 0).
- ``nextCursor`` is an **opaque** base64 string; clients must not parse/construct it.
- **Final page omits ``nextCursor`` entirely** — the caller drops the field when
  ``paginate`` returns ``None`` (not ``null``, not ``""``).
- Invalid / malformed / out-of-range cursor -> JSON-RPC ``-32602`` with message
  ``"invalid or expired cursor"``.
"""

from __future__ import annotations

import base64

from .errors import INVALID_CURSOR_MESSAGE, INVALID_PARAMS, mcp_error

PAGE_SIZE = 10

# Internal token shape: "offset:<n>". Opaque to clients (urlsafe-base64 wrapped).
_TOKEN_PREFIX = "offset:"


def encode_cursor(offset: int) -> str:
    """Encode a non-negative ``offset`` into an opaque urlsafe-base64 cursor."""
    token = f"{_TOKEN_PREFIX}{offset}".encode()
    return base64.urlsafe_b64encode(token).decode("ascii")


def decode_cursor(cursor: str | None) -> int:
    """Decode an opaque cursor back to its integer offset.

    ``None`` -> ``0`` (first page). Anything malformed, non-base64, wrong-prefix,
    non-integer, or negative raises ``mcp_error(-32602, "invalid or expired cursor")``.
    """
    if cursor is None:
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    except Exception as exc:  # noqa: BLE001 - any decode failure is an invalid cursor
        raise mcp_error(INVALID_PARAMS, INVALID_CURSOR_MESSAGE) from exc

    if not raw.startswith(_TOKEN_PREFIX):
        raise mcp_error(INVALID_PARAMS, INVALID_CURSOR_MESSAGE)

    digits = raw[len(_TOKEN_PREFIX):]
    if not digits.isdigit():  # rejects negatives, signs, whitespace, empty
        raise mcp_error(INVALID_PARAMS, INVALID_CURSOR_MESSAGE)

    return int(digits)


def paginate(
    items: list,
    cursor: str | None,
    page_size: int = PAGE_SIZE,
) -> tuple[list, str | None]:
    """Slice ``items`` into a page starting at ``cursor``.

    Returns ``(page_items, next_cursor)`` where ``next_cursor`` is ``None`` on the
    final page so the caller can **omit** ``nextCursor`` entirely. An offset at or
    beyond the end of the catalog raises ``-32602`` (out-of-range cursor), except the
    natural offset==len boundary is not reachable because the final page never emits a
    next cursor.
    """
    offset = decode_cursor(cursor)

    # Out-of-range: an offset past the catalog is an invalid/expired cursor. offset==0
    # on an empty catalog is valid (empty first page).
    if offset > len(items) or (offset == len(items) and offset != 0):
        raise mcp_error(INVALID_PARAMS, INVALID_CURSOR_MESSAGE)

    page = items[offset:offset + page_size]
    next_offset = offset + page_size
    next_cursor = encode_cursor(next_offset) if next_offset < len(items) else None
    return page, next_cursor


__all__ = ["PAGE_SIZE", "encode_cursor", "decode_cursor", "paginate"]
