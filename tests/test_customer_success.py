"""
tests/test_customer_success.py — Customer Success Agent tests

Tests the engagement health check, check-in email gating, and monthly ROI
data retrieval. All DB calls hit the real Neon DB; email sending is mocked.

Run with: pytest tests/test_customer_success.py -v
"""

import pytest
from unittest.mock import patch, AsyncMock

from agents.customer_success import (
    check_restaurant_health,
    send_checkin_if_needed,
    send_monthly_roi_summary_email,
)
from tools.database import (
    get_days_since_last_login,
    get_food_cost_trend_data,
    get_monthly_roi_data,
    get_orders_count_last_week,
    get_orders_count_this_week,
    get_recipe_coverage_pct,
)


# ---------------------------------------------------------------------------
# DB helper tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_days_since_last_login_returns_float_or_none(pool, demo_restaurant):
    result = await get_days_since_last_login(pool, str(demo_restaurant["id"]))
    assert result is None or isinstance(result, float)
    if result is not None:
        assert result >= 0.0


@pytest.mark.asyncio
async def test_get_orders_count_this_week_returns_int(pool, demo_restaurant):
    result = await get_orders_count_this_week(pool, str(demo_restaurant["id"]))
    assert isinstance(result, int)
    assert result >= 0


@pytest.mark.asyncio
async def test_get_orders_count_last_week_returns_int(pool, demo_restaurant):
    result = await get_orders_count_last_week(pool, str(demo_restaurant["id"]))
    assert isinstance(result, int)
    assert result >= 0


@pytest.mark.asyncio
async def test_get_food_cost_trend_data_shape(pool, demo_restaurant):
    result = await get_food_cost_trend_data(pool, str(demo_restaurant["id"]))
    assert "trend" in result
    assert "current_avg" in result
    assert "prior_avg" in result
    assert result["trend"] in ("improving", "stable", "worsening")


@pytest.mark.asyncio
async def test_get_recipe_coverage_pct_valid_range(pool, demo_restaurant):
    result = await get_recipe_coverage_pct(pool, str(demo_restaurant["id"]))
    assert isinstance(result, float)
    assert 0.0 <= result <= 100.0


@pytest.mark.asyncio
async def test_get_monthly_roi_data_shape(pool, demo_restaurant):
    result = await get_monthly_roi_data(pool, str(demo_restaurant["id"]))
    for key in ("month_name", "total_orders", "purchase_orders_approved", "estimated_hours_saved"):
        assert key in result
    assert isinstance(result["total_orders"], int)
    assert isinstance(result["estimated_hours_saved"], float)
    assert isinstance(result["month_name"], str)
    assert len(result["month_name"]) > 0


# ---------------------------------------------------------------------------
# Health check — structure and validity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_restaurant_health_returns_dict(pool, demo_restaurant):
    result = await check_restaurant_health(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_check_restaurant_health_score_in_range(pool, demo_restaurant):
    result = await check_restaurant_health(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    assert 0 <= result["score"] <= 100


@pytest.mark.asyncio
async def test_check_restaurant_health_risk_level_valid(pool, demo_restaurant):
    result = await check_restaurant_health(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    assert result["risk_level"] in ("ok", "at_risk", "churning")


@pytest.mark.asyncio
async def test_check_restaurant_health_required_keys(pool, demo_restaurant):
    result = await check_restaurant_health(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    for key in (
        "score", "flags", "risk_level", "days_since_login",
        "orders_this_week", "orders_last_week", "order_drop_pct",
        "food_cost_trend", "recipe_coverage_pct",
    ):
        assert key in result, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_check_restaurant_health_flags_is_list(pool, demo_restaurant):
    result = await check_restaurant_health(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    assert isinstance(result["flags"], list)


@pytest.mark.asyncio
async def test_check_restaurant_health_risk_consistent_with_score(pool, demo_restaurant):
    """Risk level must be consistent with the numeric score."""
    result = await check_restaurant_health(
        pool, str(demo_restaurant["id"]), demo_restaurant["name"]
    )
    score = result["score"]
    risk = result["risk_level"]
    if score >= 70:
        assert risk == "ok"
    elif score >= 40:
        assert risk == "at_risk"
    else:
        assert risk == "churning"


# ---------------------------------------------------------------------------
# Check-in email gating
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_checkin_if_needed_ok_sends_no_email(pool, demo_restaurant):
    """An 'ok' health score must never trigger a check-in email."""
    health = {
        "score": 85,
        "flags": [],
        "risk_level": "ok",
        "days_since_login": 1.0,
        "orders_this_week": 50,
        "orders_last_week": 48,
        "order_drop_pct": 0.0,
        "food_cost_trend": "stable",
        "current_fc_avg": None,
        "prior_fc_avg": None,
        "recipe_coverage_pct": 90.0,
    }
    with patch("agents.customer_success.send_checkin_email", new=AsyncMock()) as mock_email:
        result = await send_checkin_if_needed(
            pool, str(demo_restaurant["id"]), demo_restaurant["name"], health
        )
    assert result is False
    mock_email.assert_not_called()


@pytest.mark.asyncio
async def test_send_checkin_if_needed_no_manager_email_returns_false(pool, demo_restaurant):
    """If no manager email exists, must return False without crashing."""
    health = {
        "score": 35,
        "flags": ["inactive_logins", "order_volume_drop"],
        "risk_level": "churning",
        "days_since_login": 20.0,
        "orders_this_week": 5,
        "orders_last_week": 50,
        "order_drop_pct": 90.0,
        "food_cost_trend": "worsening",
        "current_fc_avg": 38.0,
        "prior_fc_avg": 30.0,
        "recipe_coverage_pct": 20.0,
    }
    with patch("agents.customer_success.get_manager_email", new=AsyncMock(return_value=None)):
        result = await send_checkin_if_needed(
            pool, str(demo_restaurant["id"]), demo_restaurant["name"], health
        )
    assert result is False


@pytest.mark.asyncio
async def test_send_monthly_roi_summary_no_manager_email_returns_false(pool, demo_restaurant):
    """If no manager email exists, ROI summary must return False without crashing."""
    with patch("agents.customer_success.get_manager_email", new=AsyncMock(return_value=None)):
        result = await send_monthly_roi_summary_email(
            pool, str(demo_restaurant["id"]), demo_restaurant["name"]
        )
    assert result is False
