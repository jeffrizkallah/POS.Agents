"""
tools/order_calculator.py

Pure Python (no DB, no I/O). Calculates how much of an ingredient to order
given current stock levels, depletion rate, and supplier lead time.
"""

import math


def calculate_order_quantity(
    current_stock: float,
    reorder_point: float,
    par_level: float,
    daily_usage: float,
    lead_time_days: int,
) -> dict:
    """
    Calculate the recommended order quantity for a low-stock ingredient.

    Formula:
        days_of_stock_needed = lead_time_days + 3  (3-day safety buffer)
        order_qty = max(par_level - current_stock, daily_usage × days_of_stock_needed)
        Rounded up to the nearest whole unit.

    Args:
        current_stock:   Current on-hand quantity (in the ingredient's unit).
        reorder_point:   The threshold that triggered this check.
        par_level:       The "full" target level.
        daily_usage:     Average units consumed per day (from depletion rates).
        lead_time_days:  Days until a supplier delivery arrives.

    Returns:
        {
            "recommended_qty": float,   # rounded-up quantity to order
            "days_of_coverage": float,  # how many days the order will last
            "reasoning": str            # human-readable explanation
        }
    """
    # Edge case: if daily_usage is zero we cannot calculate days of coverage.
    # Order enough to reach par level so stock is topped up.
    if daily_usage <= 0:
        recommended_qty = max(par_level - current_stock, 0)
        recommended_qty = math.ceil(recommended_qty) if recommended_qty > 0 else 1
        return {
            "recommended_qty": float(recommended_qty),
            "days_of_coverage": None,
            "reasoning": (
                f"No recent sales data to calculate usage rate. "
                f"Ordering {recommended_qty} units to reach par level of {par_level}."
            ),
        }

    days_of_stock_needed = lead_time_days + 3  # 3-day safety buffer

    # Option A: top up to par level
    top_up_qty = max(par_level - current_stock, 0)

    # Option B: cover lead time + safety buffer
    coverage_qty = daily_usage * days_of_stock_needed

    raw_qty = max(top_up_qty, coverage_qty)

    # Round up to nearest whole unit (supplier delivers in whole units)
    recommended_qty = math.ceil(raw_qty) if raw_qty > 0 else 1

    days_of_coverage = recommended_qty / daily_usage

    # Days of stock remaining before new order arrives
    days_remaining = current_stock / daily_usage if daily_usage > 0 else None

    urgency = ""
    if days_remaining is not None and days_remaining < lead_time_days:
        urgency = " ⚠️ URGENT: current stock will run out before delivery arrives."

    reasoning = (
        f"Current stock: {current_stock} (reorder point: {reorder_point}, par: {par_level}). "
        f"Daily usage: {daily_usage:.2f}/day. "
        f"Lead time: {lead_time_days}d + 3d buffer = {days_of_stock_needed}d needed. "
        f"Top-up to par: {top_up_qty:.2f}, coverage qty: {coverage_qty:.2f}. "
        f"Ordering {recommended_qty} units → {days_of_coverage:.1f} days of coverage.{urgency}"
    )

    return {
        "recommended_qty": float(recommended_qty),
        "days_of_coverage": round(days_of_coverage, 1),
        "reasoning": reasoning,
    }
