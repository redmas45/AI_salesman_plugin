"""Compatibility facade for hard-flow barrier detection."""

from __future__ import annotations

import sys

from agent.flows import flow_barriers as _module

sys.modules[__name__] = _module
