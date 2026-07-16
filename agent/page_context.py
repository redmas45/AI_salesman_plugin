"""Compatibility facade for prompt page-context helpers."""
import sys
from agent.prompts import page_context as _page_context
sys.modules[__name__] = _page_context
