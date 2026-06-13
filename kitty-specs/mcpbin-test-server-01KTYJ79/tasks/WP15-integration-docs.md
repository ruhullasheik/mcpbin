---
work_package_id: WP15
title: Integration, validation & docs
dependencies:
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
- WP10
- WP11
- WP12
- WP13
- WP14
requirement_refs:
- FR-008
- FR-011
- FR-013
- FR-016
- FR-017
- FR-018
- NFR-001
- NFR-006
planning_base_branch: devs/ruhulla
merge_target_branch: devs/ruhulla
branch_strategy: Planning artifacts for this feature were generated on devs/ruhulla. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into devs/ruhulla unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mcpbin-test-server-01KTYJ79
base_commit: fd17b7d7cdf627547a3896eb7041016a97e887f9
created_at: '2026-06-13T07:06:23.828193+00:00'
subtasks:
- T056
- T057
- T058
- T059
- T060
shell_pid: '16080'
history:
- date: '2026-06-12'
  author: tasks
  action: created
authoritative_surface: tests/test_integration.py
execution_mode: code_change
owned_files:
- README.md
- tests/test_meta_contract.py
- tests/test_pagination.py
- tests/test_profiles.py
- tests/test_integration.py
tags: []
---

# WP15 — Integration, validation & docs

## Objective

Close the mission with cross-cutting validation that only makes sense once all feature areas
exist — every tool result carries a valid `_meta`; pagination produces multiple pages with an
absent final cursor and `-32602` on bad cursors across all three list methods; all four
profiles gate capabilities correctly; the real catalog reaches pagination thresholds — and
write the README test checklist (FR-017).

## Context
- Depends on **all** feature WPs (WP04–WP14). Uses conftest fixtures from WP03.
- Seeds README from [../quickstart.md](../quickstart.md). Resolves the research **R11**
  catalog-sizing decision.

## Implement command
```bash
spec-kitty agent action implement WP15 --agent <name>
```

## Subtasks

### T056 — `tests/test_meta_contract.py` (FR-013, NFR-006)
- Enumerate every registered tool; call each with minimal valid args; assert the result carries
  a `_meta` matching `contracts/meta-schema.json` (keys `tool`/`received`/`note`, correct
  `tool` name), **including** `isError` results and `return_empty`.
- Assert every tool has a non-empty `description` (NFR-006).

### T057 — `tests/test_pagination.py` (FR-008, SC-004)
- For `tools/list`, `resources/list`, `prompts/list`: follow cursors and assert >1 page where
  the catalog exceeds 10; each non-final page has an opaque `nextCursor`; the **final page omits
  `nextCursor`** (absent, not null/empty); an invalid cursor → `-32602` `"invalid or expired
  cursor"`.
- Resources must span multiple pages (≥100). Document the tools/prompts page outcome.

### T058 — `tests/test_profiles.py` (FR-011)
- For each profile build a client and assert advertised capabilities + gating:
  `full` advertises all; `tools-only` → `resources/list`/`prompts/list` raise `-32601`;
  `no-sampling` → non-sampling ops work and `sampling_*` degrade; `minimal` → tools only, **no
  `listChanged`** advertised, list methods for omitted caps `-32601`.

### T059 — `tests/test_integration.py` (FR-018, NFR-001, R11)
- Assert catalog sizing: tool count, resource count (≥100), prompt count; document that
  pagination is exercised by the real catalog (no synthetic padding, FR-018).
- Determinism spot-check: call a couple of deterministic tools twice and assert identical
  results except dynamic fields (`requestCount`) (NFR-001).
- **R11 decision gate**: if the stakeholder requires a hard "50+ tools / 50+ prompts", this is
  where the shortfall surfaces — either accept the documented page counts or coordinate adding
  real variants in the relevant feature WP. Record the decision in the PR.

### T060 — `README.md` (FR-017)
- Test checklist: the list of calls a compliant client should make (derive from
  `quickstart.md`'s 13 scenarios). Run instructions (`uv run mcpbin`, `--transport`,
  `--profile`), Docker build/run, and a pointer to the reference UI. Mention structured stderr
  logging (FR-016).

## Branch Strategy
Planning/base **devs/ruhulla**; merge target **devs/ruhulla**; worktree per lane (this is the
join lane; depends on all feature lanes).

## Definition of Done
- [ ] `uv run pytest` (full suite) is green.
- [ ] Every tool result has a schema-valid `_meta`; every tool has a description.
- [ ] Pagination multipage + absent final cursor + `-32602` verified for all three list methods.
- [ ] All four profiles' capability gating verified.
- [ ] Catalog sizing asserted; R11 decision recorded.
- [ ] README test checklist complete (FR-017).
- [ ] No files outside `owned_files` modified.

## Risks & reviewer guidance
- This WP is the integration truth test — if a feature WP cut a corner, it surfaces here.
  Reviewer: ensure failures are fixed in the owning feature WP, not patched around in
  integration tests.
- The R11 sizing tension must be explicitly resolved (accept documented pages, or add real
  variants) — do not silently pad.
