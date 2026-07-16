"""Compatibility facade for safe website flow rehearsal."""

from __future__ import annotations

import sys

from agent.flows import flow_rehearsal as _module

sys.modules[__name__] = _module
