"""Compatibility facade for action readiness helpers."""
import sys
from agent.action_helpers import action_readiness as _action_readiness
sys.modules[__name__] = _action_readiness
