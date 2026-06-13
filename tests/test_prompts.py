"""Prompt tests (WP13, T052) — FR-007.

Exercises prompts/list and prompts/get for all 5 shapes, including the no-description
and embedded-resource specifics.
"""

from __future__ import annotations

from fastmcp import Client

PROMPT_NAMES = {"simple", "with_args", "multi_turn", "with_embedded_resource", "no_description"}


async def test_all_prompts_listed(client_full: Client):
    async with client_full as c:
        prompts = {p.name: p for p in await c.list_prompts()}
    assert PROMPT_NAMES <= set(prompts)


async def test_no_description_has_no_description_field(client_full: Client):
    async with client_full as c:
        prompts = {p.name: p for p in await c.list_prompts()}
    assert prompts["no_description"].description is None
    # And a prompt that *does* have one still carries it (sanity contrast).
    assert prompts["simple"].description


async def test_simple_single_user_message(client_full: Client):
    async with client_full as c:
        result = await c.get_prompt("simple")
        assert len(result.messages) == 1
        assert result.messages[0].role == "user"


async def test_with_args_includes_arguments(client_full: Client):
    async with client_full as c:
        result = await c.get_prompt("with_args", {"topic": "otters", "tone": "playful"})
        text = " ".join(
            m.content.text for m in result.messages if getattr(m.content, "text", None)
        )
        assert "otters" in text and "playful" in text


async def test_multi_turn_alternates_roles(client_full: Client):
    async with client_full as c:
        result = await c.get_prompt("multi_turn")
        roles = [m.role for m in result.messages]
        assert roles == ["user", "assistant", "user"]


async def test_with_embedded_resource_has_resource_block(client_full: Client):
    async with client_full as c:
        result = await c.get_prompt("with_embedded_resource")
        contents = [m.content for m in result.messages]
        assert any(getattr(c_, "type", None) == "resource" for c_ in contents)
