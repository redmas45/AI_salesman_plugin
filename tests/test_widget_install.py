"""Public widget installer and adapter runtime contract tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes import clients as client_routes
from agent.adapter_discovery import build_discovery
from db import clients as client_db


def test_install_script_loads_adapter_before_widget() -> None:
    script = client_routes._render_install_script(
        site="ai_kart",
        api_base_url="https://hub.example.com/aihub",
    )

    adapter_index = script.index("shopbot-adapter.js?site=ai_kart")
    widget_index = script.index("shopbot.js?site=ai_kart")

    assert "__aihubInstallLoadedSites" in script
    assert adapter_index < widget_index
    assert "data-site-id" in script
    assert "data-api-url" in script


def test_public_runtime_config_exposes_adapter_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        client_routes.admin_db,
        "get_client_detail",
        lambda site: {
            "site_id": site,
            "adapter_name": "generated_adapter.js",
            "vertical_key": "ecommerce",
            "vertical_config": {
                "routes": {"shop": "/catalog"},
                "actions": {"CHECKOUT": {"type": "navigate", "path": "/checkout"}},
            },
        },
    )
    monkeypatch.setattr(
        client_routes.admin_db,
        "get_vertical_detail",
        lambda key: {
            "key": key,
            "label": "E-commerce",
            "risk_level": "low",
            "action_types": ["SHOW_PRODUCTS", "ADD_TO_CART", "CHECKOUT"],
            "entity_types": ["product"],
        },
    )
    monkeypatch.setattr(
        client_routes.admin_db,
        "get_site_selectors",
        lambda site: {
            "selectors": {"add_to_cart": "button[data-add]"},
            "confidence": 0.82,
            "validated": True,
        },
    )
    monkeypatch.setattr(client_routes.admin_db, "is_client_widget_enabled", lambda site: True)

    payload = client_routes._public_runtime_config(
        site="ai_kart",
        api_base_url="https://hub.example.com/aihub",
    )

    assert payload["site_id"] == "ai_kart"
    assert payload["enabled"] is True
    assert payload["vertical"]["key"] == "ecommerce"
    assert payload["adapter"]["mode"] == "generated-runtime"
    assert payload["adapter"]["routes"]["shop"] == "/catalog"
    assert payload["adapter"]["actions"]["CHECKOUT"]["path"] == "/checkout"
    assert payload["adapter"]["selectors"]["add_to_cart"] == "button[data-add]"
    assert payload["install"]["adapter_script"].endswith("/shopbot-adapter.js?site=ai_kart")


def test_generated_client_script_tag_uses_installer(monkeypatch) -> None:
    monkeypatch.setattr(client_db, "_public_hub_origin", lambda: "https://hub.example.com/aihub")

    script_tag = client_db.script_tag_for_site("AI KART")

    assert "install.js?site=ai_kart" in script_tag
    assert "shopbot.js" not in script_tag


def test_travel_site_registration_generates_booking_adapter_config() -> None:
    discovery = build_discovery(
        {
            "site_id": "tickets_to_do",
            "origin": "https://www.ticketstodo.com",
            "url": "https://www.ticketstodo.com/",
            "title": "TicketsToDo - Tours, Attractions and Activities",
            "text_sample": "Book tours, attractions, activity tickets, destinations, theme parks, and travel experiences.",
            "buttons": [
                {"label": "Book Now", "selector": "button.book-now"},
                {"label": "Search", "selector": "button.search"},
            ],
            "links": [
                {"label": "Things to do", "href": "https://www.ticketstodo.com/things-to-do/"},
                {"label": "Help", "href": "https://www.ticketstodo.com/contact/"},
            ],
            "forms": [
                {
                    "label": "Search destination or activity",
                    "selector": "form.search",
                    "input_selector": "input[name='q']",
                    "submit_selector": "button.search",
                }
            ],
            "platform_hints": {},
        }
    )

    actions = discovery.vertical_config["actions"]

    assert discovery.vertical_key == "travel"
    assert "START_BOOKING" in actions
    assert actions["START_BOOKING"]["selector"] == "button.book-now"
    assert "SEARCH_AVAILABILITY" in actions
    assert discovery.vertical_config["routes"]["shop"] == "/things-to-do/"
