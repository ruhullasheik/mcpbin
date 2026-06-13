"""Auto-discovery registry for feature modules (FR-011, research R2).

The registry is the linchpin that lets feature work packages add themselves without
touching shared files.

The ``register`` contract
-------------------------
Every feature module — each ``mcpbin.tools.*`` submodule plus the optional
``mcpbin.resources`` and ``mcpbin.prompts`` modules — MUST expose::

    def register(app, profile, ctx) -> None:
        '''Register this module's tools/resources/prompts on ``app``.

        ``app``     : the FastMCP application instance.
        ``profile`` : the active :class:`mcpbin.profiles.Profile`; modules self-skip
                      capabilities the profile omits (e.g. a sampling module registers
                      nothing when ``not profile.sampling``).
        ``ctx``     : shared runtime context object (session store, assets, etc.)
                      assembled by WP03's server; opaque to the registry.
        '''

:func:`register_all` discovers and invokes every such ``register``.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any

from . import tools as _tools_pkg
from .profiles import Profile

logger = logging.getLogger("mcpbin.registry")


def register_all(app: Any, profile: Profile, ctx: Any) -> None:
    """Discover and register every feature module honoring ``profile``.

    1. Walk ``mcpbin.tools`` submodules via ``pkgutil.iter_modules`` and call each
       module's ``register(app, profile, ctx)``.
    2. Then attempt the optional ``mcpbin.resources`` and ``mcpbin.prompts`` modules,
       each guarded by ``try/except ImportError`` (they may not exist yet during
       WP02/WP03). They are skipped when the active profile omits that capability, and
       a warning is logged when the profile wants them but the module is absent.
    """
    # 1. Tool feature modules (always available under every profile: tools=True).
    for module_info in pkgutil.iter_modules(_tools_pkg.__path__):
        module_name = f"{_tools_pkg.__name__}.{module_info.name}"
        module = importlib.import_module(module_name)
        register = getattr(module, "register", None)
        if register is None:
            logger.warning(
                "tool module %s has no register(app, profile, ctx); skipping",
                module_name,
            )
            continue
        register(app, profile, ctx)

    # 2. Optional resources / prompts modules, gated by profile and guarded import.
    for capability, module_name in (
        ("resources", f"{__package__}.resources"),
        ("prompts", f"{__package__}.prompts"),
    ):
        if not profile.has(capability):
            # Profile omits this capability — do not register it. WP03 installs the
            # -32601 handler for the corresponding list method.
            continue
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            logger.warning(
                "profile %s advertises %s but %s is not present; skipping",
                profile.name,
                capability,
                module_name,
            )
            continue
        register = getattr(module, "register", None)
        if register is None:
            logger.warning(
                "module %s has no register(app, profile, ctx); skipping",
                module_name,
            )
            continue
        register(app, profile, ctx)


__all__ = ["register_all"]
