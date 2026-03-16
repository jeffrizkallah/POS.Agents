"""Anomaly detection for weekly report snapshots (Phase 6H).

Compares current week metrics against the previous week and raises flags
when significant deviations are detected. All detected anomalies are saved
to the analytics_anomalies table (ON CONFLICT DO NOTHING).
"""

import asyncpg
from datetime import date
from typing import Optional


async def detect_anomalies(
    pool: asyncpg.Pool,
    restaurant_id: str,
    current_metrics: dict,
    previous_metrics: dict,
    week_start: date,
) -> list:
    """Compare current vs previous week metrics. Save and return anomalies.

    current_metrics / previous_metrics are the merged metric dicts from
    report_builder (keys: gross_revenue, food_cost_pct, waste_rate_pct,
    stock_out_count, top_margin_killer_pct).

    Returns a list of anomaly dicts: {anomaly_type, severity, description,
    metric_value, previous_value, change_pct}.
    """
    anomalies = []

    cur_revenue = float(current_metrics.get("gross_revenue") or 0)
    prev_revenue = float(previous_metrics.get("gross_revenue") or 0)
    cur_fc = float(current_metrics.get("food_cost_pct") or 0)
    prev_fc = float(previous_metrics.get("food_cost_pct") or 0)
    cur_waste = float(current_metrics.get("waste_rate_pct") or 0)
    prev_waste = float(previous_metrics.get("waste_rate_pct") or 0)
    cur_stockouts = int(current_metrics.get("stock_out_count") or 0)
    prev_stockouts = int(previous_metrics.get("stock_out_count") or 0)
    cur_killer_pct = current_metrics.get("top_margin_killer_pct")

    # 1. Revenue drop (>20% decline)
    if prev_revenue > 0 and cur_revenue < prev_revenue * 0.80:
        change_pct = round((cur_revenue - prev_revenue) / prev_revenue * 100, 2)
        anomalies.append({
            "anomaly_type": "revenue_drop",
            "severity": "critical",
            "metric_value": cur_revenue,
            "previous_value": prev_revenue,
            "change_pct": change_pct,
            "description": (
                f"Revenue dropped {abs(change_pct):.1f}% vs last week "
                f"(AED {cur_revenue:,.0f} vs AED {prev_revenue:,.0f}). "
                f"Investigate immediately — check order volume, voids, and table activity."
            ),
        })

    # 2. Revenue spike (>25% increase)
    if prev_revenue > 0 and cur_revenue > prev_revenue * 1.25:
        change_pct = round((cur_revenue - prev_revenue) / prev_revenue * 100, 2)
        anomalies.append({
            "anomaly_type": "revenue_spike",
            "severity": "info",
            "metric_value": cur_revenue,
            "previous_value": prev_revenue,
            "change_pct": change_pct,
            "description": (
                f"Excellent week — revenue up {change_pct:.1f}% vs last week "
                f"(AED {cur_revenue:,.0f} vs AED {prev_revenue:,.0f}). "
                f"Review what drove this and replicate."
            ),
        })

    # 3. New record high revenue
    all_time_max = await _get_all_time_max_revenue(pool, restaurant_id, week_start)
    if all_time_max is not None and cur_revenue > all_time_max:
        anomalies.append({
            "anomaly_type": "new_record_high",
            "severity": "info",
            "metric_value": cur_revenue,
            "previous_value": all_time_max,
            "change_pct": round((cur_revenue - all_time_max) / all_time_max * 100, 2) if all_time_max > 0 else 0.0,
            "description": (
                f"New all-time revenue record: AED {cur_revenue:,.0f}. "
                f"Previous record was AED {all_time_max:,.0f}. Celebrate and document what worked."
            ),
        })

    # 4. Food cost spike (+3pp)
    if prev_fc > 0 and cur_fc > prev_fc + 3:
        change_pct = round(cur_fc - prev_fc, 2)
        anomalies.append({
            "anomaly_type": "food_cost_spike",
            "severity": "warning",
            "metric_value": cur_fc,
            "previous_value": prev_fc,
            "change_pct": change_pct,
            "description": (
                f"Food cost % jumped {change_pct:.1f}pp to {cur_fc:.1f}% "
                f"(from {prev_fc:.1f}% last week). "
                f"Check supplier invoices and high-cost dishes."
            ),
        })

    # 5. Waste surge (+2pp in rate)
    if prev_waste > 0 and cur_waste > prev_waste + 2:
        change_pct = round(cur_waste - prev_waste, 2)
        anomalies.append({
            "anomaly_type": "waste_surge",
            "severity": "warning",
            "metric_value": cur_waste,
            "previous_value": prev_waste,
            "change_pct": change_pct,
            "description": (
                f"Waste rate increased {change_pct:.1f}pp to {cur_waste:.1f}% "
                f"(from {prev_waste:.1f}% last week). "
                f"Review waste logs and adjust ordering quantities."
            ),
        })

    # 6. Stock-out spike (>2 additional stockouts vs prior week)
    if cur_stockouts > prev_stockouts + 2:
        anomalies.append({
            "anomaly_type": "stock_out_spike",
            "severity": "warning",
            "metric_value": float(cur_stockouts),
            "previous_value": float(prev_stockouts),
            "change_pct": float(cur_stockouts - prev_stockouts),
            "description": (
                f"{cur_stockouts} ingredient(s) currently at zero stock "
                f"({cur_stockouts - prev_stockouts} more than last week). "
                f"Review reorder points and supplier lead times."
            ),
        })

    # 7. Dish margin collapse (top margin killer >45% food cost)
    if cur_killer_pct is not None and float(cur_killer_pct) > 45:
        anomalies.append({
            "anomaly_type": "dish_margin_collapse",
            "severity": "critical",
            "metric_value": float(cur_killer_pct),
            "previous_value": None,
            "change_pct": None,
            "description": (
                f"'{current_metrics.get('top_margin_killer_name', 'Unknown dish')}' "
                f"has a food cost of {float(cur_killer_pct):.1f}% — "
                f"critically above the 45% collapse threshold. "
                f"Review recipe costs and consider a price increase or removal."
            ),
        })

    # Save all anomalies to DB
    for anomaly in anomalies:
        await _save_anomaly(
            pool=pool,
            restaurant_id=restaurant_id,
            week_start=week_start,
            **anomaly,
        )

    return anomalies


