"""Compatibility facade for client initialization runtime."""

from __future__ import annotations

import sys

from agent.client_setup import client_initialization_runtime as _module

sys.modules[__name__] = _module
