"""MCP prompts (FR-007): every prompt shape a client should handle.

Registered via the :func:`register` contract and discovered by
:func:`mcpbin.registry.register_all` (guarded ``mcpbin.prompts`` import). Under
profiles that omit ``prompts`` the registry never calls this module.

Shapes (see ``contracts/prompts.md``):

* ``simple``                 – single user message, no arguments.
* ``with_args``              – required ``topic`` + optional ``tone``; both appear in
  the produced message.
* ``multi_turn``             – alternating user/assistant messages.
* ``with_embedded_resource`` – a message whose content embeds a resource block.
* ``no_description``         – registered with **no** description (absent in
  ``prompts/list``, not an empty string). The function intentionally has no docstring
  and no ``description=`` so fastmcp leaves ``description`` unset.
"""

from __future__ import annotations

from typing import Any

from fastmcp.prompts import Message
from mcp.types import EmbeddedResource, TextContent, TextResourceContents

from .profiles import Profile

_EMBEDDED_URI = "mcpbin://text/plain"


def register(app: Any, profile: Profile, ctx: Any) -> None:
    """Register all prompts (no-op when the profile omits ``prompts``)."""
    if not profile.prompts:
        return

    @app.prompt(name="simple", description="A single user message with no arguments.")
    def simple() -> str:
        return "This is the mcpbin 'simple' prompt: a single user message, no arguments."

    @app.prompt(
        name="with_args",
        description="Prompt with a required argument (topic) and an optional one (tone).",
    )
    def with_args(topic: str, tone: str = "neutral") -> str:
        return f"Write about {topic} in a {tone} tone."

    @app.prompt(name="multi_turn", description="Alternating user/assistant messages.")
    def multi_turn() -> list[Message]:
        return [
            Message(content=TextContent(type="text", text="What is MCP?"), role="user"),
            Message(
                content=TextContent(type="text", text="MCP is the Model Context Protocol."),
                role="assistant",
            ),
            Message(content=TextContent(type="text", text="Give an example server."), role="user"),
        ]

    @app.prompt(
        name="with_embedded_resource",
        description="A user message whose content embeds a resource block.",
    )
    def with_embedded_resource() -> list[Message]:
        embedded = EmbeddedResource(
            type="resource",
            resource=TextResourceContents(
                uri=_EMBEDDED_URI,
                mimeType="text/plain",
                text="Embedded resource payload carried inside a prompt message.",
            ),
        )
        return [Message(content=embedded, role="user")]

    # No docstring and no description= → fastmcp leaves description unset (absent in list).
    @app.prompt(name="no_description")
    def no_description() -> str:  # noqa: D401,D403 - intentionally undocumented
        return "This prompt is registered without a description field."


__all__ = ["register"]
