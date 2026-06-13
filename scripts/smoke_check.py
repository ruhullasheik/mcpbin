#!/usr/bin/env python3
"""Live smoke check for a deployed (or local) mcpbin instance.

Verifies two things about a running mcpbin base URL:

  1. The web UI is served at ``GET /`` (HTTP 200 + app-shell marker).
  2. The MCP endpoint at ``POST /mcp`` answers a JSON-RPC ``initialize`` with a
     real MCP reply (JSON or SSE ``data:`` carrying JSON-RPC), i.e. it is wired
     up and not a 404/405.

Both checks are retried with backoff so a free-tier cold start (NFR-004) does
not produce a false failure. The script is **stdlib only** (``urllib``,
``json``, ``argparse``, ``time``) so it runs in any Python 3.12 environment
without installing anything.

Local usage
-----------
Start the server in one shell::

    uv run mcpbin --transport http        # binds 127.0.0.1:8000 by default

Then run the smoke check in another shell::

    uv run python scripts/smoke_check.py http://localhost:8000
    # -> both checks PASS, exit code 0

Against the deployed Space::

    python scripts/smoke_check.py https://<owner>-mcpbin.hf.space

Options::

    --timeout <seconds>   cold-start retry budget (default 30)
    --interval <seconds>  delay between retry attempts (default 2)

Exit code is ``0`` only if **both** checks pass; non-zero otherwise (so it is
usable directly as a CI / deploy gate step). A dead URL fails within roughly
``--timeout`` seconds rather than hanging.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

# JSON-RPC initialize handshake per the MCP spec (2025-03-26).
INIT_PAYLOAD = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "smoke", "version": "1"},
    },
}

# UI app-shell markers; either is sufficient to prove the reference UI is served.
UI_MARKERS = ('id="search"', "mcpbin")

# Per-request socket timeout. Kept small so a hung connection still leaves room
# for retries inside the overall --timeout budget.
REQUEST_TIMEOUT = 10


class StillWaking(Exception):
    """Transient condition (cold start / connection refused / 5xx) — retry."""


class CheckFailed(Exception):
    """Definitive failure (wrong content, 404/405) — endpoint is wrong, not asleep."""


def _read(resp):
    """Decode an HTTP response body to text."""
    raw = resp.read()
    charset = resp.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def check_ui(base_url):
    """Check 1 — GET <base>/ returns 200 and contains an app-shell marker.

    Returns a short detail string on success. Raises StillWaking for transient
    transport errors (so the caller retries) or CheckFailed for a definitively
    wrong response.
    """
    url = base_url + "/"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            status = resp.status
            body = _read(resp)
    except urllib.error.HTTPError as exc:
        # 5xx/503 => container still starting; other HTTP codes => wrong surface.
        if exc.code >= 500:
            raise StillWaking(f"HTTP {exc.code} from GET /") from exc
        raise CheckFailed(f"GET / returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise StillWaking(f"connection error on GET /: {exc}") from exc

    if status != 200:
        raise CheckFailed(f"GET / returned HTTP {status}")
    if not any(marker in body for marker in UI_MARKERS):
        raise CheckFailed("GET / 200 but no app-shell marker (id=\"search\"/mcpbin)")
    return f"HTTP 200, app-shell marker present ({url})"


def _extract_jsonrpc(content_type, body):
    """Return a parsed JSON-RPC object from a /mcp response body.

    Handles both ``application/json`` and SSE (``text/event-stream``), where the
    JSON-RPC payload rides on ``data:`` lines. Returns None if no JSON-RPC
    object can be recovered.
    """
    body = body.strip()
    if not body:
        return None

    is_sse = "text/event-stream" in (content_type or "").lower()
    if is_sse or body.startswith("data:") or "\ndata:" in body:
        # Concatenate the data payload(s) of SSE events and parse as JSON.
        data_lines = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())
        candidate = "".join(data_lines).strip()
        if candidate:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return None
        return None

    # Plain JSON body.
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def check_mcp(base_url):
    """Check 2 — POST <base>/mcp initialize gets a real MCP reply.

    Pass if status is 200 and the body parses as a JSON-RPC message (a
    ``result`` or even an ``error`` proves the endpoint is live). A 404/405 or
    non-JSON-RPC body is a definitive failure; connection errors / 5xx are
    treated as "still waking" so the caller retries.
    """
    url = base_url + "/mcp"
    data = json.dumps(INIT_PAYLOAD).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            body = _read(resp)
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 405):
            raise CheckFailed(f"POST /mcp returned HTTP {exc.code} (endpoint not wired)") from exc
        if exc.code >= 500:
            raise StillWaking(f"HTTP {exc.code} from POST /mcp") from exc
        raise CheckFailed(f"POST /mcp returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise StillWaking(f"connection error on POST /mcp: {exc}") from exc

    if status in (404, 405):
        raise CheckFailed(f"POST /mcp returned HTTP {status} (endpoint not wired)")
    if status != 200:
        raise CheckFailed(f"POST /mcp returned HTTP {status}")

    parsed = _extract_jsonrpc(content_type, body)
    if not isinstance(parsed, dict) or parsed.get("jsonrpc") != "2.0":
        raise CheckFailed("POST /mcp 200 but body is not a JSON-RPC reply")

    kind = "result" if "result" in parsed else ("error" if "error" in parsed else "reply")
    transport = "SSE" if "text/event-stream" in content_type.lower() else "JSON"
    return f"HTTP 200, JSON-RPC {kind} via {transport} ({url})"


def run_check(name, fn, base_url, deadline, interval):
    """Run one check, retrying transient failures until the deadline.

    Returns True (and prints a PASS line) on success, False (with a FAIL line)
    on a definitive failure or once the deadline is exceeded.
    """
    last_transient = None
    while True:
        try:
            detail = fn(base_url)
            print(f"PASS  {name}: {detail}")
            return True
        except CheckFailed as exc:
            print(f"FAIL  {name}: {exc}")
            return False
        except StillWaking as exc:
            last_transient = exc
            if time.monotonic() >= deadline:
                print(f"FAIL  {name}: timed out waiting for server ({exc})")
                return False
            remaining = deadline - time.monotonic()
            sleep_for = min(interval, max(0.0, remaining))
            print(f"...   {name}: still waking ({exc}); retrying in {sleep_for:.0f}s")
            time.sleep(sleep_for)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Live smoke check for a deployed mcpbin instance (UI + /mcp).",
    )
    parser.add_argument(
        "base_url",
        help="Base URL of the instance, e.g. https://owner-mcpbin.hf.space or http://localhost:8000",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30,
        help="Cold-start retry budget in seconds (default: 30)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2,
        help="Delay between retry attempts in seconds (default: 2)",
    )
    args = parser.parse_args(argv)

    base_url = args.base_url.rstrip("/")
    deadline = time.monotonic() + args.timeout

    print(f"Smoke checking {base_url} (timeout {args.timeout:.0f}s, interval {args.interval:.0f}s)")

    ui_ok = run_check("UI   (GET /)", check_ui, base_url, deadline, args.interval)
    mcp_ok = run_check("MCP  (POST /mcp)", check_mcp, base_url, deadline, args.interval)

    if ui_ok and mcp_ok:
        print("RESULT: PASS — both checks succeeded")
        return 0
    print("RESULT: FAIL — see check lines above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
