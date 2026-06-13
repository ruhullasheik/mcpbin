"""mcpbin tool feature modules.

This package is the discovery root for :func:`mcpbin.registry.register_all`, which
walks its submodules via ``pkgutil.iter_modules(__path__)``. Each feature module
(echo, response_types, errors, delays, schema, notifications, sampling, inspect —
added by later work packages) must expose::

    def register(app, profile, ctx) -> None: ...

Keeping this file as a bare package marker is intentional: it enables ``pkgutil``
discovery without importing anything at package-import time.
"""
