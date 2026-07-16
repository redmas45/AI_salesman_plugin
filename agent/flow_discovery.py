"""Compatibility facade for server-side website flow discovery."""

from __future__ import annotations

import sys

from agent.flows import flow_discovery as _module

sys.modules[__name__] = _module
