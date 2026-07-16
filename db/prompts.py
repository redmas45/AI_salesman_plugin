"""Compatibility facade for prompt profile helpers."""
import sys
from db.prompting import prompt_profiles as _prompt_profiles
sys.modules[__name__] = _prompt_profiles
