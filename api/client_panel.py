"""Compatibility facade for external client panel routes."""
import sys
from api.client_panels import panel_routes as _panel_routes
sys.modules[__name__] = _panel_routes
