"""Compatibility facade for generated adapter discovery."""

from __future__ import annotations

import sys

from agent.adapters import adapter_discovery as _module

sys.modules[__name__] = _module
