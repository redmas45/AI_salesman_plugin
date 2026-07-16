"""Compatibility facade for OpenAI LLM provider helpers."""
import sys
from agent.providers import llm as _llm
sys.modules[__name__] = _llm
