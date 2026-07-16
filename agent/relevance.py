"""Compatibility facade for sales relevance and cache-safety policy."""

from __future__ import annotations

import sys

from agent.responses import sales_relevance as _module

sys.modules[__name__] = _module
