"""Compatibility facade for product and entity turn response recovery."""

from __future__ import annotations

import sys

from agent.products import product_turn_responses as _module

sys.modules[__name__] = _module
