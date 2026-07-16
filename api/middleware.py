"""Compatibility facade for runtime middleware."""
import sys
from api.runtime import middleware as _middleware
sys.modules[__name__] = _middleware
