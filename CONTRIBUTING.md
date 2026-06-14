# Contributing to mcpbin

Thanks for your interest in improving **mcpbin** — a diagnostic test server for Model
Context Protocol (MCP) clients. Contributions of all kinds are welcome: bug fixes, new
diagnostic tools/resources/prompts, docs, and the reference UI.

## Ways to contribute

- **Report a bug** or **request a feature** via the issue templates.
- **Open a pull request** for a fix or enhancement.

## Development setup

mcpbin uses [`uv`](https://docs.astral.sh/uv/) (Python 3.12+). FastMCP is the only runtime
dependency.

```bash
git clone https://github.com/<your-fork>/mcpbin
cd mcpbin
uv sync                         # install deps from the committed lockfile
uv run pytest                   # run the full test suite (must pass)
uv run mcpbin --transport http  # serve UI at http://localhost:8000/ , MCP at /mcp
```

Quick local verification of a running server:

```bash
python scripts/smoke_check.py http://localhost:8000
```

## Pull request flow

1. **Fork** the repo and create a branch off `main`.
2. Make your change. **Add or update tests** — this project keeps a green suite.
3. Run `uv run pytest` locally; keep it passing.
4. Open a PR against **`main`**. CI runs the test suite on every PR; it must be green to merge.
5. Keep PRs small and focused; describe the change and link any related issue.

### Conventions

- **Runtime dependencies:** FastMCP only. Don't add third-party runtime deps (dev/test deps
  are fine). If you change dependencies, run `uv lock` and commit `uv.lock`.
- **Tests:** every tool/resource/prompt should have a test exercising it through the
  in-memory client (see `tests/`).
- **Determinism:** tool responses must be reproducible (no randomness/timestamps in outputs
  except documented dynamic fields like `requestCount`).
- **`_meta`:** every tool result carries the fixed `_meta` block — preserve that contract.
- Commit messages: a short imperative summary (≤~60 chars) is appreciated.

### Adding a new tool / feature area

Tool modules live in `src/mcpbin/tools/<area>.py` and expose `register(app, profile, ctx)`;
they're auto-discovered by `registry.py`. Resources and prompts live in
`src/mcpbin/resources.py` / `src/mcpbin/prompts.py`. Add a matching test module under `tests/`.

## Things contributors can ignore

- **Spec Kitty** (`kitty-specs/`, `.kittify/`) is the maintainer's internal planning tool.
  You don't need it to contribute — a normal fork-and-PR works fine.
- **Versioning & releases** are handled by the maintainer (version bump + `v*` tag). Please
  don't bump the version or edit release/deploy workflows in feature PRs.
- The **Hugging Face Space** repo is managed automatically by CI on release — don't edit it.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating you
agree to uphold it.
