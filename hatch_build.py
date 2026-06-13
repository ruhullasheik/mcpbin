"""Custom hatchling build hook for mcpbin packaging.

The reference frontend lives at the repository root (``frontend/``) and is
authored by a later work package (WP14). We want it shipped into the wheel as
package data under ``mcpbin/frontend/`` *when it exists*, without making the
build fail before that work package lands.

A static ``[tool.hatch.build.targets.wheel.force-include]`` entry would raise
``FileNotFoundError`` whenever ``frontend/`` is absent, breaking ``uv sync`` and
``docker build`` for the scaffold. This hook instead injects the force-include
mapping only when the directory is present, so:

* before WP14: the package still imports/builds cleanly;
* after WP14: the frontend ships in the wheel under ``mcpbin/frontend/``.
"""

from __future__ import annotations

import os

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class FrontendBuildHook(BuildHookInterface):
    """Conditionally force-include the repo-root ``frontend/`` directory."""

    PLUGIN_NAME = "mcpbin-frontend"

    def initialize(self, version: str, build_data: dict) -> None:
        frontend_dir = os.path.join(self.root, "frontend")
        if not os.path.isdir(frontend_dir):
            return

        force_include = build_data.setdefault("force_include", {})
        force_include[frontend_dir] = "mcpbin/frontend"
