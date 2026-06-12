# Phase 1 Data Model: mcpbin

**Mission**: mcpbin-test-server-01KTYJ79 · **Date**: 2026-06-12

mcpbin has no persistent storage. "Entities" here are the in-memory/runtime shapes that
define behavior. Validation rules are drawn from the spec's FRs/NFRs.

---

## Entity: `_meta` block (FR-013)

The fixed documentation envelope appended as the final text content block of **every** tool
result (including `isError` and empty results).

| Field | Type | Rules |
|---|---|---|
| `tool` | string | Name of the called tool. Required, non-empty. |
| `received` | object | Exact raw parsed arguments as the server received them — even when the tool ignores them (error tools). May be `{}` for no-arg tools. |
| `note` | string | One human-readable sentence explaining the response; references an MCP spec section where relevant. |

Invariant: schema is identical across all tools. Tested by `test_meta_contract.py`.
See `contracts/meta-schema.json`.

---

## Entity: Tool

A named, schema-bearing callable returning MCP content blocks + a `_meta` block.

| Field | Type | Rules |
|---|---|---|
| `name` | string | Unique across the catalog. |
| `description` | string | Non-empty; states what it does and what to expect (FR-016, NFR-006). |
| `inputSchema` | JSON Schema | Per feature area; `schema_no_args` has none. |
| `feature_area` | enum | echo · response_types · errors · delays · schema · notifications · sampling · inspect. Drives UI grouping (FR-015). |
| result | MCP result | Content blocks (text/image/resource/empty) + trailing `_meta`; may set `isError`. |

Catalog (42 named tools): echo(7), response_types(6), errors(7), delays(5), schema(6),
notifications(6), sampling(4), inspect(1). See `contracts/tools.md`.

**Profile visibility**: a tool is registered only if its feature area is enabled by the
active profile (sampling tools absent under `tools-only`/`no-sampling`/`minimal`).

---

## Entity: Resource (FR-006)

Addressable item returning text/markdown/binary content; some intentionally not-found.

| Field | Type | Rules |
|---|---|---|
| `uri` | string / URI template | e.g. `mcpbin://text/plain`, template `mcpbin://dynamic/{id}`. |
| `name` | string | Required. |
| `description` | string | Non-empty (NFR-006). |
| `mimeType` | string | e.g. `text/plain`, `text/markdown`, `application/octet-stream`. |
| `content` | text or base64 blob | Deterministic (NFR-001). |
| `state` | enum | present · missing (`mcpbin://missing` always not-found) · template. |

Template rule: `mcpbin://dynamic/{id}` resolves for `id ∈ {alpha, beta, gamma}` (distinct
text), else not-found — distinct from `mcpbin://missing` (URI resolves, content absent).
Catalog targets ≥100 resources (large paginated list) to force pagination. See
`contracts/resources.md`.

---

## Entity: Prompt (FR-007)

Named message template producing user/assistant messages.

| Field | Type | Rules |
|---|---|---|
| `name` | string | Unique. |
| `description` | string \| absent | `no_description` omits it entirely from the listing. |
| `arguments` | list[{name, required, description}] | `with_args` has required + optional. |
| `messages` | list[{role, content}] | `multi_turn` alternates user/assistant; `with_embedded_resource` includes a resource content block. |

Shapes: simple · with_args · multi_turn · with_embedded_resource · no_description. See
`contracts/prompts.md`.

---

## Entity: Profile (FR-011)

Named capability subset advertised at `initialize`.

| Profile | tools | resources | prompts | sampling | pagination/listChanged |
|---|---|---|---|---|---|
| `full` (default) | ✓ | ✓ | ✓ | ✓ | ✓ |
| `tools-only` | ✓ | ✗ → `-32601` | ✗ → `-32601` | ✗ | ✓ |
| `no-sampling` | ✓ | ✓ | ✓ | ✗ (sampling tools degrade) | ✓ |
| `minimal` | ✓ | ✗ → `-32601` | ✗ → `-32601` | ✗ | ✗ (no `listChanged`) |

Rule: omitted capability → its list method returns JSON-RPC `-32601`, never an empty list.

---

## Entity: Session (FR-012)

Per-connection in-memory state.

| Field | Type | Rules |
|---|---|---|
| `protocolVersion` | string | `2025-03-26` (C-005). |
| `clientInfo` | {name, version} | From `initialize`. |
| `negotiatedCapabilities` | object | Result of profile ∩ client capabilities. |
| `transport` | enum | `stdio` \| `sse` \| `http`. |
| `requestCount` | int | Increments per request in this session; excluded from reproducibility (NFR-001). |

Surfaced by `inspect_session`.

---

## Entity: Cursor (FR-008)

Opaque pagination token.

| Field | Type | Rules |
|---|---|---|
| value | base64 string | Clients must not parse/construct. Encodes an internal offset. |
| invalid → | error | Malformed/expired → JSON-RPC `-32602`, message `"invalid or expired cursor"`. |
| final page | — | `nextCursor` field **absent** (not null/empty). |

Page size = 10 for `tools/list`, `resources/list`, `prompts/list`.

---

## Relationships

- A **Profile** gates which **Tool**/**Resource**/**Prompt** entities are registered and which
  capabilities are advertised on a **Session**.
- Every **Tool** result embeds one **`_meta` block**.
- **Cursor** governs paged listing of **Tool**, **Resource**, and **Prompt** collections.
- A **Session** carries the negotiated capabilities derived from its **Profile** and the
  client's declared capabilities (affects sampling availability).
