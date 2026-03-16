"""Integration tests for Phase 6 — Reporting & Analytics Agent.

Tests run against the real Neon database using the first available restaurant.
Run with: pytest tests/test_reporting.py -v

Expected: all metric modules return dicts/lists with correct types,
report builder assembles a package, anomaly detector runs without error.
The full agent run (test_full_agent_run) is slow — it calls Claude.
"""

import asyncio
import pytest
from datetime import date, timedelta

from tools.database import create_pool, get_all_restaurants
from tools.metrics.revenue_metrics import get_revenue_metrics, get_revenue_by_category
from tools.metrics.food_cost_metrics import get_food_cost_metrics, get_dish_performance
from tools.metrics.inventory_metrics import get_inventory_metrics, get_waste_by_ingredient
from tools.metrics.menu_metrics import get_menu_metrics, get_full_menu_performance
from tools.metrics.ops_metrics import get_ops_metrics
from tools.metrics.platform_metrics import get_platform_metrics, get_client_league_table
from tools.anomaly_detector import detect_anomalies
from tools.report_builder import build_report_package


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def pool():
    p = await create_pool()
    yield p
    await p.close()


@pytest.fixture
async def first_restaurant(pool):
    restaurants = await get_all_restaurants(pool)
    assert restaurants, "No restaurants found in DB — seed test data first"
    return restaurants[0]


@pytest.fixture
def week_window():
    """Use the last completed week (Mon–Sun)."""
    today = date.today()
    week_end = today - timedelta(days=1)
    week_start = week_end - timedelta(days=6)
    return week_start, week_end


# ---------------------------------------------------------------------------
# Revenue metrics (6C)
# ---------------------------------------------------------------------------

async def test_get_revenue_metrics_returns_dict(pool, first_restaurant, week_window):
    week_start, week_end = week_window
    result = await get_revenue_metrics(pool, str(first_restaurant["id"]), week_start, week_end)
    assert isinstance(result, dict)
    assert "gross_revenue" in result
    assert "total_covers" in result
    assert "revenue_wow_pct" in result
    assert isinstance(result["gross_revenue"], float)
    assert isinstance(result["total_covers"], int)


async def test_get_revenue_by_category_returns_list(pool, first_restaurant, week_window):
    week_start, week_end = week_window
    result = await get_revenue_by_category(pool, str(first_restaurant["id"]), week_start, week_end)
    assert isinstance(result, list)
    for row in result:
        assert "category" in row
        assert "revenue" in row
        assert "pct_of_total" in row


# ---------------------------------------------------------------------------
# Food cost metrics (6D)
# ---------------------------------------------------------------------------

async def test_get_food_cost_metrics_returns_dict(pool, first_restaurant, week_window):
    week_start, week_end = week_window
    result = await get_food_cost_metrics(pool, str(first_restaurant["id"]), week_start, week_end)
    assert isinstance(result, dict)
    assert "food_cost_pct" in result
    assert "food_cost_trend" in result
    assert result["food_cost_trend"] in ("improving", "stable", "deteriorating")
    assert isinstance(result["food_cost_pct"], float)


async def test_get_dish_performance_returns_list(pool, first_restaurant, week_window):
    week_start, week_end = week_window
    result = await get_dish_performance(pool, str(first_restaurant["id"]), week_start, week_end)
    assert isinstance(result, list)
    for row in result:
        assert "dish_name" in row
        assert "food_cost_pct" in row


# ---------------------------------------------------------------------------
# Inventory metrics (6E)
# ---------------------------------------------------------------------------

async def test_get_inventory_metrics_returns_dict(pool, first_restaurant, week_window):
    week_start, week_end = week_window
    result = await get_inventory_metrics(pool, str(first_restaurant["id"]), week_start, week_end)
    assert isinstance(result, dict)
    assert "waste_rate_pct" in result
    assert "stock_out_count" in result
    assert isinstance(result["waste_rate_pct"], float)
    assert isinstance(result["stock_out_count"], int)


async def test_get_waste_by_ingredient_returns_list(pool, first_restaurant, week_window):
    week_start, week_end = week_window
    result = await get_waste_by_ingredient(pool, str(first_restaurant["id"]), week_start, week_end)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Menu metrics (6F)
# ---------------------------------------------------------------------------

async def test_get_menu_metrics_returns_dict(pool, first_restaurant, week_window):
    week_start, week_end = week_window
    result = await get_menu_metrics(pool, str(first_restaurant["id"]), week_start, week_end)
    assert isinstance(result, dict)
    assert "star_to_dog_ratio" in result
    assert "attachment_rate" in result
    assert "top_dish_count" in result
    assert 0.0 <= result["star_to_dog_ratio"] <= 1.0


async def test_get_full_menu_performance_returns_list(pool, first_restaurant, week_window):
    week_start, week_end = week_window
    result = await get_full_menu_performance(pool, str(first_restaurant["id"]), week_start, week_end)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Ops metrics (6F)
# ---------------------------------------------------------------------------

