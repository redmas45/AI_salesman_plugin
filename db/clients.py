"""Compatibility facade for CRM client persistence workflows."""

from __future__ import annotations

import sys

from db.client_domain import client_facade as _module

sys.modules[__name__] = _module
