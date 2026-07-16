"""Compatibility facade for generated adapter repair helpers."""

from __future__ import annotations

import sys

from agent.adapters import adapter_repair as _module

sys.modules[__name__] = _module
