"""Menu performance metrics for the weekly analytics report (Phase 6F)."""

import asyncpg
from datetime import date


async def get_menu_metrics(
    pool: asyncpg.Pool, restaurant_id: str, week_start: date, week_end: date
) -> dict:
    """Compute menu-level metrics for the given window.

    Returns: top_dish_name, top_dish_count, star_to_dog_ratio, attachment_rate.
    """
    try:
        # Top dish by order count
        top_dish_row = await pool.fetchrow(
            """
            SELECT
                mi.name        AS dish_name,
                SUM(oi.quantity)::int AS order_count
            FROM order_items oi
            JOIN orders     o  ON o.id  = oi.order_id
            JOIN menu_items mi ON mi.id = oi.menu_item_id
            WHERE o.restaurant_id = $1
              AND o.created_at >= $2
              AND o.created_at <  $3
              AND o.status NOT IN ('cancelled', 'voided')
            GROUP BY mi.id, mi.name
            ORDER BY order_count DESC
            LIMIT 1
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        top_dish_name = top_dish_row["dish_name"] if top_dish_row else None
        top_dish_count = int(top_dish_row["order_count"]) if top_dish_row else 0

        # Star-to-dog ratio: items with food_cost_pct ≤ 30% vs total (using latest snapshot)
        ratio_row = await pool.fetchrow(
            """
            WITH latest AS (
                SELECT DISTINCT ON (menu_item_id)
                    menu_item_id, food_cost_pct
                FROM food_cost_snapshots
                WHERE restaurant_id = $1
                ORDER BY menu_item_id, snapshot_date DESC
            )
            SELECT
                COUNT(*)                                                         AS total_items,
                COUNT(*) FILTER (WHERE food_cost_pct <= 30)                      AS star_items
            FROM latest
            """,
            restaurant_id,
        )
        total_items = int(ratio_row["total_items"] or 0)
        star_items = int(ratio_row["star_items"] or 0)
        star_to_dog_ratio = (
            round(star_items / total_items, 4) if total_items > 0 else 0.0
        )

        # Attachment rate: sides+drinks orders per main order
        # Classify by menu category name heuristic (contains 'main' or 'starter' = main)
        attachment_row = await pool.fetchrow(
            """
            WITH order_counts AS (
                SELECT
                    o.id AS order_id,
                    COUNT(*) FILTER (
                        WHERE LOWER(COALESCE(mc.name, '')) LIKE '%main%'
                           OR LOWER(COALESCE(mc.name, '')) LIKE '%entree%'
                           OR LOWER(COALESCE(mc.name, '')) LIKE '%starter%'
                    ) AS main_count,
                    COUNT(*) FILTER (
                        WHERE LOWER(COALESCE(mc.name, '')) LIKE '%side%'
                           OR LOWER(COALESCE(mc.name, '')) LIKE '%drink%'
                           OR LOWER(COALESCE(mc.name, '')) LIKE '%beverage%'
                           OR LOWER(COALESCE(mc.name, '')) LIKE '%dessert%'
                    ) AS attachment_count
                FROM orders o
                JOIN order_items oi    ON oi.order_id   = o.id
                JOIN menu_items  mi    ON mi.id          = oi.menu_item_id
                LEFT JOIN menu_categories mc ON mc.id   = mi.category_id
                WHERE o.restaurant_id = $1
                  AND o.created_at >= $2
                  AND o.created_at <  $3
                  AND o.status NOT IN ('cancelled', 'voided')
                GROUP BY o.id
            )
            SELECT
                COALESCE(SUM(attachment_count), 0)  AS total_attachments,
                COALESCE(SUM(main_count), 0)        AS total_mains
            FROM order_counts
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        total_mains = int(attachment_row["total_mains"] or 0) if attachment_row else 0
        total_attachments = int(attachment_row["total_attachments"] or 0) if attachment_row else 0
        attachment_rate = (
            round(total_attachments / total_mains, 4) if total_mains > 0 else 0.0
        )

        return {
            "top_dish_name": top_dish_name,
            "top_dish_count": top_dish_count,
            "star_to_dog_ratio": star_to_dog_ratio,
            "attachment_rate": attachment_rate,
        }

    except Exception as e:
        print(f"[Metrics Error] get_menu_metrics(restaurant_id={restaurant_id}): {e}")
        return {
            "top_dish_name": None,
            "top_dish_count": 0,
            "star_to_dog_ratio": 0.0,
            "attachment_rate": 0.0,
        }


async def get_full_menu_performance(
    pool: asyncpg.Pool, restaurant_id: str, week_start: date, week_end: date
) -> list:
    """Full menu performance table: name, category, sales_count, revenue, food_cost_pct.

    Ordered by sales_count desc.
    """
    try:
        rows = await pool.fetch(
            """
            WITH latest_snapshot AS (
                SELECT DISTINCT ON (menu_item_id)
                    menu_item_id, food_cost_pct
                FROM food_cost_snapshots
                WHERE restaurant_id = $1
                ORDER BY menu_item_id, snapshot_date DESC
            ),
            sales AS (
                SELECT
                    oi.menu_item_id,
                    SUM(oi.quantity)::int        AS sales_count,
                    SUM(oi.quantity * mi.price)  AS revenue
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
                mi.name                                  AS dish_name,
                COALESCE(mc.name, 'Uncategorised')       AS category,
                COALESCE(s.sales_count, 0)               AS sales_count,
                COALESCE(s.revenue, 0)                   AS revenue,
                COALESCE(ls.food_cost_pct, 0)            AS food_cost_pct
            FROM menu_items mi
            LEFT JOIN menu_categories   mc ON mc.id = mi.category_id
            LEFT JOIN latest_snapshot   ls ON ls.menu_item_id = mi.id
            LEFT JOIN sales             s  ON s.menu_item_id  = mi.id
            WHERE mi.restaurant_id = $1
              AND mi.is_available = true
            ORDER BY s.sales_count DESC NULLS LAST
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        return [
            {
                "dish_name": r["dish_name"],
                "category": r["category"],
                "sales_count": int(r["sales_count"] or 0),
                "revenue": round(float(r["revenue"] or 0), 2),
                "food_cost_pct": round(float(r["food_cost_pct"] or 0), 2),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[Metrics Error] get_full_menu_performance(restaurant_id={restaurant_id}): {e}")
        return []
