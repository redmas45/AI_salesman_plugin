"""Compatibility facade for tenant answer cache helpers."""
import sys

from db.cache import answer_cache as _answer_cache

sys.modules[__name__] = _answer_cache
