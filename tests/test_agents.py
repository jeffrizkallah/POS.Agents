"""
tests/test_agents.py — Agent integration tests

Runs the full inventory check → draft purchase order cycle against the real
Neon DB (demo restaurant). Claude API calls are mocked to avoid cost and
non-determinism; all DB reads and writes are real.

Run with: pytest tests/test_agents.py -v
"""

import math
import pytest
from unittest.mock import patch, AsyncMock

from agents.inventory import run_inventory_check, detect_waste_anomalies
from agents.ordering import draft_purchase_orders


# ---------------------------------------------------------------------------
# Inventory agent — run_inventory_check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_inventory_check_returns_list(pool, demo_restaurant):
    result = await run_inventory_check(pool, str(demo_restaurant["id"]))
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_run_inventory_check_item_shape(pool, demo_restaurant):
    result = await run_inventory_check(pool, str(demo_restaurant["id"]))
    for item in result:
        assert "ingredient" in item
        assert "daily_usage" in item
        assert "days_until_stockout" in item

        assert isinstance(item["daily_usage"], float)
        assert item["daily_usage"] >= 0.0

        # days_until_stockout is either a non-negative float or math.inf
        dos = item["days_until_stockout"]
        assert dos == math.inf or (isinstance(dos, float) and dos >= 0.0)

        # Ingredient must have required keys
        ing = item["ingredient"]
        for key in ("id", "name", "unit", "stock_qty", "reorder_point"):
            assert key in ing


@pytest.mark.asyncio
async def test_run_inventory_check_only_returns_low_stock(pool, demo_restaurant):
    """Every returned ingredient must be at or below its reorder point."""
    result = await run_inventory_check(pool, str(demo_restaurant["id"]))
    for item in result:
        ing = item["ingredient"]
        assert float(ing["stock_qty"]) <= float(ing["reorder_point"])


@pytest.mark.asyncio
async def test_run_inventory_check_writes_depletion_rates(pool, demo_restaurant):
    """After a scan, every returned item must have a depletion rate in the DB."""
    from tools.database import get_depletion_rate

    result = await run_inventory_check(pool, str(demo_restaurant["id"]))
    for item in result:
        ingredient_id = str(item["ingredient"]["id"])
        rate = await get_depletion_rate(pool, ingredient_id)
        assert rate is not None, (
            f"Depletion rate not saved for ingredient {ingredient_id}"
        )


# ---------------------------------------------------------------------------
# Inventory agent — detect_waste_anomalies
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_detect_waste_anomalies_returns_list(pool, demo_restaurant):
    result = await detect_waste_anomalies(pool, str(demo_restaurant["id"]))
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_detect_waste_anomalies_item_shape(pool, demo_restaurant):
    result = await detect_waste_anomalies(pool, str(demo_restaurant["id"]))
    for anomaly in result:
        for key in ("ingredient_id", "ingredient_name", "current_week_qty",
                    "avg_4week_qty", "ratio"):
            assert key in anomaly
        # An anomaly must be at least 3× the average
        assert anomaly["current_week_qty"] >= 3.0 * anomaly["avg_4week_qty"]
        assert anomaly["ratio"] >= 3.0


# ---------------------------------------------------------------------------
# Ordering agent — draft_purchase_orders (Claude mocked)
# ---------------------------------------------------------------------------

def _build_mock_claude_response(low_stock_items: list[dict]) -> list[dict]:
    """Build a minimal valid Claude response from real inventory data."""
    # Group items by supplier so we can generate one order per supplier
    by_supplier: dict[str, dict] = {}
    for entry in low_stock_items:
        ing = entry["ingredient"]
        sid = str(ing.get("supplier_id") or "")
        if not sid:
            continue
        if sid not in by_supplier:
            by_supplier[sid] = {
                "supplier_id": sid,
                "supplier_name": ing.get("supplier_name") or "Test Supplier",
                "items": [],
                "notes": "mocked Claude response for unit test",
            }
        by_supplier[sid]["items"].append({
            "ingredient_id": str(ing["id"]),
            "name": ing["name"],
            "quantity": max(1.0, entry["daily_usage"] * 7),
            "unit": ing["unit"],
            "cost_per_unit": float(ing.get("cost_per_unit") or 0),
            "reasoning": "Test quantity based on 7-day coverage.",
        })

    orders = []
    for order in by_supplier.values():
        order["total_cost"] = sum(
            i["quantity"] * i["cost_per_unit"] for i in order["items"]
        )
        orders.append(order)
    return orders


