"""Compatibility facade for admin CRM persistence helpers."""

from __future__ import annotations

import sys

from db.admin_domain import admin_facade as _module

sys.modules[__name__] = _module
