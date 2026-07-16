"""Compatibility facade for input and output guardrails."""

from __future__ import annotations

import sys

from agent.guardrail_helpers import guardrails as _module

sys.modules[__name__] = _module
