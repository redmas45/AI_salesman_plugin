"""Compatibility facade for prompt context budgeting helpers."""
import sys
from agent.prompts import context_budget as _context_budget
sys.modules[__name__] = _context_budget
