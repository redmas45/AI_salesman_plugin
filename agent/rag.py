"""Compatibility facade for product RAG retrieval."""
import sys
from agent.retrieval import product_rag as _product_rag
sys.modules[__name__] = _product_rag
