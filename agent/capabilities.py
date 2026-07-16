"""Compatibility facade for runtime capability filtering."""
import sys
from agent.action_helpers import capabilities as _capabilities
sys.modules[__name__] = _capabilities
