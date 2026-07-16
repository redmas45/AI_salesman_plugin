"""Compatibility facade for admin settings helpers."""
import sys
from db.settings import settings_manager as _settings_manager
sys.modules[__name__] = _settings_manager
