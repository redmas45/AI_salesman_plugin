"""Compatibility facade for API contracts."""
import sys
from api.contracts import models as _models
sys.modules[__name__] = _models
