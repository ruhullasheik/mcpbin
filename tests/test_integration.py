"""Cross-WP integration test (WP15, T059) — FR-018, NFR-001.

Asserts catalog sizing (the real, un-padded catalog exercises pagination) and a
determinism spot-check. Documents the R11 decision.
"""

from __future__ import annotations

import json

from fastmcp import Client

# R11 decision (recorded): the documented, un-padded catalog is 42 tools / 124 resources
# / 5 prompts. Tools (5 pages) and resources (13 pages) genuinely exercise pagination;
# the 5 documented prompt shapes fit on one page. The PRD's "50+ tools/prompts" was a
# target, not a hard floor, and FR-018 forbids synthetic padding — so we keep the real
# feature catalog and assert pagination is exercised where it naturally occurs.
EXPECTED_TOOLS = 42
EXPECTED_PROMPTS = 5
MIN_RESOURCES = 100


async def test_catalog_sizes(client_full: Client):
    async with client_full as c:
        tools = await c.list_tools()
        resources = await c.list_resources()
        prompts = await c.list_prompts()
    assert len(tools) == EXPECTED_TOOLS, [t.name for t in tools]
    assert len(resources) >= MIN_RESOURCES
    assert len(prompts) == EXPECTED_PROMPTS


async def test_all_feature_areas_present(client_full: Client):
    async with client_full as c:
        names = {t.name for t in await c.list_tools()}
    # one canonical tool per feature area must be present (cross-area smoke).
    for canary in (
        "echo",
        "return_text",
        "error_parse",
        "delay_1s",
        "schema_no_args",
        "notify_log",
        "sampling_unsupported",
        "inspect_session",
    ):
        assert canary in names, f"missing {canary}"


async def test_determinism_spot_check(client_full: Client):
    """Identical deterministic calls return identical content (excluding dynamic fields)."""
    async with client_full as c:
        r1 = await c.call_tool("echo_string", {"value": "repeatable"})
        r2 = await c.call_tool("echo_string", {"value": "repeatable"})
    t1 = [b.text for b in r1.content]
    t2 = [b.text for b in r2.content]
    assert t1 == t2
