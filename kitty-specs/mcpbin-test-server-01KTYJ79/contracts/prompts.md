# Contract: Prompt Catalog (FR-007)

**Mission**: mcpbin-test-server-01KTYJ79

Exercised via `prompts/list` (paginated, page size 10) and `prompts/get`.

| Prompt | description | arguments | messages |
|---|---|---|---|
| `simple` | present | none | single `user` message. |
| `with_args` | present | `topic` (required), `tone` (optional) | message(s) interpolating the args. |
| `multi_turn` | present | none | alternating `user` / `assistant` messages (≥2 turns). |
| `with_embedded_resource` | present | none | a message whose content includes an embedded `resource` block. |
| `no_description` | **absent** (no `description` field in listing) | none | single `user` message. |

## Behaviors to assert

- `prompts/list` returns all prompts; `no_description` has no `description` field.
- `with_args` includes provided required + optional argument values in the returned messages.
- `multi_turn` returns alternating user/assistant roles.
- `with_embedded_resource` returns a message containing an embedded resource content block.

> **Open (research R11)**: only 5 documented prompt shapes exist. Reaching the PRD's
> "50+ prompts" pagination target without synthetic padding is flagged for the tasks phase —
> either accept fewer prompt pages or add genuinely distinct documented prompt variants.
