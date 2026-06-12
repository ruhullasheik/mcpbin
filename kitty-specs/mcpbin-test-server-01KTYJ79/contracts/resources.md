# Contract: Resource Catalog (FR-006)

**Mission**: mcpbin-test-server-01KTYJ79

Exercised via `resources/list` (paginated, page size 10) and `resources/read`.

## Static resources

| URI | name | mimeType | Read result |
|---|---|---|---|
| `mcpbin://text/plain` | Plain text | `text/plain` | Deterministic plain text. |
| `mcpbin://text/markdown` | Markdown | `text/markdown` | Deterministic markdown. |
| `mcpbin://blob/binary` | Binary blob | `application/octet-stream` | Valid base64 blob. |
| `mcpbin://large/paginated` (family) | Large list | `text/plain` | A large set (≥100 total resources) whose listing requires multiple `resources/list` cursor pages. |
| `mcpbin://missing` | Missing | — | Listed in `resources/list` but **always** returns a not-found error on read (simulates deleted/unavailable). |

## URI template

| Template | Valid ids | Read result |
|---|---|---|
| `mcpbin://dynamic/{id}` | `alpha`, `beta`, `gamma` | Each returns distinct short text naming the id. |
| `mcpbin://dynamic/{id}` | any other id | Not-found error (distinct from `mcpbin://missing`: the URI resolves but content does not exist). |

## Behaviors to assert

- `resources/list` returns all resources including the template entry and `mcpbin://missing`.
- Reading `mcpbin://missing` and an unknown `dynamic/{id}` both return not-found errors.
- The large paginated family forces >1 list page (SC-004); final page omits `nextCursor`.
- All read content is deterministic (NFR-001).
