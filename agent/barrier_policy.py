"""Compatibility facade for barrier-aware action policy."""
import sys
from agent.action_helpers import barrier_policy as _barrier_policy
sys.modules[__name__] = _barrier_policy
