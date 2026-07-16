"""Compatibility facade for CRM admin routes."""

from __future__ import annotations

import sys

from api.crm_admin import crm_router as _module

sys.modules[__name__] = _module
