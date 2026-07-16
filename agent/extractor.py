"""Compatibility facade for LLM-assisted adapter selector extraction."""

from __future__ import annotations

import sys

from agent.adapters import adapter_llm_extractor as _module

sys.modules[__name__] = _module
