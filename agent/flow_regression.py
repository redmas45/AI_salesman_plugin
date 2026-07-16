"""Compatibility facade for flow regression comparison."""

from __future__ import annotations

import sys

from agent.flows import flow_regression as _module

sys.modules[__name__] = _module
