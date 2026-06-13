"""Cross-cutting pagination test (WP15, T057) — FR-008, SC-004.

Validates opaque-cursor pagination against the *real* catalog: tools (42 -> multiple
pages) and resources (124 -> multiple pages) must span >1 page with an opaque nextCursor
on every non-final page and NO nextCursor on the final page; an invalid cursor returns
-32602 "invalid or expired cursor". Prompts (5) fit on a single page (documented).
"""

from __future__ import annotations

import pytest
from fastmcp import Client
from mcp import McpError

from mcpbin.pagination import PAGE_SIZE
from mcpbin.errors import INVALID_CURSOR_MESSAGE, INVALID_PARAMS


async def _walk(c: Client, method: str, field: str):
    """Return (pages, total_items). Each page is the raw List*Result."""
    pages = []
    items = 0
    cursor = None
    while True:
        result = await getattr(c, method)(cursor=cursor)
        pages.append(result)
        items += len(getattr(result, field))
        cursor = result.nextCursor
        if not cursor:
            break
    return pages, items


async def test_tools_list_multipage(client_full: Client):
    async with client_full as c:
        pages, total = await _walk(c, "list_tools_mcp", "tools")
    assert total >= 40
    assert len(pages) > 1  # multiple pages required (SC-004)
    for p in pages[:-1]:
        assert p.nextCursor and isinstance(p.nextCursor, str)
        assert len(p.tools) == PAGE_SIZE
    assert pages[-1].nextCursor is None  # final page omits nextCursor (absent)


async def test_resources_list_multipage(client_full: Client):
    async with client_full as c:
        pages, total = await _walk(c, "list_resources_mcp", "resources")
    assert total >= 100
    assert len(pages) > 1
    for p in pages[:-1]:
        assert p.nextCursor
        assert len(p.resources) == PAGE_SIZE
    assert pages[-1].nextCursor is None


async def test_prompts_list_single_page(client_full: Client):
    async with client_full as c:
        pages, total = await _walk(c, "list_prompts_mcp", "prompts")
    # 5 documented prompt shapes fit on one page (R11): single page, no nextCursor.
    assert total == 5
    assert len(pages) == 1
    assert pages[0].nextCursor is None


async def test_invalid_cursor_returns_minus_32602(client_full: Client):
    async with client_full as c:
        for method in ("list_tools_mcp", "list_resources_mcp", "list_prompts_mcp"):
            with pytest.raises(McpError) as exc:
                await getattr(c, method)(cursor="totally-bogus-cursor!!")
            assert exc.value.error.code == INVALID_PARAMS
            assert exc.value.error.message == INVALID_CURSOR_MESSAGE
