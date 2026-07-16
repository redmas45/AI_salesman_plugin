"""Compatibility facade for ecommerce prompt helpers."""
import sys
from agent.prompts import ecommerce_prompt as _ecommerce_prompt
sys.modules[__name__] = _ecommerce_prompt
