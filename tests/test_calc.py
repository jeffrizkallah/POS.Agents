"""
tests/test_calc.py

Unit tests for tools/order_calculator.py — pure math, no DB required.
Run with: pytest tests/test_calc.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from tools.order_calculator import calculate_order_quantity


def test_normal_case():
    """Standard low-stock scenario with known usage and lead time."""
    result = calculate_order_quantity(
        current_stock=1.2,
        reorder_point=2.0,
        par_level=10.0,
        daily_usage=0.8,
        lead_time_days=2,
    )
    # days_of_stock_needed = 2 + 3 = 5
    # coverage_qty = 0.8 * 5 = 4.0
    # top_up_qty = 10.0 - 1.2 = 8.8
    # raw_qty = max(8.8, 4.0) = 8.8 → ceil = 9
    assert result["recommended_qty"] == 9.0
    assert result["days_of_coverage"] == pytest.approx(9 / 0.8, rel=0.01)
    assert "reasoning" in result
    assert len(result["reasoning"]) > 0


def test_zero_daily_usage():
    """When there's no sales data, order to reach par level."""
    result = calculate_order_quantity(
        current_stock=0.5,
        reorder_point=2.0,
        par_level=10.0,
        daily_usage=0.0,
        lead_time_days=3,
    )
    assert result["recommended_qty"] >= 1
    assert result["days_of_coverage"] is None
    assert "No recent sales data" in result["reasoning"]


def test_zero_stock():
    """Stock is completely depleted."""
    result = calculate_order_quantity(
        current_stock=0.0,
        reorder_point=2.0,
        par_level=8.0,
        daily_usage=1.5,
        lead_time_days=1,
    )
    # top_up_qty = 8.0, coverage_qty = 1.5 * 4 = 6.0
    # raw = max(8.0, 6.0) = 8.0 → ceil = 8
    assert result["recommended_qty"] == 8.0
    assert result["days_of_coverage"] == pytest.approx(8 / 1.5, rel=0.01)


def test_coverage_dominates_top_up():
    """When coverage qty > top-up qty, use coverage qty."""
    result = calculate_order_quantity(
        current_stock=9.5,
        reorder_point=10.0,
        par_level=12.0,     # top_up = 2.5
        daily_usage=5.0,    # coverage = 5 * (7+3) = 50
        lead_time_days=7,
    )
    # raw = max(2.5, 50) = 50 → ceil = 50
    assert result["recommended_qty"] == 50.0


def test_top_up_dominates_coverage():
    """When top-up qty > coverage qty, use top-up qty."""
    result = calculate_order_quantity(
        current_stock=1.0,
        reorder_point=2.0,
        par_level=100.0,    # top_up = 99
        daily_usage=0.1,    # coverage = 0.1 * 5 = 0.5
        lead_time_days=2,
    )
    # raw = max(99, 0.5) = 99 → ceil = 99
    assert result["recommended_qty"] == 99.0


def test_fractional_usage_rounds_up():
    """Result must always be a whole number (rounded up)."""
    result = calculate_order_quantity(
        current_stock=0.3,
        reorder_point=1.0,
        par_level=5.0,
        daily_usage=0.7,
        lead_time_days=2,
    )
    qty = result["recommended_qty"]
    assert qty == int(qty), "recommended_qty must be a whole number (float with .0)"


def test_minimum_order_is_one():
    """Even if calculated qty rounds to 0, we order at least 1."""
    result = calculate_order_quantity(
        current_stock=0.0,
        reorder_point=0.0,
        par_level=0.0,
        daily_usage=0.0,
        lead_time_days=1,
    )
    assert result["recommended_qty"] >= 1.0


def test_long_lead_time():
    """Long lead time increases the order quantity."""
    short = calculate_order_quantity(1.0, 2.0, 10.0, 1.0, lead_time_days=1)
    long_ = calculate_order_quantity(1.0, 2.0, 10.0, 1.0, lead_time_days=10)
    assert long_["recommended_qty"] >= short["recommended_qty"]


def test_days_of_coverage_matches_qty():
    """days_of_coverage should equal recommended_qty / daily_usage."""
    result = calculate_order_quantity(
        current_stock=2.0,
        reorder_point=3.0,
        par_level=15.0,
        daily_usage=2.0,
        lead_time_days=3,
    )
    expected_coverage = result["recommended_qty"] / 2.0
    assert result["days_of_coverage"] == pytest.approx(expected_coverage, rel=0.01)


def test_returns_dict_with_required_keys():
    """Always returns all three required keys."""
    result = calculate_order_quantity(5.0, 10.0, 20.0, 3.0, 2)
    assert "recommended_qty" in result
    assert "days_of_coverage" in result
    assert "reasoning" in result


def test_urgency_flagged_in_reasoning():
    """URGENT flag appears when stock will run out before delivery."""
    # stock=0.1, daily_usage=1.0 → 0.1 days remaining, lead_time=2
    result = calculate_order_quantity(
        current_stock=0.1,
        reorder_point=2.0,
        par_level=10.0,
        daily_usage=1.0,
        lead_time_days=2,
    )
    assert "URGENT" in result["reasoning"]
