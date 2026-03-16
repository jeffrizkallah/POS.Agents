"""Inventory metrics for the weekly analytics report (Phase 6E)."""

import asyncpg
from datetime import date


async def get_inventory_metrics(
    pool: asyncpg.Pool, restaurant_id: str, week_start: date, week_end: date
) -> dict:
    """Compute inventory/waste metrics for the given window.

    Uses inventory_transactions for waste and usage data.
    Handles division by zero and NULL with COALESCE.
    """
    try:
        # Waste events from inventory_transactions WHERE type='waste'
        waste_row = await pool.fetchrow(
            """
            SELECT
                COALESCE(SUM(ABS(quantity_change)), 0) AS waste_qty,
                COUNT(*)                                AS waste_event_count
            FROM inventory_transactions
            WHERE ingredient_id IN (
                SELECT id FROM ingredients WHERE restaurant_id = $1
            )
              AND type = 'waste'
              AND created_at >= $2
              AND created_at <  $3
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        waste_qty = float(waste_row["waste_qty"] or 0)
        waste_event_count = int(waste_row["waste_event_count"] or 0)

        # Total usage from sales transactions
        usage_row = await pool.fetchrow(
            """
            SELECT COALESCE(SUM(ABS(quantity_change)), 0) AS total_usage
            FROM inventory_transactions
            WHERE ingredient_id IN (
                SELECT id FROM ingredients WHERE restaurant_id = $1
            )
              AND type = 'sale'
              AND created_at >= $2
              AND created_at <  $3
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        total_usage = float(usage_row["total_usage"] or 0)

        # Waste rate: waste_qty / (total_usage + waste_qty) × 100
        total_throughput = total_usage + waste_qty
        waste_rate_pct = (
            round(waste_qty / total_throughput * 100, 2)
            if total_throughput > 0
            else 0.0
        )

        # Stock-out count: ingredients currently at 0 stock (proxy for stock-outs this week)
        stockout_row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS stockout_count
            FROM ingredients
            WHERE restaurant_id = $1
              AND stock_qty = 0
              AND reorder_point > 0
            """,
            restaurant_id,
        )
        stock_out_count = int(stockout_row["stockout_count"] or 0)

        # Avg days stock cover: AVG(stock_qty / daily_usage) for ingredients with data
        cover_row = await pool.fetchrow(
            """
            SELECT AVG(
                CASE
                    WHEN idr.daily_usage > 0
                    THEN i.stock_qty / idr.daily_usage
                    ELSE NULL
                END
            ) AS avg_cover
            FROM ingredients i
            JOIN ingredient_depletion_rates idr ON idr.ingredient_id = i.id
            WHERE i.restaurant_id = $1
              AND i.reorder_point > 0
            """,
            restaurant_id,
        )
        avg_days_stock_cover = (
            round(float(cover_row["avg_cover"]), 1)
            if cover_row and cover_row["avg_cover"] is not None
            else None
        )

        # PO cycle time: AVG days from created_at to received (last 30 days)
        po_row = await pool.fetchrow(
            """
            SELECT AVG(
                EXTRACT(EPOCH FROM (updated_at - created_at)) / 86400.0
            ) AS avg_cycle_days
            FROM purchase_orders
            WHERE restaurant_id = $1
              AND status IN ('received', 'completed')
              AND created_at >= NOW() - INTERVAL '30 days'
            """,
            restaurant_id,
        )
        po_cycle_time_days = (
            round(float(po_row["avg_cycle_days"]), 1)
            if po_row and po_row["avg_cycle_days"] is not None
            else None
        )

        return {
            "waste_qty": round(waste_qty, 2),
            "waste_event_count": waste_event_count,
            "waste_rate_pct": waste_rate_pct,
            "stock_out_count": stock_out_count,
            "avg_days_stock_cover": avg_days_stock_cover,
            "po_cycle_time_days": po_cycle_time_days,
        }

    except Exception as e:
        print(f"[Metrics Error] get_inventory_metrics(restaurant_id={restaurant_id}): {e}")
        return {
            "waste_qty": 0.0,
            "waste_event_count": 0,
            "waste_rate_pct": 0.0,
            "stock_out_count": 0,
            "avg_days_stock_cover": None,
            "po_cycle_time_days": None,
        }


async def get_waste_by_ingredient(
    pool: asyncpg.Pool, restaurant_id: str, week_start: date, week_end: date
) -> list:
    """Top 10 ingredients by waste quantity this week."""
    try:
        rows = await pool.fetch(
            """
            SELECT
                i.name                                     AS ingredient_name,
                i.unit,
                SUM(ABS(it.quantity_change))               AS total_wasted
            FROM inventory_transactions it
            JOIN ingredients i ON i.id = it.ingredient_id
            WHERE i.restaurant_id = $1
              AND it.type = 'waste'
              AND it.created_at >= $2
              AND it.created_at <  $3
            GROUP BY i.id, i.name, i.unit
            ORDER BY total_wasted DESC
            LIMIT 10
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        return [
            {
                "ingredient_name": r["ingredient_name"],
                "unit": r["unit"],
                "total_wasted": round(float(r["total_wasted"] or 0), 2),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[Metrics Error] get_waste_by_ingredient(restaurant_id={restaurant_id}): {e}")
        return []
