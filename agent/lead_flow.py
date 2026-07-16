"""Compatibility facade for lead-flow action helpers."""
import sys
from agent.action_helpers import lead_flow as _lead_flow
sys.modules[__name__] = _lead_flow
