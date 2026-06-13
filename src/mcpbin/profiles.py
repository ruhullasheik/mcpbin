"""Capability profiles (FR-011, research R2).

Four named profiles select which capabilities ``initialize`` advertises and which
feature areas register. The matrix is taken verbatim from ``data-model.md`` /
``contracts/protocol.md``:

| Profile      | tools | resources | prompts | sampling | pagination | list_changed |
|--------------|-------|-----------|---------|----------|------------|--------------|
| full         |  ✓    |    ✓      |   ✓     |    ✓     |     ✓      |      ✓       |
| tools-only   |  ✓    |    ✗      |   ✗     |    ✗     |     ✓      |      ✓       |
| no-sampling  |  ✓    |    ✓      |   ✓     |    ✗     |     ✓      |      ✓       |
| minimal      |  ✓    |    ✗      |   ✗     |    ✗     |     ✗      |      ✗       |

(``no-sampling`` still advertises ``tools/resources/prompts``; its sampling *tools*
degrade gracefully rather than being absent — see WP08. ``tools-only``/``minimal``
omit sampling entirely.)

Turning an omitted list method into ``-32601`` happens in WP03 (server) using these
flags; feature modules self-skip in their ``register`` via ``profile.has(...)``.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

# Profile name constants.
FULL = "full"
TOOLS_ONLY = "tools-only"
NO_SAMPLING = "no-sampling"
MINIMAL = "minimal"

DEFAULT_PROFILE = FULL


@dataclass(frozen=True)
class Profile:
    """An advertised capability subset.

    Each boolean is a capability flag. ``has(capability)`` looks one up by name so
    feature ``register`` functions can gate on e.g. ``profile.has("sampling")``.
    """

    name: str
    tools: bool
    resources: bool
    prompts: bool
    sampling: bool
    pagination: bool
    list_changed: bool

    def has(self, capability: str) -> bool:
        """Return whether ``capability`` (a flag name) is enabled for this profile.

        Unknown capability names return ``False`` rather than raising, so callers can
        probe optimistically.
        """
        value = getattr(self, capability, False)
        return bool(value) if isinstance(value, bool) else False


PROFILES: dict[str, Profile] = {
    FULL: Profile(
        name=FULL,
        tools=True,
        resources=True,
        prompts=True,
        sampling=True,
        pagination=True,
        list_changed=True,
    ),
    TOOLS_ONLY: Profile(
        name=TOOLS_ONLY,
        tools=True,
        resources=False,
        prompts=False,
        sampling=False,
        pagination=True,
        list_changed=True,
    ),
    NO_SAMPLING: Profile(
        name=NO_SAMPLING,
        tools=True,
        resources=True,
        prompts=True,
        sampling=False,
        pagination=True,
        list_changed=True,
    ),
    MINIMAL: Profile(
        name=MINIMAL,
        tools=True,
        resources=False,
        prompts=False,
        sampling=False,
        pagination=False,
        list_changed=False,
    ),
}

# Capability flag names (everything on Profile except its ``name``).
CAPABILITIES: tuple[str, ...] = tuple(
    f.name for f in fields(Profile) if f.name != "name"
)


def get_profile(name: str | None = None) -> Profile:
    """Return the named :class:`Profile`, defaulting to ``full``.

    ``None`` selects the default. An unknown name raises ``ValueError`` so a bad
    ``--profile`` flag fails fast at startup.
    """
    if name is None:
        name = DEFAULT_PROFILE
    try:
        return PROFILES[name]
    except KeyError as exc:
        valid = ", ".join(sorted(PROFILES))
        raise ValueError(f"unknown profile {name!r}; expected one of: {valid}") from exc


__all__ = [
    "FULL",
    "TOOLS_ONLY",
    "NO_SAMPLING",
    "MINIMAL",
    "DEFAULT_PROFILE",
    "CAPABILITIES",
    "Profile",
    "PROFILES",
    "get_profile",
]
