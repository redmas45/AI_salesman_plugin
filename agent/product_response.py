"""Compatibility facade for ecommerce product response helpers."""

from __future__ import annotations

import sys

from agent.products import product_response as _module

sys.modules[__name__] = _module
