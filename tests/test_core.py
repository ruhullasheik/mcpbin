"""WP02 — core protocol primitives unit tests (T013).

Covers: cursor codec round-trip + error semantics, pagination page size / final-page
omission, the four capability profiles, the ``_meta`` envelope against
``contracts/meta-schema.json``, and per-session request counting + isolation.

These are pure-Python tests; only ``pagination``/``errors`` touch the MCP error type.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp import McpError

from mcpbin import _meta as meta_mod
from mcpbin import errors, pagination, profiles
from mcpbin.session import SessionState, SessionStore


# --------------------------------------------------------------------------- #
# Locate the contract schema (shared kitty-specs artifact).
# --------------------------------------------------------------------------- #
def _find_meta_schema() -> dict:
    here = Path(__file__).resolve()
    rel = Path(
        "kitty-specs/mcpbin-test-server-01KTYJ79/contracts/meta-schema.json"
    )
    for parent in here.parents:
        candidate = parent / rel
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"could not locate {rel} above {here}")


META_SCHEMA = _find_meta_schema()


# --------------------------------------------------------------------------- #
# Cursor codec (FR-008)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("offset", [0, 1, 9, 10, 11, 100, 1000])
def test_cursor_round_trip(offset):
    encoded = pagination.encode_cursor(offset)
    assert isinstance(encoded, str)
    # Opaque: the raw offset string must not be plainly visible.
    assert str(offset) not in encoded or offset == 0  # base64 hides it
    assert pagination.decode_cursor(encoded) == offset


def test_decode_cursor_none_is_zero():
    assert pagination.decode_cursor(None) == 0


@pytest.mark.parametrize(
    "garbage",
    [
        "not-base64!!!",
        "",
        "Zm9vOmJhcg==",          # valid base64 but wrong prefix ("foo:bar")
        pagination.base64.urlsafe_b64encode(b"offset:-5").decode(),  # negative
        pagination.base64.urlsafe_b64encode(b"offset:abc").decode(),  # non-int
        pagination.base64.urlsafe_b64encode(b"offset:").decode(),     # empty int
    ],
)
def test_decode_cursor_garbage_raises_invalid_params(garbage):
    with pytest.raises(McpError) as excinfo:
        pagination.decode_cursor(garbage)
    err = excinfo.value.error
    assert err.code == errors.INVALID_PARAMS == -32602
    assert err.message == errors.INVALID_CURSOR_MESSAGE == "invalid or expired cursor"


# --------------------------------------------------------------------------- #
# Pagination (FR-008)
# --------------------------------------------------------------------------- #
def test_paginate_page_size_ten_and_next_cursor():
    items = list(range(25))  # 3 pages: 10, 10, 5
    page1, next1 = pagination.paginate(items, None)
    assert page1 == list(range(0, 10))
    assert next1 is not None

    page2, next2 = pagination.paginate(items, next1)
    assert page2 == list(range(10, 20))
    assert next2 is not None

    page3, next3 = pagination.paginate(items, next2)
    assert page3 == list(range(20, 25))
    # Final page omits nextCursor entirely.
    assert next3 is None


def test_paginate_exact_multiple_final_page_has_no_next():
    items = list(range(20))  # exactly 2 full pages
    _, next1 = pagination.paginate(items, None)
    page2, next2 = pagination.paginate(items, next1)
    assert page2 == list(range(10, 20))
    assert next2 is None


def test_paginate_empty_catalog():
    page, nxt = pagination.paginate([], None)
    assert page == []
    assert nxt is None


def test_paginate_out_of_range_cursor_raises():
    items = list(range(5))
    bad = pagination.encode_cursor(50)
    with pytest.raises(McpError) as excinfo:
        pagination.paginate(items, bad)
    assert excinfo.value.error.code == -32602
    assert excinfo.value.error.message == "invalid or expired cursor"


# --------------------------------------------------------------------------- #
# Profiles matrix (FR-011)
# --------------------------------------------------------------------------- #
# Expected matrix straight from data-model.md:
#                tools  resources prompts sampling pagination list_changed
_EXPECTED = {
    "full":        (True,  True,  True,  True,  True,  True),
    "tools-only":  (True,  False, False, False, True,  True),
    "no-sampling": (True,  True,  True,  False, True,  True),
    "minimal":     (True,  False, False, False, False, False),
}


@pytest.mark.parametrize("name,expected", _EXPECTED.items())
def test_profile_matrix(name, expected):
    p = profiles.get_profile(name)
    actual = (
        p.tools,
        p.resources,
        p.prompts,
        p.sampling,
        p.pagination,
        p.list_changed,
    )
    assert actual == expected
    assert p.name == name


def test_profile_has_predicate():
    full = profiles.get_profile("full")
    assert full.has("sampling") is True
    minimal = profiles.get_profile("minimal")
    assert minimal.has("sampling") is False
    assert minimal.has("list_changed") is False
    # Unknown capability -> False, not an error.
    assert minimal.has("nonexistent") is False


def test_profile_default_is_full():
    assert profiles.get_profile().name == "full"
    assert profiles.get_profile(None).name == "full"


def test_profile_unknown_name_raises():
    with pytest.raises(ValueError):
        profiles.get_profile("bogus")


# --------------------------------------------------------------------------- #
# _meta envelope (FR-013) — validate against contracts/meta-schema.json
# --------------------------------------------------------------------------- #
def _assert_matches_meta_schema(obj: dict) -> None:
    """Dependency-free structural check against the contract schema."""
    assert isinstance(obj, dict)
    for key in META_SCHEMA["required"]:
        assert key in obj, f"missing required key {key!r}"
    props = META_SCHEMA["properties"]
    type_map = {"string": str, "object": dict}
    for key, spec in props.items():
        if key not in obj:
            continue
        py_type = type_map[spec["type"]]
        assert isinstance(obj[key], py_type), f"{key} must be {spec['type']}"
        if spec.get("minLength"):
            assert len(obj[key]) >= spec["minLength"], f"{key} too short"


def test_build_meta_matches_schema():
    m = meta_mod.build_meta(
        tool="echo",
        received={"message": "hi"},
        note="Echoes the message back per the echo feature area.",
    )
    assert set(m.keys()) == {"tool", "received", "note"}
    _assert_matches_meta_schema(m)


def test_build_meta_no_arg_tool_received_empty_object():
    m = meta_mod.build_meta(
        tool="schema_no_args",
        received={},
        note="No-arg tool; received is the empty object.",
    )
    assert m["received"] == {}
    _assert_matches_meta_schema(m)


def test_append_meta_adds_final_text_block():
    content = [{"type": "text", "text": "hello"}]
    m = meta_mod.build_meta("echo", {"x": 1}, "note here")
    out = meta_mod.append_meta(content, m)
    # original untouched
    assert content == [{"type": "text", "text": "hello"}]
    # appended as the final block, JSON-encoded text of {"_meta": {...}}
    assert len(out) == 2
    final = out[-1]
    assert final["type"] == "text"
    decoded = json.loads(final["text"])
    assert decoded == {"_meta": m}


def test_append_meta_on_empty_content():
    m = meta_mod.build_meta("return_empty", {}, "Empty result still carries _meta.")
    out = meta_mod.append_meta([], m)
    assert len(out) == 1
    assert json.loads(out[0]["text"]) == {"_meta": m}


# --------------------------------------------------------------------------- #
# Errors helpers (FR-003)
# --------------------------------------------------------------------------- #
def test_mcp_error_carries_code():
    err = errors.mcp_error(errors.METHOD_NOT_FOUND, "nope")
    assert isinstance(err, McpError)
    assert err.error.code == -32601
    assert err.error.message == "nope"


def test_build_jsonrpc_error_dict():
    e = errors.build_jsonrpc_error(errors.PARSE_ERROR, "Parse error")
    assert e == {"code": -32700, "message": "Parse error"}
    e2 = errors.build_jsonrpc_error(-32700, "Parse error", data={"detail": "x"})
    assert e2["data"] == {"detail": "x"}


def test_error_constants():
    assert errors.PARSE_ERROR == -32700
    assert errors.INVALID_REQUEST == -32600
    assert errors.METHOD_NOT_FOUND == -32601
    assert errors.INVALID_PARAMS == -32602
    assert errors.INTERNAL_ERROR == -32603


# --------------------------------------------------------------------------- #
# Session (FR-012)
# --------------------------------------------------------------------------- #
def test_session_increment_raises_count():
    store = SessionStore()
    assert store.increment("s1") == 1
    assert store.increment("s1") == 2
    assert store.increment("s1") == 3
    assert store.get_or_create("s1").request_count == 3


def test_session_isolation():
    store = SessionStore()
    store.increment("a")
    store.increment("a")
    store.increment("b")
    assert store.get_or_create("a").request_count == 2
    assert store.get_or_create("b").request_count == 1
    assert "a" in store and "b" in store
    assert len(store) == 2


def test_session_state_defaults():
    s = SessionState()
    assert s.protocol_version == "2025-03-26"
    assert s.request_count == 0
    assert s.negotiated_capabilities == {}
    assert s.transport is None
    assert s.client_info is None


def test_get_or_create_returns_same_instance():
    store = SessionStore()
    first = store.get_or_create("x")
    first.transport = "stdio"
    again = store.get_or_create("x")
    assert again is first
    assert again.transport == "stdio"
