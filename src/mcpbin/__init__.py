"""mcpbin — a diagnostic test server for MCP clients (like httpbin for REST APIs).

This package provides a deterministic MCP server exposing documented, reproducible
endpoints so MCP *client* developers can validate protocol compliance.

Submodules (server, tools, resources, prompts, etc.) are added by later work
packages; this module intentionally exposes only the version string so that
``import mcpbin`` succeeds before those modules exist.
"""

__version__ = "0.1.3"

__all__ = ["__version__"]
