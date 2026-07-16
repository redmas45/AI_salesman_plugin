"""Compatibility facade for tenant isolation audit helpers."""
import sys
from agent.security import tenant_isolation as _tenant_isolation
sys.modules[__name__] = _tenant_isolation