@pytest.mark.asyncio
async def test_draft_purchase_orders_with_mock_claude(pool, demo_restaurant):
    """Full cycle: real inventory check + mocked Claude → real DB PO save."""
    restaurant_id = str(demo_restaurant["id"])
    restaurant_name = demo_restaurant["name"]

    low_stock_items = await run_inventory_check(pool, restaurant_id)

    if not low_stock_items:
        pytest.skip("No low-stock items in demo restaurant — cannot test ordering.")

    # Filter to items that have a supplier (ordering requires one)
    orderable = [i for i in low_stock_items if i["ingredient"].get("supplier_id")]
    if not orderable:
        pytest.skip("No low-stock items with a supplier assigned.")

    mock_response = _build_mock_claude_response(orderable)

    with patch("agents.ordering._call_claude", new=AsyncMock(return_value=mock_response)):
        created = await draft_purchase_orders(
            pool, restaurant_id, restaurant_name, orderable
        )

    assert isinstance(created, list)
    # Each created order must have a po_id (UUID string)
    for order in created:
        assert "po_id" in order
        assert isinstance(order["po_id"], str)
        assert len(order["po_id"]) == 36
        assert "supplier_id" in order
        assert "items" in order
        assert len(order["items"]) >= 1


@pytest.mark.asyncio
async def test_draft_purchase_orders_empty_input(pool, demo_restaurant):
    """Empty low_stock_items must return [] without calling Claude or the DB."""
    result = await draft_purchase_orders(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"], []
    )
    assert result == []


@pytest.mark.asyncio
async def test_draft_purchase_orders_bad_claude_json(pool, demo_restaurant):
    """Invalid JSON from Claude must be caught: returns [] and does not crash."""
    low_stock_items = await run_inventory_check(pool, str(demo_restaurant["id"]))
    if not low_stock_items:
        pytest.skip("No low-stock items — cannot test bad-JSON path.")

    async def bad_claude(_payload):
        raise ValueError("Claude returned invalid JSON: <html>error</html>")

    with patch("agents.ordering._call_claude", new=bad_claude):
        result = await draft_purchase_orders(
            pool,
            str(demo_restaurant["id"]),
            demo_restaurant["name"],
            low_stock_items,
        )

    assert result == []


@pytest.mark.asyncio
async def test_draft_purchase_orders_duplicate_guard(pool, demo_restaurant):
    """Running draft twice on the same day must not create duplicate POs."""
    restaurant_id = str(demo_restaurant["id"])
    restaurant_name = demo_restaurant["name"]

    low_stock_items = await run_inventory_check(pool, restaurant_id)
    orderable = [i for i in low_stock_items if i["ingredient"].get("supplier_id")]
    if not orderable:
        pytest.skip("No low-stock items with a supplier assigned.")

    mock_response = _build_mock_claude_response(orderable)

    with patch("agents.ordering._call_claude", new=AsyncMock(return_value=mock_response)):
        first_run = await draft_purchase_orders(
            pool, restaurant_id, restaurant_name, orderable
        )
        second_run = await draft_purchase_orders(
            pool, restaurant_id, restaurant_name, orderable
        )

    # Second run should produce no new orders (duplicate guard blocks them)
    first_po_ids = {o["po_id"] for o in first_run}
    second_po_ids = {o["po_id"] for o in second_run}
    assert first_po_ids.isdisjoint(second_po_ids), (
        "Duplicate PO IDs found — duplicate guard is not working."
    )
    assert len(second_run) == 0, (
        "Second run created new POs despite duplicate guard."
    )
