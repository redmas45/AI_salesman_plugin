"""Compatibility facade for text-to-speech provider helpers."""
import sys
from agent.providers import tts as _tts
sys.modules[__name__] = _tts
