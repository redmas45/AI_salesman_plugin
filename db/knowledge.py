"""Compatibility facade for tenant knowledge-base helpers."""
import sys
from db.knowledge_base import knowledge_items as _knowledge_items
sys.modules[__name__] = _knowledge_items
