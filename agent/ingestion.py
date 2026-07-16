"""Compatibility facade for catalog ingestion runtime."""

from __future__ import annotations

import sys

from agent.ingestion_helpers import ingestion_facade as _module

sys.modules[__name__] = _module
