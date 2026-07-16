"""Compatibility facade for adapter interaction-learning helpers."""

from __future__ import annotations

import sys

from agent.adapters import adapter_interaction_learning as _module

sys.modules[__name__] = _module
