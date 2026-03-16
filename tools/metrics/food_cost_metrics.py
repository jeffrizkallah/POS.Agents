"""Food cost metrics for the weekly analytics report (Phase 6D)."""

import asyncpg
from datetime import date


async def get_food_cost_metrics(
    pool: asyncpg.Pool, restaurant_id: str, week_start: date, week_end: date
) -> dict:
    """Compute food cost metrics from food_cost_snapshots for the given window.

    Returns a dict matching weekly_report_snapshots food cost columns.
    """
    try:
        # Average food cost % for this week
        current_row = await pool.fetchrow(
            """
            SELECT AVG(food_cost_pct) AS avg_pct
            FROM food_cost_snapshots
            WHERE restaurant_id = $1
              AND snapshot_date >= $2
              AND snapshot_date <  $3
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        food_cost_pct = float(current_row["avg_pct"]) if current_row and current_row["avg_pct"] is not None else 0.0

        # Prior 2-week avg (2 weeks before the window)
        from datetime import timedelta
        prior_start = week_start - timedelta(days=14)
        prior_end = week_start
        prior_row = await pool.fetchrow(
            """
            SELECT AVG(food_cost_pct) AS avg_pct
            FROM food_cost_snapshots
            WHERE restaurant_id = $1
              AND snapshot_date >= $2
              AND snapshot_date <  $3
            """,
            restaurant_id,
            prior_start,
            prior_end,
        )
        prior_pct = float(prior_row["avg_pct"]) if prior_row and prior_row["avg_pct"] is not None else None

        # Trend: compare current vs prior (±1pp threshold)
        if food_cost_pct == 0 or prior_pct is None:
            food_cost_trend = "stable"
        elif food_cost_pct < prior_pct - 1.0:
            food_cost_trend = "improving"
        elif food_cost_pct > prior_pct + 1.0:
            food_cost_trend = "deteriorating"
        else:
            food_cost_trend = "stable"

        # Top margin killer: highest food_cost_pct dish in window
        killer_row = await pool.fetchrow(
            """
            SELECT DISTINCT ON (fcs.menu_item_id)
                mi.name       AS dish_name,
                fcs.food_cost_pct
            FROM food_cost_snapshots fcs
            JOIN menu_items mi ON mi.id = fcs.menu_item_id
            WHERE fcs.restaurant_id = $1
              AND fcs.snapshot_date >= $2
              AND fcs.snapshot_date <  $3
            ORDER BY fcs.menu_item_id, fcs.snapshot_date DESC
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        # Get max from latest-per-item
        killer_max_row = await pool.fetchrow(
            """
            WITH latest AS (
                SELECT DISTINCT ON (menu_item_id)
                    menu_item_id, food_cost_pct, ingredient_cost, selling_price
                FROM food_cost_snapshots
                WHERE restaurant_id = $1
                  AND snapshot_date >= $2
                  AND snapshot_date <  $3
                ORDER BY menu_item_id, snapshot_date DESC
            )
            SELECT mi.name, l.food_cost_pct, l.ingredient_cost, l.selling_price
            FROM latest l
            JOIN menu_items mi ON mi.id = l.menu_item_id
            ORDER BY l.food_cost_pct DESC
            LIMIT 1
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        top_margin_killer_name = killer_max_row["name"] if killer_max_row else None
        top_margin_killer_pct = float(killer_max_row["food_cost_pct"]) if killer_max_row else None

        # Top star dish: lowest food_cost_pct
        star_row = await pool.fetchrow(
            """
            WITH latest AS (
                SELECT DISTINCT ON (menu_item_id)
                    menu_item_id, food_cost_pct
                FROM food_cost_snapshots
                WHERE restaurant_id = $1
                  AND snapshot_date >= $2
                  AND snapshot_date <  $3
                  AND food_cost_pct > 0
                ORDER BY menu_item_id, snapshot_date DESC
            )
            SELECT mi.name, l.food_cost_pct
            FROM latest l
            JOIN menu_items mi ON mi.id = l.menu_item_id
            ORDER BY l.food_cost_pct ASC
            LIMIT 1
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        top_star_dish_name = star_row["name"] if star_row else None
        top_star_dish_pct = float(star_row["food_cost_pct"]) if star_row else None

        # Estimated margin loss: SUM of (food_cost_pct - 30)/100 × selling_price × sales_count for items > 30%
        margin_loss_row = await pool.fetchrow(
            """
            WITH latest AS (
                SELECT DISTINCT ON (fcs.menu_item_id)
                    fcs.menu_item_id,
                    fcs.food_cost_pct,
                    fcs.selling_price
                FROM food_cost_snapshots fcs
                WHERE fcs.restaurant_id = $1
                  AND fcs.snapshot_date >= $2
                  AND fcs.snapshot_date <  $3
                  AND fcs.food_cost_pct > 30
                ORDER BY fcs.menu_item_id, fcs.snapshot_date DESC
            )
            SELECT COALESCE(
                SUM(
                    (l.food_cost_pct - 30) / 100.0
                    * l.selling_price
                    * COALESCE(sales.units_sold, 0)
                ), 0
            ) AS margin_loss
            FROM latest l
            LEFT JOIN LATERAL (
                SELECT COALESCE(SUM(oi.quantity), 0) AS units_sold
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE oi.menu_item_id = l.menu_item_id
                  AND o.restaurant_id = $1
                  AND o.created_at >= $2
                  AND o.created_at <  $3
                  AND o.status NOT IN ('cancelled', 'voided')
            ) sales ON TRUE
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        estimated_margin_loss = float(margin_loss_row["margin_loss"] or 0) if margin_loss_row else 0.0

        # Pricing agent recovery: sum of price increases from applied recommendations in window
        recovery_row = await pool.fetchrow(
            """
            SELECT COALESCE(
                SUM(
                    (apr.recommended_price - apr.current_price)
                    * COALESCE(sales.units_sold, 1)
                ), 0
            ) AS recovery
            FROM ai_pricing_recommendations apr
            LEFT JOIN LATERAL (
                SELECT COALESCE(SUM(oi.quantity), 0) AS units_sold
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE oi.menu_item_id = apr.menu_item_id
                  AND o.restaurant_id = $1
                  AND o.created_at >= $2
                  AND o.created_at <  $3
                  AND o.status NOT IN ('cancelled', 'voided')
            ) sales ON TRUE
            WHERE apr.restaurant_id = $1
              AND apr.status = 'applied'
              AND apr.created_at >= $2
              AND apr.created_at <  $3
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        pricing_agent_recovery = float(recovery_row["recovery"] or 0) if recovery_row else 0.0

        return {
            "food_cost_pct": round(food_cost_pct, 2),
            "food_cost_trend": food_cost_trend,
            "top_margin_killer_name": top_margin_killer_name,
            "top_margin_killer_pct": round(top_margin_killer_pct, 2) if top_margin_killer_pct is not None else None,
            "top_star_dish_name": top_star_dish_name,
            "top_star_dish_pct": round(top_star_dish_pct, 2) if top_star_dish_pct is not None else None,
            "estimated_margin_loss": round(estimated_margin_loss, 2),
            "pricing_agent_recovery": round(pricing_agent_recovery, 2),
        }

    except Exception as e:
        print(f"[Metrics Error] get_food_cost_metrics(restaurant_id={restaurant_id}): {e}")
        return {
            "food_cost_pct": 0.0,
            "food_cost_trend": "stable",
            "top_margin_killer_name": None,
            "top_margin_killer_pct": None,
            "top_star_dish_name": None,
            "top_star_dish_pct": None,
            "estimated_margin_loss": 0.0,
            "pricing_agent_recovery": 0.0,
        }


async def get_dish_performance(
    pool: asyncpg.Pool, restaurant_id: str, week_start: date, week_end: date
) -> list:
    """Per-dish performance: food cost %, sales count, revenue. Top 20 by food_cost_pct desc."""
    try:
        rows = await pool.fetch(
            """
            WITH latest_snapshot AS (
                SELECT DISTINCT ON (menu_item_id)
                    menu_item_id,
                    food_cost_pct,
                    ingredient_cost,
                    selling_price
                FROM food_cost_snapshots
                WHERE restaurant_id = $1
                  AND snapshot_date >= $2
                  AND snapshot_date <  $3
                ORDER BY menu_item_id, snapshot_date DESC
            ),
            sales AS (
                SELECT
                    oi.menu_item_id,
                    SUM(oi.quantity)::int              AS sales_count,
                    SUM(oi.quantity * mi.price)        AS revenue
                FROM order_items oi
                JOIN orders o  ON o.id  = oi.order_id
                JOIN menu_items mi ON mi.id = oi.menu_item_id
                WHERE o.restaurant_id = $1
                  AND o.created_at >= $2
                  AND o.created_at <  $3
                  AND o.status NOT IN ('cancelled', 'voided')
                GROUP BY oi.menu_item_id
            )
            SELECT
                mi.name                                     AS dish_name,
                mc.name                                     AS category,
                COALESCE(ls.food_cost_pct, 0)               AS food_cost_pct,
                COALESCE(ls.selling_price, mi.price)        AS selling_price,
                COALESCE(ls.ingredient_cost, 0)             AS ingredient_cost,
                COALESCE(s.sales_count, 0)                  AS sales_count,
                COALESCE(s.revenue, 0)                      AS revenue_contribution
            FROM menu_items mi
            LEFT JOIN menu_categories mc ON mc.id = mi.category_id
            LEFT JOIN latest_snapshot ls ON ls.menu_item_id = mi.id
            LEFT JOIN sales s ON s.menu_item_id = mi.id
            WHERE mi.restaurant_id = $1
              AND mi.is_available = true
            ORDER BY ls.food_cost_pct DESC NULLS LAST
            LIMIT 20
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        return [
            {
                "dish_name": r["dish_name"],
                "category": r["category"],
                "food_cost_pct": float(r["food_cost_pct"] or 0),
                "selling_price": float(r["selling_price"] or 0),
                "ingredient_cost": float(r["ingredient_cost"] or 0),
                "sales_count": int(r["sales_count"] or 0),
                "revenue_contribution": float(r["revenue_contribution"] or 0),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[Metrics Error] get_dish_performance(restaurant_id={restaurant_id}): {e}")
        return []
