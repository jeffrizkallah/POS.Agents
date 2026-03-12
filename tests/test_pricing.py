"""
tests/test_pricing.py — Pricing agent integration tests

Runs save_food_cost_snapshots and generate_pricing_recommendations against the
real Neon DB (demo restaurant). Claude API calls are mocked to avoid cost and
non-determinism; all DB reads and writes are real.

Run with: pytest tests/test_pricing.py -v
"""

import pytest
from unittest.mock import patch, AsyncMock

from agents.pricing import save_food_cost_snapshots, generate_pricing_recommendations
from tools.database import get_menu_items_with_costs, get_over_target_menu_items
from tools.pricing_calculator import (
    calculate_cm,
    calculate_avg_cm,
    classify_menu_item,
    requires_multi_cycle_flag,
)


# ---------------------------------------------------------------------------
# pricing_calculator unit tests (no DB, pure math)
# ---------------------------------------------------------------------------

def test_calculate_cm_basic():
    assert calculate_cm(33.5, 15.0) == 18.5


def test_calculate_cm_zero_cost():
    assert calculate_cm(20.0, 0.0) == 20.0


def test_calculate_avg_cm_basic():
    items = [
        {"price": 33.5, "food_cost": 15.0},  # cm = 18.5
        {"price": 24.0, "food_cost": 6.5},   # cm = 17.5
        {"price": 15.0, "food_cost": 4.0},   # cm = 11.0
    ]
    # avg = (18.5 + 17.5 + 11.0) / 3 = 15.67
    assert calculate_avg_cm(items) == 15.67


def test_calculate_avg_cm_empty():
    assert calculate_avg_cm([]) == 0.0


def test_classify_underpriced_star():
    # High cost%, high CM
    result = classify_menu_item(
        food_cost_pct=44.78, target_food_cost_pct=27.0, cm=18.5, avg_cm=13.5
    )
    assert result == "underpriced_star"


def test_classify_problem():
    # High cost%, low CM
    result = classify_menu_item(
        food_cost_pct=44.78, target_food_cost_pct=27.0, cm=8.0, avg_cm=13.5
    )
    assert result == "problem"


def test_classify_true_star():
    # OK cost%, high CM
    result = classify_menu_item(
        food_cost_pct=27.08, target_food_cost_pct=30.0, cm=17.5, avg_cm=13.5
    )
    assert result == "true_star"


def test_classify_plowhorse():
    # OK cost%, low CM
    result = classify_menu_item(
        food_cost_pct=27.27, target_food_cost_pct=30.0, cm=8.0, avg_cm=13.5
    )
    assert result == "plowhorse"


def test_requires_multi_cycle_flag_true():
    # Salmon at 33.5 with food cost 15, target 27%, max increase 8%
    # target price needed = 15 / 0.27 = 55.56
    # max allowed = 33.5 * 1.08 = 36.18 — clearly not enough
    assert requires_multi_cycle_flag(33.5, 15.0, 27.0, 8.0) is True


def test_requires_multi_cycle_flag_false():
    # Item at 20.0 with food cost 5.4, target 30%, max increase 8%
    # target price needed = 5.4 / 0.30 = 18.0
    # max allowed = 20.0 * 1.08 = 21.6 — one cycle is more than enough
    assert requires_multi_cycle_flag(20.0, 5.4, 30.0, 8.0) is False


def test_requires_multi_cycle_flag_zero_price():
    assert requires_multi_cycle_flag(0.0, 5.0, 30.0, 8.0) is False


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_menu_items_with_costs_returns_list(pool, demo_restaurant):
    result = await get_menu_items_with_costs(pool, str(demo_restaurant["id"]))
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_menu_items_with_costs_item_shape(pool, demo_restaurant):
    result = await get_menu_items_with_costs(pool, str(demo_restaurant["id"]))
    for item in result:
        assert "menu_item_id" in item
        assert "menu_item_name" in item
        assert "price" in item
        assert "food_cost" in item
        assert float(item["food_cost"]) >= 0.0


