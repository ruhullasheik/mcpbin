---
title: mcpbin
emoji: 🧪
colorFrom: green
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Test server for MCP clients — like httpbin for REST
---

# mcpbin — diagnostic MCP test server

This Space hosts **mcpbin** — like [httpbin](https://httpbin.org) for REST APIs, but a
deterministic test server for **Model Context Protocol (MCP) clients**. Point your client at
it to verify protocol compliance, validate error handling, and explore edge cases.

- **Web UI:** the Space's main URL (`https://<owner>-mcpbin.hf.space/`)
- **MCP endpoint (Streamable HTTP):** `https://<owner>-mcpbin.hf.space/mcp`

Targets MCP spec `2025-03-26`. Built on FastMCP. 42 tools, 124 resources, 5 prompts across
echo / response-types / errors / delays / schema / notifications / sampling / inspect.

> This is a public demo on the `full` profile. It is documentation + protocol exercise only;
> there is no "run tool" button in the UI.

See the [project repository](https://github.com/ruhullasheik/mcpbin) for the full client
test checklist and self-hosting options.
