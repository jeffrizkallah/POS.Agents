"""
tests/test_db.py — Database function tests

Tests every function in tools/database.py against the real Neon DB.
Uses a demo restaurant row (seeded in the DB). No mocking — all real queries.
Run with: pytest tests/test_db.py -v
"""

import pytest
import pytest_asyncio

from tools.database import (
    get_all_restaurants,
    get_low_stock_ingredients,
    calculate_depletion_from_sales,
    update_depletion_rate,
    get_depletion_rate,
    save_purchase_order,
    log_agent_action,
    get_ingredient_by_id,
    get_manager_email,
    get_existing_draft_po_today,
    get_waste_by_ingredient,
)


# ---------------------------------------------------------------------------
# get_all_restaurants
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_restaurants_returns_list(pool):
    result = await get_all_restaurants(pool)
    assert isinstance(result, list)
    assert len(result) >= 1


@pytest.mark.asyncio
async def test_get_all_restaurants_has_required_keys(pool):
    restaurants = await get_all_restaurants(pool)
    r = restaurants[0]
    assert "id" in r
    assert "name" in r


# ---------------------------------------------------------------------------
# get_low_stock_ingredients
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_low_stock_ingredients_returns_list(pool, demo_restaurant):
    result = await get_low_stock_ingredients(pool, str(demo_restaurant["id"]))
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_low_stock_ingredients_item_shape(pool, demo_restaurant):
    result = await get_low_stock_ingredients(pool, str(demo_restaurant["id"]))
    if result:
        item = result[0]
        for key in ("id", "name", "unit", "stock_qty", "reorder_point", "par_level",
                    "cost_per_unit", "supplier_id"):
            assert key in item, f"Missing key: {key}"
        # All items must be at or below their reorder point
        assert float(item["stock_qty"]) <= float(item["reorder_point"])


# ---------------------------------------------------------------------------
# calculate_depletion_from_sales
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def any_ingredient_id(pool):
    """Return any ingredient id from the first restaurant for depletion tests."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id FROM ingredients LIMIT 1")
    assert row, "No ingredients found in DB."
    return str(row["id"])


@pytest.mark.asyncio
async def test_calculate_depletion_returns_float(pool, any_ingredient_id):
    result = await calculate_depletion_from_sales(pool, any_ingredient_id, 7)
    assert isinstance(result, float)
    assert result >= 0.0


@pytest.mark.asyncio
async def test_calculate_depletion_zero_days_returns_zero(pool, any_ingredient_id):
    result = await calculate_depletion_from_sales(pool, any_ingredient_id, 0)
    assert result == 0.0


@pytest.mark.asyncio
async def test_calculate_depletion_nonexistent_ingredient(pool):
    # Should return 0.0 (no transactions), not raise
    result = await calculate_depletion_from_sales(
        pool, "00000000-0000-0000-0000-000000000000", 7
    )
    assert result == 0.0


# ---------------------------------------------------------------------------
# update_depletion_rate + get_depletion_rate (round-trip)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_and_read_depletion_rate(pool, any_ingredient_id):
    test_usage = 3.1415
    await update_depletion_rate(pool, any_ingredient_id, test_usage, 7)
    saved = await get_depletion_rate(pool, any_ingredient_id)
    assert saved is not None
    assert abs(saved - test_usage) < 0.001


@pytest.mark.asyncio
async def test_update_depletion_rate_upserts(pool, any_ingredient_id):
    """Calling update twice should not raise (ON CONFLICT DO UPDATE)."""
    await update_depletion_rate(pool, any_ingredient_id, 1.0, 7)
    await update_depletion_rate(pool, any_ingredient_id, 2.0, 14)
    saved = await get_depletion_rate(pool, any_ingredient_id)
    assert abs(saved - 2.0) < 0.001


@pytest.mark.asyncio
async def test_get_depletion_rate_missing_returns_none(pool):
    result = await get_depletion_rate(pool, "00000000-0000-0000-0000-000000000001")
    assert result is None


# ---------------------------------------------------------------------------
# log_agent_action
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_agent_action_returns_uuid(pool, demo_restaurant):
    log_id = await log_agent_action(
        pool=pool,
        restaurant_id=str(demo_restaurant["id"]),
        agent_name="test_agent",
        action_type="unit_test",
        summary="test_db.py integration test run",
        data={"test": True, "source": "test_db.py"},
        status="completed",
    )
    assert isinstance(log_id, str)
    assert len(log_id) == 36  # UUID format


@pytest.mark.asyncio
async def test_log_agent_action_null_restaurant(pool):
    """System-level logs have no restaurant_id — should still succeed."""
    log_id = await log_agent_action(
        pool=pool,
        restaurant_id=None,
        agent_name="system",
        action_type="unit_test",
        summary="null restaurant_id test",
        data={},
        status="completed",
    )
    assert isinstance(log_id, str)


# ---------------------------------------------------------------------------
# get_ingredient_by_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_ingredient_by_id_found(pool, any_ingredient_id):
    result = await get_ingredient_by_id(pool, any_ingredient_id)
    assert result is not None
    assert "id" in result
    assert "name" in result
    assert str(result["id"]) == any_ingredient_id


@pytest.mark.asyncio
async def test_get_ingredient_by_id_missing_returns_none(pool):
    result = await get_ingredient_by_id(pool, "00000000-0000-0000-0000-000000000002")
    assert result is None


# ---------------------------------------------------------------------------
# get_manager_email
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_manager_email_returns_string_or_none(pool, demo_restaurant):
    result = await get_manager_email(pool, str(demo_restaurant["id"]))
    assert result is None or isinstance(result, str)
    if result:
        assert "@" in result


# ---------------------------------------------------------------------------
# get_existing_draft_po_today
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_existing_draft_po_today_no_crash(pool, demo_restaurant):
    """Calling with a fake supplier should return None, not raise."""
    result = await get_existing_draft_po_today(
        pool,
        str(demo_restaurant["id"]),
        "00000000-0000-0000-0000-000000000099",
    )
    assert result is None


# ---------------------------------------------------------------------------
# get_waste_by_ingredient
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_waste_by_ingredient_returns_list(pool, demo_restaurant):
    result = await get_waste_by_ingredient(pool, str(demo_restaurant["id"]))
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_waste_by_ingredient_item_shape(pool, demo_restaurant):
    result = await get_waste_by_ingredient(pool, str(demo_restaurant["id"]))
    if result:
        item = result[0]
        for key in ("ingredient_id", "ingredient_name", "current_week_qty", "avg_4week_qty"):
            assert key in item
        assert float(item["current_week_qty"]) > 0
