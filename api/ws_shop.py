"""Compatibility facade for runtime WebSocket shop transport."""
import sys
from api.runtime import ws_shop as _ws_shop
sys.modules[__name__] = _ws_shop
