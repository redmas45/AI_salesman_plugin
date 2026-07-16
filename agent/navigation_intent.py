"""Compatibility facade for navigation and sort intent responses."""

from __future__ import annotations

import sys

from agent.responses import navigation_intent as _module

sys.modules[__name__] = _module
