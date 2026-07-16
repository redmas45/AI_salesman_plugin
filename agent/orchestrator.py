"""Compatibility facade for orchestrator runtime entrypoints."""

from __future__ import annotations

import sys

from agent.orchestration import orchestrator_facade as _module

sys.modules[__name__] = _module
