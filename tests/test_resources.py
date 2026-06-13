"""Resource tests (WP12, T049) — FR-006.

Exercises resource listing (with pagination), reads of every shape, the URI template,
and the two distinct not-found cases (unknown template id vs mcpbin://missing).
"""

from __future__ import annotations

import base64

import pytest
from fastmcp import Client
from mcp import McpError


async def _list_all_resource_uris(c: Client) -> set[str]:
    """Follow every nextCursor page to build the full resources/list URI set."""
    uris: set[str] = set()
    cursor = None
    while True:
        page = await c.list_resources_mcp(cursor=cursor)
        uris.update(str(r.uri) for r in page.resources)
        cursor = page.nextCursor
        if not cursor:
            break
    return uris


async def test_resources_list_is_large_and_paginated(client_full: Client):
    async with client_full as c:
        # First page is capped at the page size (10); more pages follow.
        first = await c.list_resources_mcp()
        assert len(first.resources) == 10
        assert first.nextCursor

        uris = await _list_all_resource_uris(c)
        assert len(uris) >= 100
        assert "mcpbin://text/plain" in uris
        assert "mcpbin://text/markdown" in uris
        assert "mcpbin://blob/binary" in uris
        assert "mcpbin://missing" in uris


async def test_text_and_markdown_read(client_full: Client):
    async with client_full as c:
        plain = await c.read_resource("mcpbin://text/plain")
        assert "plain text" in plain[0].text.lower()
        md = await c.read_resource("mcpbin://text/markdown")
        assert md[0].text.lstrip().startswith("#")


async def test_blob_read_is_valid_base64(client_full: Client):
    async with client_full as c:
        blob = await c.read_resource("mcpbin://blob/binary")
        # Binary resources surface as BlobResourceContents with a base64 `blob` field.
        b64 = blob[0].blob
        decoded = base64.b64decode(b64)
        assert decoded == b"mcpbin-binary-blob-\x00\x01\x02\x03-deterministic"


async def test_dynamic_template_valid_ids_distinct(client_full: Client):
    async with client_full as c:
        texts = {}
        for rid in ("alpha", "beta", "gamma"):
            res = await c.read_resource(f"mcpbin://dynamic/{rid}")
            texts[rid] = res[0].text
        # Each id yields distinct content mentioning its id.
        assert len(set(texts.values())) == 3
        for rid, text in texts.items():
            assert rid in text


async def test_dynamic_unknown_id_not_found(client_full: Client):
    async with client_full as c:
        with pytest.raises((McpError, Exception)):
            await c.read_resource("mcpbin://dynamic/delta")


async def test_missing_resource_listed_but_not_found_on_read(client_full: Client):
    async with client_full as c:
        uris = await _list_all_resource_uris(c)
        assert "mcpbin://missing" in uris  # listed
        with pytest.raises((McpError, Exception)):
            await c.read_resource("mcpbin://missing")  # but not readable
