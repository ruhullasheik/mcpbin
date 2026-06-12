# Phase 0 Research: mcpbin

**Mission**: mcpbin-test-server-01KTYJ79 · **Date**: 2026-06-12

Each unknown from `plan.md` Phase 0 is resolved below as Decision / Rationale /
Alternatives. Items where FastMCP's exact surface must be confirmed against the
installed version are marked **⚠ verify-on-impl** — the first implementation work
package pins the FastMCP version in `uv.lock` and confirms these against that version.

---

## R1. Transport selection (FR-014, C-005)

- **Decision**: Single Typer/argparse-driven `main()` in `server.py` builds one `FastMCP`
  app and runs it with the transport chosen by `--transport {stdio,sse,http}` (default
  `stdio`). FastMCP's `app.run(transport=...)` selects stdio, SSE, or Streamable HTTP.
- **Rationale**: PRD requires one binary, one flag (FR-014). FastMCP natively supports all
  three transports via its run API, so no custom transport code is needed.
- **Alternatives**: Separate entry points per transport (rejected — violates "single binary");
  hand-rolling SSE/HTTP with a raw ASGI server (rejected — reimplements FastMCP).
- **⚠ verify-on-impl**: exact transport keyword strings (`"sse"` vs `"http"` vs
  `"streamable-http"`) and how the HTTP transports also mount the static frontend at `/`.

## R2. Per-profile capability gating → `-32601` (FR-011)

- **Decision**: `profiles.py` defines four profiles as capability sets. `server.py` registers
  only the tools/resources/prompts a profile includes, and for omitted *capabilities* installs
  handlers for the corresponding list methods (`resources/list`, `prompts/list`, etc.) that
  raise a JSON-RPC `-32601` method-not-found. `minimal` additionally omits `listChanged` from
  advertised capabilities.
- **Rationale**: Spec FR-011 + acceptance require `-32601` (not empty list) for omitted
  capabilities. Capability advertisement at `initialize` must reflect the active profile.
- **Alternatives**: Always register everything and filter at call time (rejected — would still
  advertise the capability); returning empty lists (rejected — explicitly forbidden by spec).
- **⚠ verify-on-impl**: how FastMCP lets us (a) control advertised capabilities at `initialize`
  and (b) override/disable a built-in list handler to raise `-32601`. If FastMCP auto-registers
  list handlers, we may need a low-level handler override or a thin protocol shim.

## R3. Opaque cursor pagination → `-32602` on bad cursor (FR-008)

- **Decision**: `pagination.py` provides `encode_cursor(offset) -> str` (base64 of an opaque
  token) and `decode_cursor(str) -> int` that raises a `-32602` "invalid or expired cursor" on
  malformed/out-of-range input. List handlers slice the catalog at page size 10 and omit
  `nextCursor` entirely on the final page (not null/empty).
- **Rationale**: Spec mandates opaque base64 cursors, page size 10, absent final `nextCursor`,
  and the exact `-32602` message. Implementing the cursor codec ourselves guarantees these
  byte-level semantics regardless of FastMCP defaults.
- **Alternatives**: Rely on FastMCP's built-in pagination (rejected unless it already produces
  exactly this behavior — verify); cursor = raw offset string (rejected — must be opaque).
- **⚠ verify-on-impl**: whether FastMCP paginates `tools/list` automatically and whether we can
  inject our cursor codec, or must override the list handlers at the protocol layer. Catalog
  size must force >1 page (page 10 vs ≥50 tools / ≥100 resources / ≥50 prompts).

## R4. Raw JSON-RPC error codes from tools (FR-003)

- **Decision**: `errors.py` centralizes the standard codes. `error_invalid_request/-method_
  not_found/-invalid_params/-internal` raise JSON-RPC errors with the documented codes;
  `error_unknown_code` uses a non-standard code outside `-32700…-32603`; `error_tool_level`
  returns a normal result with `isError: true`; `error_parse` returns a *simulated* well-formed
  `-32700` object as text content (a real parse error happens before routing) with a
  `_meta.note` explaining the simulation. Every error tool still emits `_meta` with raw input.
