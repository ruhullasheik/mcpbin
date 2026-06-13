"""Tests for the WP07 delay tools (FR-004, NFR-002, NFR-003).

Speed contract: this suite never performs the real 30 s / 60 s waits. Clamp and
fixed-delay behaviour is asserted either with a tiny real value (the ``delay 2``
timing window for NFR-002) or by patching ``asyncio.sleep`` to record its argument
without sleeping. The cancellation branch is exercised by injecting a real
``asyncio.CancelledError`` into the running coroutine (see
``test_delay_cancel_returns_cancelled``), because the mcp SDK both emits its own
cancellation error and suppresses the handler's response, so the bespoke
``"cancelled by client"`` payload is not deliverable over the in-memory wire (see
``mcpbin.tools.delays`` module docstring).
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from mcpbin.tools import delays


def _meta_of(result) -> dict:
    """Parse the trailing ``_meta`` envelope text block of a ToolResult/CallToolResult."""
    content = result.content
    return json.loads(content[-1].text)["_meta"]


# --------------------------------------------------------------------------- #
# Registration / catalog
# --------------------------------------------------------------------------- #
async def test_delay_tools_registered(client_full):
    async with client_full as client:
        names = {t.name for t in await client.list_tools()}
    assert {"delay", "delay_1s", "delay_5s", "delay_30s", "delay_cancel"} <= names


# --------------------------------------------------------------------------- #
# delay: real (short) timing + clamp via patched sleep
# --------------------------------------------------------------------------- #
async def test_delay_two_seconds_completes_in_window(client_full):
    """NFR-002: delay 2 completes after ~2 s (tolerant CI window) with _meta."""
    start = time.monotonic()
    async with client_full as client:
        result = await client.call_tool("delay", {"seconds": 2})
    elapsed = time.monotonic() - start
    # Tolerant window: must actually wait ~2 s but not block CI for long.
    assert 1.5 <= elapsed <= 6.0
    meta = _meta_of(result)
    assert meta["tool"] == "delay"
    assert meta["received"] == {"seconds": 2}


def test_effective_delay_clamps_at_30():
    """Clamp logic: anything above 30 collapses to 30; negatives floor at 0."""
    assert delays._effective_delay(99) == 30.0
    assert delays._effective_delay(30) == 30.0
    assert delays._effective_delay(2) == 2.0
    assert delays._effective_delay(-5) == 0.0


async def test_delay_99_clamps_without_waiting(monkeypatch):
    """delay 99 must sleep <=30 s. Patch asyncio.sleep to record the arg (no real wait)."""
    recorded: list[float] = []

    async def fake_sleep(seconds):
        recorded.append(seconds)

    monkeypatch.setattr(delays.asyncio, "sleep", fake_sleep)
    result = await delays._delay(99)

    assert recorded == [30.0]  # clamped, and we did not actually wait
    meta = _meta_of(result)
    assert meta["tool"] == "delay"
    assert meta["received"] == {"seconds": 99}
    assert "clamped" in meta["note"]


# --------------------------------------------------------------------------- #
# Fixed delays: assert duration via patched sleep (no real 5 s / 30 s waits)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("tool_name", "seconds"),
    [("delay_1s", 1), ("delay_5s", 5), ("delay_30s", 30)],
)
async def test_fixed_delays_sleep_expected_duration(monkeypatch, tool_name, seconds):
    recorded: list[float] = []

    async def fake_sleep(value):
        recorded.append(value)

    monkeypatch.setattr(delays.asyncio, "sleep", fake_sleep)
    result = await delays._fixed_delay(tool_name, seconds)

    assert recorded == [seconds]
    meta = _meta_of(result)
    assert meta["tool"] == tool_name
    assert meta["received"] == {}


# --------------------------------------------------------------------------- #
# delay_cancel: both branches
# --------------------------------------------------------------------------- #
async def test_delay_cancel_completed_branch():
    """No cancellation -> normal result, _meta reports completed (wait_seconds=0)."""
    result = await delays._delay_cancel(wait_seconds=0)
    assert result.is_error is False
    meta = _meta_of(result)
    assert meta["tool"] == "delay_cancel"
    assert "completed" in meta["note"]


async def test_delay_cancel_returns_cancelled():
    """Cancellation branch: inject CancelledError, assert prompt isError + exact message.

    Drives the coroutine as an asyncio task and cancels it once it is parked in the
    60 s sleep. The handler catches the CancelledError and synchronously returns the
    contract payload, so ``await task`` resolves with the result (not a CancelledError).
    """
    task = asyncio.create_task(delays._delay_cancel())
    # Let the task reach its `await asyncio.sleep(60)` checkpoint.
    await asyncio.sleep(0.05)

    start = time.monotonic()
    task.cancel()
    result = await task
    elapsed = time.monotonic() - start

    assert elapsed < 1.0  # NFR-003: returns well within 1 s of cancellation
    assert result.is_error is True
    assert result.content[0].text == delays.CANCEL_MESSAGE
    meta = _meta_of(result)
    assert meta["tool"] == "delay_cancel"
    assert "cancelled" in meta["note"].lower()


async def test_delay_cancel_branch_on_cancellation():
    """Run the coroutine as a real task, cancel it mid-wait, and assert it returns
    the cancellation result promptly (well under the 1 s NFR-003 budget) rather than
    propagating CancelledError. Uses a long wait so cancellation, not timeout, wins.
    """
    task = asyncio.create_task(delays._delay_cancel(wait_seconds=30))
    await asyncio.sleep(0.05)  # let the task reach the asyncio.sleep suspension point
    task.cancel()
    result = await task  # coroutine suppresses CancelledError and returns synchronously

    assert result.is_error is True
    assert result.content[0].text == delays.CANCEL_MESSAGE
