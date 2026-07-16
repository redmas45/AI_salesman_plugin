"""Compatibility facade for core database helpers."""

from __future__ import annotations

import sys

from db.core import database as _module

sys.modules[__name__] = _module
