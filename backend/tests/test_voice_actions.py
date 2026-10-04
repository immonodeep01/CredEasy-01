from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server


def test_stock_movement_action_is_sanitized():
    actions = server.sanitize_actions([{
        "type": "STOCK_MOVEMENT",
        "itemName": "  Tea leaves  ",
        "quantity": 2.5,
        "movementType": "sale",
        "direction": "decrease",
        "note": "Counter sale",
        "itemId": "model-controlled-id",
    }])

    assert actions == [{
        "type": "STOCK_MOVEMENT",
        "itemName": "Tea leaves",
        "quantity": 2.5,
        "movementType": "sale",
        "direction": "decrease",
        "note": "Counter sale",
    }]


def test_stock_movement_rejects_invalid_quantity_and_direction():
    actions = server.sanitize_actions([
        {"type": "STOCK_MOVEMENT", "itemName": "Tea", "quantity": True, "movementType": "purchase", "direction": "increase"},
        {"type": "STOCK_MOVEMENT", "itemName": "Tea", "quantity": 0.00001, "movementType": "purchase", "direction": "increase"},
        {"type": "STOCK_MOVEMENT", "itemName": "Tea", "quantity": 1_000_001, "movementType": "purchase", "direction": "increase"},
        {"type": "STOCK_MOVEMENT", "itemName": "Tea", "quantity": 2, "movementType": "sale", "direction": "increase"},
        {"type": "STOCK_MOVEMENT", "itemName": "Tea", "quantity": 2, "movementType": "unknown", "direction": "decrease"},
    ])

    assert actions == []


def test_stock_adjustment_requires_a_valid_direction():
    assert server.sanitize_actions([
        {"type": "STOCK_MOVEMENT", "itemName": "Tea", "quantity": 1.23456, "movementType": "adjustment", "direction": "increase"}
    ]) == [{
        "type": "STOCK_MOVEMENT",
        "itemName": "Tea",
        "quantity": 1.2346,
        "movementType": "adjustment",
        "direction": "increase",
        "note": "",
    }]
    assert server.sanitize_actions([
        {"type": "STOCK_MOVEMENT", "itemName": "Tea", "quantity": 2, "movementType": "adjustment", "direction": "unknown"}
    ]) == []


def test_navigation_actions_only_accept_supported_app_routes():
    actions = server.sanitize_actions([
        {"type": "NAVIGATE", "route": "inventory"},
        {"type": "NAVIGATE", "route": "daybook"},
        {"type": "NAVIGATE", "route": "https://example.com"},
    ])

    assert actions == [
        {"type": "NAVIGATE", "route": "inventory"},
        {"type": "NAVIGATE", "route": "daybook"},
    ]
