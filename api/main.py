"""Compatibility facade for the FastAPI runtime application."""

from __future__ import annotations

import sys

from api.runtime import main_app as _module

sys.modules[__name__] = _module