# ---------------------------------------------------------------------------
# Part 1: save_food_cost_snapshots
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_food_cost_snapshots_returns_list(pool, demo_restaurant):
    result = await save_food_cost_snapshots(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_save_food_cost_snapshots_item_shape(pool, demo_restaurant):
    result = await save_food_cost_snapshots(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    for snap in result:
        assert "menu_item_id" in snap
        assert "menu_item_name" in snap
        assert "food_cost" in snap
        assert "food_cost_pct" in snap
        assert "price_at_snapshot" in snap
        assert float(snap["price_at_snapshot"]) > 0
        assert 0 <= float(snap["food_cost_pct"]) <= 1000  # sanity bound


@pytest.mark.asyncio
async def test_save_food_cost_snapshots_pct_formula(pool, demo_restaurant):
    """food_cost_pct must equal (food_cost / price) * 100 for every snapshot."""
    result = await save_food_cost_snapshots(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    for snap in result:
        price = float(snap["price_at_snapshot"])
        food_cost = float(snap["food_cost"])
        expected_pct = round((food_cost / price) * 100, 2)
        assert abs(float(snap["food_cost_pct"]) - expected_pct) < 0.01, (
            f"food_cost_pct mismatch for {snap['menu_item_name']}: "
            f"expected {expected_pct}, got {snap['food_cost_pct']}"
        )


# ---------------------------------------------------------------------------
# Part 2: generate_pricing_recommendations (Claude mocked)
# ---------------------------------------------------------------------------

def _build_mock_claude_response(over_target_items: list[dict]) -> list[dict]:
    """Build a minimal valid Claude response from real DB data."""
    recs = []
    for item in over_target_items:
        current_price = float(item["current_price"])
        food_cost = float(item["food_cost"])
        # Suggest a 5% price increase (within the 8% guardrail)
        recommended_price = round(current_price * 1.05, 2)
        projected_pct = round((food_cost / recommended_price) * 100, 2)
        recs.append(
            {
                "menu_item_id": str(item["menu_item_id"]),
                "current_price": current_price,
                "recommended_price": recommended_price,
                "reasoning": (
                    f"{item['menu_item_name']} has a food cost of "
                    f"{item['food_cost_pct']:.1f}%. A 5% price increase to "
                    f"${recommended_price} brings it to {projected_pct:.1f}%."
                ),
                "projected_food_cost_pct": projected_pct,
            }
        )
    return recs


@pytest.mark.asyncio
async def test_generate_pricing_recommendations_returns_list(pool, demo_restaurant):
    """generate_pricing_recommendations must return a list (may be empty)."""
    # Use a very low target so we always have over-target items to recommend on
    target_pct = 0.0

    # First save snapshots so there's data to query
    await save_food_cost_snapshots(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )

    over_target = await get_over_target_menu_items(
        pool, str(demo_restaurant["id"]), target_pct
    )

    if not over_target:
        pytest.skip("No menu items with food cost data — cannot test recommendations.")

    mock_response = _build_mock_claude_response(over_target)

    with patch(
        "agents.pricing._call_claude", new=AsyncMock(return_value=mock_response)
    ):
        result = await generate_pricing_recommendations(
            pool,
            str(demo_restaurant["id"]),
            demo_restaurant["name"],
            target_pct,
        )

    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_generate_pricing_recommendations_item_shape(pool, demo_restaurant):
    target_pct = 0.0

    await save_food_cost_snapshots(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    over_target = await get_over_target_menu_items(
        pool, str(demo_restaurant["id"]), target_pct
    )
    if not over_target:
        pytest.skip("No menu items with food cost data.")

    mock_response = _build_mock_claude_response(over_target)

    with patch(
        "agents.pricing._call_claude", new=AsyncMock(return_value=mock_response)
    ):
        result = await generate_pricing_recommendations(
            pool,
            str(demo_restaurant["id"]),
            demo_restaurant["name"],
            target_pct,
        )

    for rec in result:
        assert "rec_id" in rec
        assert "menu_item_id" in rec
        assert "current_price" in rec
        assert "recommended_price" in rec
        assert "reasoning" in rec
        assert float(rec["recommended_price"]) >= float(rec["current_price"]), (
            "recommended_price must not be lower than current_price"
        )


@pytest.mark.asyncio
async def test_generate_pricing_recommendations_guardrail(pool, demo_restaurant):
    """Recommended price must never exceed current_price × 1.08 (8% guardrail)."""
    target_pct = 0.0

    await save_food_cost_snapshots(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    over_target = await get_over_target_menu_items(
        pool, str(demo_restaurant["id"]), target_pct
    )
    if not over_target:
        pytest.skip("No menu items with food cost data.")

    # Mock Claude returning a 20% increase (should be capped at 8%)
    def excessive_response(over_target_items):
        recs = []
        for item in over_target_items:
            current_price = float(item["current_price"])
            recs.append(
                {
                    "menu_item_id": str(item["menu_item_id"]),
                    "current_price": current_price,
                    "recommended_price": round(current_price * 1.20, 2),
                    "reasoning": "Test: excessive 20% increase.",
                    "projected_food_cost_pct": 10.0,
                }
            )
        return recs

    mock_response = excessive_response(over_target)

    with patch(
        "agents.pricing._call_claude", new=AsyncMock(return_value=mock_response)
    ):
        result = await generate_pricing_recommendations(
            pool,
            str(demo_restaurant["id"]),
            demo_restaurant["name"],
            target_pct,
        )

    for rec in result:
        current = float(rec["current_price"])
        recommended = float(rec["recommended_price"])
        max_allowed = round(current * 1.08, 2)
        assert recommended <= max_allowed + 0.01, (
            f"Guardrail violated: {recommended} > {max_allowed} "
            f"(8% cap on ${current})"
        )


@pytest.mark.asyncio
async def test_generate_pricing_recommendations_bad_claude_json(pool, demo_restaurant):
    """Invalid JSON from Claude must be caught — returns [] and does not crash."""
    target_pct = 0.0

    await save_food_cost_snapshots(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    over_target = await get_over_target_menu_items(
        pool, str(demo_restaurant["id"]), target_pct
    )
    if not over_target:
        pytest.skip("No menu items with food cost data.")

    async def bad_claude(_payload):
        raise ValueError("Claude returned invalid JSON: <html>error</html>")

    with patch("agents.pricing._call_claude", new=bad_claude):
        result = await generate_pricing_recommendations(
            pool,
            str(demo_restaurant["id"]),
            demo_restaurant["name"],
            target_pct,
        )

    assert result == []


@pytest.mark.asyncio
async def test_generate_pricing_recommendations_no_over_target(pool, demo_restaurant):
    """With a very high target %, no items are over target — returns []."""
    # 999% target means nothing is over budget
    target_pct = 999.0

    await save_food_cost_snapshots(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )

    with patch("agents.pricing._call_claude") as mock_claude:
        result = await generate_pricing_recommendations(
            pool,
            str(demo_restaurant["id"]),
            demo_restaurant["name"],
            target_pct,
        )

    # Claude should not have been called at all
    mock_claude.assert_not_called()
    assert result == []