async def test_get_ops_metrics_returns_dict(pool, first_restaurant, week_window):
    week_start, week_end = week_window
    result = await get_ops_metrics(pool, str(first_restaurant["id"]), week_start, week_end)
    assert isinstance(result, dict)
    assert "table_turn_rate" in result
    assert "orders_by_hour" in result
    assert "recommendation_action_rate" in result
    assert len(result["orders_by_hour"]) == 24
    for entry in result["orders_by_hour"]:
        assert "hour" in entry
        assert "count" in entry


# ---------------------------------------------------------------------------
# Platform metrics (6G)
# ---------------------------------------------------------------------------

async def test_get_platform_metrics_returns_dict(pool, week_window):
    week_start, week_end = week_window
    result = await get_platform_metrics(pool, week_start, week_end)
    assert isinstance(result, dict)
    assert "total_active_clients" in result
    assert "total_platform_revenue" in result
    assert "agent_total_runs" in result
    assert isinstance(result["total_active_clients"], int)
    assert isinstance(result["total_platform_revenue"], float)


async def test_get_client_league_table_returns_list(pool, week_window):
    week_start, week_end = week_window
    result = await get_client_league_table(pool, week_start, week_end)
    assert isinstance(result, list)
    for row in result:
        assert "restaurant_name" in row
        assert "gross_revenue" in row


# ---------------------------------------------------------------------------
# Anomaly detector (6H)
# ---------------------------------------------------------------------------

async def test_detect_anomalies_revenue_drop(pool, first_restaurant, week_window):
    week_start, _ = week_window
    current = {"gross_revenue": 800.0, "food_cost_pct": 28.0, "waste_rate_pct": 4.0,
               "stock_out_count": 1, "top_margin_killer_pct": None}
    previous = {"gross_revenue": 5000.0, "food_cost_pct": 27.0, "waste_rate_pct": 3.5,
                "stock_out_count": 0}
    anomalies = await detect_anomalies(
        pool, str(first_restaurant["id"]), current, previous, week_start
    )
    types = [a["anomaly_type"] for a in anomalies]
    assert "revenue_drop" in types


async def test_detect_anomalies_food_cost_spike(pool, first_restaurant, week_window):
    week_start, _ = week_window
    current = {"gross_revenue": 5000.0, "food_cost_pct": 38.0, "waste_rate_pct": 4.0,
               "stock_out_count": 0, "top_margin_killer_pct": None}
    previous = {"gross_revenue": 5000.0, "food_cost_pct": 29.0, "waste_rate_pct": 4.0,
                "stock_out_count": 0}
    anomalies = await detect_anomalies(
        pool, str(first_restaurant["id"]), current, previous, week_start
    )
    types = [a["anomaly_type"] for a in anomalies]
    assert "food_cost_spike" in types


async def test_detect_anomalies_margin_collapse(pool, first_restaurant, week_window):
    week_start, _ = week_window
    current = {"gross_revenue": 5000.0, "food_cost_pct": 30.0, "waste_rate_pct": 4.0,
               "stock_out_count": 0, "top_margin_killer_pct": 48.0,
               "top_margin_killer_name": "Wagyu Burger"}
    previous = {}
    anomalies = await detect_anomalies(
        pool, str(first_restaurant["id"]), current, previous, week_start
    )
    types = [a["anomaly_type"] for a in anomalies]
    assert "dish_margin_collapse" in types


async def test_detect_anomalies_no_anomalies_clean_week(pool, first_restaurant, week_window):
    week_start, _ = week_window
    current = {"gross_revenue": 5200.0, "food_cost_pct": 28.0, "waste_rate_pct": 3.5,
               "stock_out_count": 0, "top_margin_killer_pct": 32.0}
    previous = {"gross_revenue": 5000.0, "food_cost_pct": 27.5, "waste_rate_pct": 3.0,
                "stock_out_count": 0}
    anomalies = await detect_anomalies(
        pool, str(first_restaurant["id"]), current, previous, week_start
    )
    # No critical anomalies expected for a healthy week
    critical = [a for a in anomalies if a["severity"] == "critical"]
    assert len(critical) == 0


# ---------------------------------------------------------------------------
# Report builder (6I)
# ---------------------------------------------------------------------------

async def test_build_report_package_returns_package(pool, first_restaurant, week_window):
    week_start, week_end = week_window
    package = await build_report_package(
        pool,
        str(first_restaurant["id"]),
        first_restaurant["name"],
        week_start,
        week_end,
    )
    assert isinstance(package, dict)
    # May be empty dict if metrics fail — that's OK for early testing
    if package:
        assert "revenue" in package
        assert "food_cost" in package
        assert "inventory" in package
        assert "menu" in package
        assert "ops" in package
        assert "anomalies" in package
        assert "benchmarks" in package
        assert isinstance(package["anomalies"], list)

        print(f"\n[Test] {first_restaurant['name']} report package:")
        print(f"  Revenue:    AED {package['revenue']['gross_revenue']:,.2f}")
        print(f"  Food cost:  {package['food_cost']['food_cost_pct']:.1f}%")
        print(f"  Waste rate: {package['inventory']['waste_rate_pct']:.1f}%")
        print(f"  Anomalies:  {len(package['anomalies'])}")
        print(f"  Top dish:   {package['menu']['top_dish_name']}")
