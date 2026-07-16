"""Compatibility facade for speech-to-text provider helpers."""
import sys
from agent.providers import stt as _stt
sys.modules[__name__] = _stt
