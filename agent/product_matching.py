"""Compatibility facade for ecommerce product catalog matching."""

from __future__ import annotations

import sys

from agent.products import product_matching as _module

sys.modules[__name__] = _module
