"""Compatibility facade for universal transaction-flow planning."""

from __future__ import annotations

import sys

from agent.flows import flow_planner as _module

sys.modules[__name__] = _module
