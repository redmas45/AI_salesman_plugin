"""Compatibility facade for sales intake helpers."""
import sys
from agent.action_helpers import sales_intake as _sales_intake
sys.modules[__name__] = _sales_intake
