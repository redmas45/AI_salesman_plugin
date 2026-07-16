"""Compatibility facade for admin schema helpers."""

from __future__ import annotations

import sys

from db.core import schema as _module

sys.modules[__name__] = _module