- **Rationale**: Directly mirrors the PRD error table and the spec's `error_parse` clarification.
- **Alternatives**: Map all errors to tool-level `isError` (rejected — must distinguish protocol
  vs tool errors per scenario 3).
- **⚠ verify-on-impl**: FastMCP's mechanism to raise a protocol-level JSON-RPC error with a
  chosen code from inside a tool (e.g. a `ToolError`/`McpError` carrying `code`), vs. needing a
  low-level error-raising path.

## R5. `_meta` envelope on every result, incl. empty (FR-013, FR-002)

- **Decision**: `_meta.py:build_meta(tool, received, note)` returns the fixed
  `{tool, received, note}` object, appended as the **final text content block** of every tool
  result. For `return_empty`, "empty" means no *substantive* content blocks; the `_meta`
  documentation block is still present (resolves the spec's flagged assumption). If — and only
  if — FastMCP supports a result-level `_meta`/metadata field separate from content, prefer that
  channel so `return_empty` can have truly zero content blocks; otherwise use the trailing text
  block uniformly.
- **Rationale**: Spec requires `_meta` on *every* result including `isError` and empty, with a
  fixed schema. A uniform helper guarantees the contract and is independently testable
  (`test_meta_contract.py`).
- **Alternatives**: Per-tool ad-hoc meta (rejected — drift risk); skipping meta on empty
  (rejected — violates FR-013).
- **⚠ verify-on-impl**: whether the MCP result object exposes a `_meta` field in spec 2025-03-26
  that FastMCP surfaces; decides the `return_empty` representation.

## R6. Cancellation for `delay_cancel` (FR-004, NFR-003)

- **Decision**: `delay_cancel` runs an async wait up to 60 s inside a structure that observes
  `notifications/cancelled` for the in-flight request; on cancellation it returns within 1 s with
  `isError: true`, message `"cancelled by client"`, and `_meta` reporting `cancelled`. On timeout
  it returns a normal result with `_meta` reporting `completed`.
- **Rationale**: NFR-003 requires <1 s reaction; scenario 4 fixes the message. Cooperative async
  cancellation via the request's cancellation signal is the standard MCP approach.
- **Alternatives**: Polling a shared flag (acceptable fallback); hard task kill (rejected — can't
  emit the required `isError` result).
- **⚠ verify-on-impl**: how FastMCP exposes the per-request cancellation signal (Context method,
  `asyncio.CancelledError`, or a cancel scope).

## R7. Server→client notifications, progress, log levels (FR-009)

- **Decision**: Notification tools use the FastMCP request **Context** to emit
  `notifications/resources/updated`, `.../resources/list_changed`, `.../prompts/list_changed`,
  `.../tools/list_changed`, a sequence of ≥3 `notifications/progress`, and `notifications/message`
  logs at debug/info/warning/error.
- **Rationale**: FastMCP's Context provides progress reporting and logging helpers and access to
  the session for sending notifications. Scenario 9 fixes the ≥3 progress / all-levels minimums.
- **Alternatives**: Raw session writes (acceptable if Context lacks a specific helper).
- **⚠ verify-on-impl**: exact Context API names for `report_progress`, `log`/`debug/info/warning/
  error`, and list-changed/resource-updated notifications.

## R8. Sampling round-trip + graceful degradation (FR-010)

- **Decision**: Sampling tools call the client back via Context's `sample()`/`create_message`
  with optional `systemPrompt` and `maxTokens`. `sampling_unsupported` (and all sampling tools
  under a profile/client without sampling) detect the missing capability and return a graceful
  `isError` result rather than throwing.
- **Rationale**: Scenario 10 + FR-010. Sampling is client-initiated capability; must degrade
  cleanly when absent (also the `no-sampling`/`tools-only`/`minimal` profile case + `sampling_
  unsupported`).
- **Alternatives**: Hard error on missing capability (rejected — spec wants *graceful*).
- **⚠ verify-on-impl**: Context sampling method signature and how to detect client sampling
  capability at call time.

## R9. Session `requestCount` (FR-012)

- **Decision**: `session.py` holds per-connection state (request count, negotiated capabilities,
  transport name) keyed by the FastMCP session; `inspect_session` reads it and the count
  increments on each request within a session, deterministic per-session but excluded from
  reproducibility checks (NFR-001).
- **Rationale**: Scenario 12 requires `requestCount` to increment across calls in one session.
- **Alternatives**: Global counter (rejected — must be per-session).
- **⚠ verify-on-impl**: how FastMCP identifies a session and exposes per-session storage and the
  negotiated capabilities/`clientInfo`/`protocolVersion` for `inspect_session`.

## R10. Deterministic tiny PNG for `return_image` (FR-002)

- **Decision**: Ship a fixed, tiny (e.g. 1×1 or small solid) PNG at
  `src/mcpbin/assets/test.png`, base64-encode it at runtime, and return it with
  `mimeType: "image/png"`. The bytes are committed, so the base64 is byte-for-byte reproducible.
- **Rationale**: NFR-001 determinism + scenario 2 "decodable base64 PNG". A committed asset is
  simpler and more reproducible than generating one at runtime.
- **Alternatives**: Generate via Pillow (rejected — adds a dependency, violates C-003
  "FastMCP only").

## R11. Catalog sizing reaches pagination thresholds (FR-018)

- **Decision**: Count real feature tools; pad **resources** (not tools) to ≥100 via the
  `mcpbin://large/paginated` family which is legitimately a "large resource list" per PRD, and
  ensure ≥50 real prompts shapes by enumerating documented variants. Tools: the PRD's echo(7) +
  response_types(6) + errors(7) + delays(5) + schema(6) + notifications(6) + sampling(4) +
  inspect(1) = **42** named tools — **below 50**.
- **Finding/Decision**: 42 < 50, so reaching ">50 tools, page size 10, multiple pages" needs
  either (a) the spec's FR-018 "no synthetic padding" honored by counting only real tools and
  accepting 42 (still 5 pages at size 10 → pagination is still exercised), or (b) adding
  genuinely useful tool variants. **Resolution**: page size 10 over 42 tools already yields 5
  pages, satisfying "requires multiple pages" (SC-004) without padding. The PRD's "50+" is a
  target, not a hard floor; FR-018 forbids *synthetic padding*. We keep 42 real tools and note
  the 5-page outcome. Resources still target ≥100 via the legitimately-large paginated resource
  list; prompts: the 5 documented shapes are few, so prompt pagination is exercised by the
  large resource list and tool list — **flag for tasks**: if prompt-list pagination must be
  demonstrated, add documented prompt variants rather than padding.
- **⚠ open for tasks**: confirm with stakeholder whether 42 tools (5 pages) satisfies the
  "50+ tools" target or whether to add real tool variants; and how to reach "50+ prompts"
  without synthetic padding given only 5 documented prompt shapes. *(This is the one substantive
  PRD-vs-spec tension; surfaced now, decided at task time.)*

---

## Summary of decisions

| # | Area | Decision | Needs impl-time verify |
|---|---|---|---|
| R1 | Transport | one app, `--transport` → `app.run(transport=...)` | transport keyword strings |
| R2 | Profiles | register subset + `-32601` handlers for omitted caps | capability advertisement + handler override |
| R3 | Pagination | own base64 cursor codec, page 10, absent final nextCursor | FastMCP list-handler injection |
| R4 | Errors | central codes; simulated `error_parse` | raising coded JSON-RPC errors from tools |
| R5 | `_meta` | uniform trailing block; prefer result-level `_meta` if available | result `_meta` field support |
| R6 | Cancel | cooperative async, <1 s, fixed message | cancellation signal API |
| R7 | Notifications | via Context helpers, ≥3 progress, all log levels | Context method names |
| R8 | Sampling | Context sampling + graceful degrade | sampling API + capability detection |
| R9 | Session | per-session `requestCount` store | session identity/storage |
| R10 | Image | committed tiny PNG, base64 at runtime | none |
| R11 | Catalog | 42 real tools = 5 pages; resources ≥100; **prompt/tool target tension flagged** | stakeholder decision at tasks |
