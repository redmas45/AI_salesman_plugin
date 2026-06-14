import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.prompt import SYSTEM_PROMPT_TEMPLATE


def test_prompt_forbids_false_empty_store_claims():
    assert "RETRIEVED CONTEXT IS NOT THE WHOLE STORE" in SYSTEM_PROMPT_TEMPLATE
    assert "NEVER say the whole store/inventory/catalog has no items" in SYSTEM_PROMPT_TEMPLATE


def test_prompt_handles_cart_tray_as_cart_not_inventory():
    assert "CART/TRAY LANGUAGE" in SYSTEM_PROMPT_TEMPLATE
    assert "tray" in SYSTEM_PROMPT_TEMPLATE
    assert "do NOT say the store inventory is empty" in SYSTEM_PROMPT_TEMPLATE
