"""Compatibility facade for AI readiness scanning."""

from __future__ import annotations

import sys

from agent.scanning import scanner as _module

sys.modules[__name__] = _module
