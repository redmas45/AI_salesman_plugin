"""Compatibility facade for provider status helpers."""
import sys
from agent.providers import provider_status as _provider_status
sys.modules[__name__] = _provider_status