async def _get_all_time_max_revenue(
    pool: asyncpg.Pool, restaurant_id: str, exclude_week_start: date
) -> Optional[float]:
    """Return the max gross_revenue from prior weekly_report_snapshots (excluding current week)."""
    try:
        row = await pool.fetchrow(
            """
            SELECT MAX(gross_revenue) AS max_rev
            FROM weekly_report_snapshots
            WHERE restaurant_id = $1
              AND week_start < $2
            """,
            restaurant_id,
            exclude_week_start,
        )
        return float(row["max_rev"]) if row and row["max_rev"] is not None else None
    except Exception as e:
        print(f"[Anomaly] _get_all_time_max_revenue failed: {e}")
        return None


async def _save_anomaly(
    pool: asyncpg.Pool,
    restaurant_id: str,
    week_start: date,
    anomaly_type: str,
    severity: str,
    description: str,
    metric_value: Optional[float],
    previous_value: Optional[float],
    change_pct: Optional[float],
) -> None:
    """Insert anomaly into analytics_anomalies. Silently skips on conflict."""
    try:
        await pool.execute(
            """
            INSERT INTO analytics_anomalies
                (restaurant_id, week_start, anomaly_type, severity,
                 metric_value, previous_value, change_pct, description, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            ON CONFLICT (restaurant_id, week_start, anomaly_type) DO NOTHING
            """,
            restaurant_id,
            week_start,
            anomaly_type,
            severity,
            metric_value,
            previous_value,
            change_pct,
            description,
        )
    except Exception as e:
        print(f"[Anomaly] _save_anomaly({anomaly_type}): {e}")
