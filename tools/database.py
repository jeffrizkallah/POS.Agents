import asyncpg
import calendar
import json
import os
from datetime import date
from typing import Optional


async def create_pool() -> asyncpg.Pool:
    """Create and return an asyncpg connection pool using DATABASE_URL from env."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
    print("[DB] Connection pool created")
    return pool


async def get_all_restaurants(pool: asyncpg.Pool) -> list[dict]:
    """Return all restaurants. No is_active column — return all rows."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, name, timezone, target_food_cost_pct, currency, created_at
            FROM restaurants
            ORDER BY name
            """
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_all_restaurants: {e}")
        raise


async def get_low_stock_ingredients(pool: asyncpg.Pool, restaurant_id: str) -> list[dict]:
    """Return all ingredients at or below their reorder_point for a restaurant,
    joined with supplier info."""
    try:
        rows = await pool.fetch(
            """
            SELECT
                i.id,
                i.name,
                i.unit,
                i.stock_qty,
                i.par_level,
                i.reorder_point,
                i.cost_per_unit,
                i.supplier_id,
                s.name          AS supplier_name,
                s.email         AS supplier_email,
                s.lead_time_days,
                s.is_supermarket
            FROM ingredients i
            LEFT JOIN suppliers s ON s.id = i.supplier_id
            WHERE i.restaurant_id = $1
              AND i.stock_qty <= i.reorder_point
            ORDER BY i.stock_qty ASC
            """,
            restaurant_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_low_stock_ingredients(restaurant_id={restaurant_id}): {e}")
        raise


async def get_depletion_rate(pool: asyncpg.Pool, ingredient_id: str) -> Optional[float]:
    """Return the saved daily_usage for an ingredient, or None if not yet calculated."""
    try:
        row = await pool.fetchrow(
            """
            SELECT daily_usage
            FROM ingredient_depletion_rates
            WHERE ingredient_id = $1
            """,
            ingredient_id,
        )
        return float(row["daily_usage"]) if row else None
    except Exception as e:
        print(f"[DB Error] get_depletion_rate(ingredient_id={ingredient_id}): {e}")
        raise


async def update_depletion_rate(
    pool: asyncpg.Pool,
    ingredient_id: str,
    daily_usage: float,
    days_analysed: int,
) -> None:
    """Upsert the daily usage rate for an ingredient (insert or update on conflict)."""
    try:
        await pool.execute(
            """
            INSERT INTO ingredient_depletion_rates (ingredient_id, daily_usage, days_analysed, calculated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (ingredient_id)
            DO UPDATE SET
                daily_usage    = EXCLUDED.daily_usage,
                days_analysed  = EXCLUDED.days_analysed,
                calculated_at  = NOW()
            """,
            ingredient_id,
            daily_usage,
            days_analysed,
        )
    except Exception as e:
        print(f"[DB Error] update_depletion_rate(ingredient_id={ingredient_id}): {e}")
        raise


async def calculate_depletion_from_sales(
    pool: asyncpg.Pool, ingredient_id: str, days: int
) -> float:
    """Calculate average daily usage from inventory_transactions of type='sale'
    over the last `days` days. Returns 0.0 if no data."""
    try:
        row = await pool.fetchrow(
            """
            SELECT COALESCE(SUM(ABS(quantity_change)), 0) AS total_used
            FROM inventory_transactions
            WHERE ingredient_id = $1
              AND type = 'sale'
              AND created_at >= NOW() - ($2 || ' days')::INTERVAL
            """,
            ingredient_id,
            str(days),
        )
        total_used = float(row["total_used"])
        return round(total_used / days, 4) if days > 0 else 0.0
    except Exception as e:
        print(f"[DB Error] calculate_depletion_from_sales(ingredient_id={ingredient_id}): {e}")
        raise


async def save_purchase_order(
    pool: asyncpg.Pool,
    restaurant_id: str,
    supplier_id: str,
    lines: list[dict],
    notes: str = "",
) -> str:
    """Create a draft purchase order with its line items in a single transaction.

    Each line dict must contain: ingredient_id, quantity_ordered, cost_per_unit.
    Returns the new purchase_order UUID as a string.
    """
    total_cost = sum(
        float(line["quantity_ordered"]) * float(line["cost_per_unit"]) for line in lines
    )
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                po_id = await conn.fetchval(
                    """
                    INSERT INTO purchase_orders (restaurant_id, supplier_id, status, total_cost, notes, created_at)
                    VALUES ($1, $2, 'draft', $3, $4, NOW())
                    RETURNING id
                    """,
                    restaurant_id,
                    supplier_id,
                    total_cost,
                    notes,
                )
                for line in lines:
                    await conn.execute(
                        """
                        INSERT INTO purchase_order_lines (purchase_order_id, ingredient_id, quantity_ordered, cost_per_unit)
                        VALUES ($1, $2, $3, $4)
                        """,
                        str(po_id),
                        line["ingredient_id"],
                        float(line["quantity_ordered"]),
                        float(line["cost_per_unit"]),
                    )
        return str(po_id)
    except Exception as e:
        print(f"[DB Error] save_purchase_order(restaurant_id={restaurant_id}): {e}")
        raise


async def log_agent_action(
    pool: asyncpg.Pool,
    restaurant_id: Optional[str],
    agent_name: str,
    action_type: str,
    summary: str,
    data: dict,
    status: str = "completed",
    requires_approval: bool = False,
) -> str:
    """Write a row to agent_logs. Returns the new log row UUID as a string."""
    try:
        log_id = await pool.fetchval(
            """
            INSERT INTO agent_logs
                (restaurant_id, agent_name, action_type, summary, data, status, requires_approval, created_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, NOW())
            RETURNING id
            """,
            restaurant_id,
            agent_name,
            action_type,
            summary,
            json.dumps(data),
            status,
            requires_approval,
        )
        return str(log_id)
    except Exception as e:
        print(f"[DB Error] log_agent_action(agent={agent_name}, type={action_type}): {e}")
        raise


async def get_ingredient_by_id(pool: asyncpg.Pool, ingredient_id: str) -> Optional[dict]:
    """Return the full ingredient row by ID, or None if not found."""
    try:
        row = await pool.fetchrow(
            "SELECT * FROM ingredients WHERE id = $1",
            ingredient_id,
        )
        return dict(row) if row else None
    except Exception as e:
        print(f"[DB Error] get_ingredient_by_id(ingredient_id={ingredient_id}): {e}")
        raise


async def get_existing_draft_po_today(
    pool: asyncpg.Pool, restaurant_id: str, supplier_id: str
) -> Optional[str]:
    """Return the id of a draft purchase order for this supplier created today,
    or None if no such order exists. Used to prevent duplicate POs."""
    try:
        row = await pool.fetchrow(
            """
            SELECT id
            FROM purchase_orders
            WHERE restaurant_id = $1
              AND supplier_id    = $2
              AND status         = 'draft'
              AND created_at    >= NOW()::date
            LIMIT 1
            """,
            restaurant_id,
            supplier_id,
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(
            f"[DB Error] get_existing_draft_po_today"
            f"(restaurant_id={restaurant_id}, supplier_id={supplier_id}): {e}"
        )
        raise


async def get_waste_by_ingredient(
    pool: asyncpg.Pool, restaurant_id: str
) -> list[dict]:
    """Return per-ingredient waste totals for the current week and the prior 4-week
    average, used by the waste anomaly detector.

    Returns rows with: ingredient_id, ingredient_name, current_week_qty, avg_4week_qty
    """
    try:
        rows = await pool.fetch(
            """
            WITH current_week AS (
                SELECT
                    wr.ingredient_id,
                    SUM(wr.quantity_wasted) AS current_week_qty
                FROM waste_records wr
                WHERE wr.restaurant_id = $1
                  AND wr.created_at >= date_trunc('week', NOW())
                GROUP BY wr.ingredient_id
            ),
            prior_4_weeks AS (
                SELECT
                    wr.ingredient_id,
                    SUM(wr.quantity_wasted) / 4.0 AS avg_4week_qty
                FROM waste_records wr
                WHERE wr.restaurant_id = $1
                  AND wr.created_at >= NOW() - INTERVAL '4 weeks'
                  AND wr.created_at < date_trunc('week', NOW())
                GROUP BY wr.ingredient_id
            )
            SELECT
                COALESCE(cw.ingredient_id, p4.ingredient_id) AS ingredient_id,
                i.name AS ingredient_name,
                COALESCE(cw.current_week_qty, 0) AS current_week_qty,
                COALESCE(p4.avg_4week_qty, 0) AS avg_4week_qty
            FROM current_week cw
            FULL OUTER JOIN prior_4_weeks p4 ON cw.ingredient_id = p4.ingredient_id
            JOIN ingredients i ON i.id = COALESCE(cw.ingredient_id, p4.ingredient_id)
            WHERE COALESCE(cw.current_week_qty, 0) > 0
            ORDER BY current_week_qty DESC
            """,
            restaurant_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_waste_by_ingredient(restaurant_id={restaurant_id}): {e}")
        raise


async def get_menu_items_with_costs(pool: asyncpg.Pool, restaurant_id: str) -> list[dict]:
    """Return all available menu items for a restaurant with their calculated food cost.

    Joins menu_items → recipes → recipe_items → ingredients to compute:
      food_cost = SUM(ingredient.cost_per_unit × recipe_item.quantity_needed)
    Items with no recipe (no ingredients linked) are included with food_cost = 0.
    """
    try:
        rows = await pool.fetch(
            """
            SELECT
                mi.id            AS menu_item_id,
                mi.name          AS menu_item_name,
                mi.price,
                COALESCE(SUM(i.cost_per_unit * ri.quantity_needed), 0) AS food_cost
            FROM menu_items mi
            LEFT JOIN recipes r      ON r.menu_item_id = mi.id
            LEFT JOIN recipe_items ri ON ri.recipe_id  = r.id
            LEFT JOIN ingredients i  ON i.id           = ri.ingredient_id
            WHERE mi.restaurant_id = $1
              AND mi.is_available  = true
            GROUP BY mi.id, mi.name, mi.price
            ORDER BY mi.name
            """,
            restaurant_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_menu_items_with_costs(restaurant_id={restaurant_id}): {e}")
        raise


async def save_food_cost_snapshot(
    pool: asyncpg.Pool,
    restaurant_id: str,
    menu_item_id: int,
    food_cost: float,
    food_cost_pct: float,
    price_at_snapshot: float,
) -> str:
    """Insert a food cost snapshot row for one menu item. Returns the new row UUID.

    Real column names (confirmed from schema):
      ingredient_cost = the food cost in dollars
      selling_price   = menu item price at time of snapshot
      snapshot_date   = timestamp of the snapshot
    """
    try:
        row_id = await pool.fetchval(
            """
            INSERT INTO food_cost_snapshots
                (restaurant_id, menu_item_id, ingredient_cost, food_cost_pct,
                 selling_price, snapshot_date)
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
            """,
            restaurant_id,
            menu_item_id,
            food_cost,
            food_cost_pct,
            price_at_snapshot,
        )
        return str(row_id)
    except Exception as e:
        print(
            f"[DB Error] save_food_cost_snapshot"
            f"(restaurant_id={restaurant_id}, menu_item_id={menu_item_id}): {e}"
        )
        raise


async def get_over_target_menu_items(
    pool: asyncpg.Pool, restaurant_id: str, target_food_cost_pct: float
) -> list[dict]:
    """Return the most recent food cost snapshot for each menu item where
    food_cost_pct exceeds target_food_cost_pct. Used to decide which items
    need a pricing recommendation."""
    try:
        rows = await pool.fetch(
            """
            WITH latest AS (
                SELECT DISTINCT ON (menu_item_id)
                    menu_item_id,
                    ingredient_cost,
                    food_cost_pct,
                    selling_price
                FROM food_cost_snapshots
                WHERE restaurant_id = $1
                ORDER BY menu_item_id, snapshot_date DESC
            )
            SELECT
                l.menu_item_id,
                mi.name            AS menu_item_name,
                l.ingredient_cost  AS food_cost,
                l.food_cost_pct,
                l.selling_price    AS current_price
            FROM latest l
            JOIN menu_items mi ON mi.id = l.menu_item_id
            WHERE l.food_cost_pct > $2
            ORDER BY l.food_cost_pct DESC
            """,
            restaurant_id,
            target_food_cost_pct,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(
            f"[DB Error] get_over_target_menu_items"
            f"(restaurant_id={restaurant_id}): {e}"
        )
        raise


async def save_pricing_recommendation(
    pool: asyncpg.Pool,
    restaurant_id: str,
    menu_item_id: int,
    current_price: float,
    recommended_price: float,
    reasoning: str,
    current_food_cost_pct: float,
    projected_food_cost_pct: float,
) -> str:
    """Insert a pricing recommendation row. Returns the new row UUID.

    Real table name: ai_pricing_recommendations
    """
    try:
        row_id = await pool.fetchval(
            """
            INSERT INTO ai_pricing_recommendations
                (restaurant_id, menu_item_id, current_price, recommended_price,
                 reasoning, current_food_cost_pct, projected_food_cost_pct,
                 status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', NOW())
            RETURNING id
            """,
            restaurant_id,
            menu_item_id,
            current_price,
            recommended_price,
            reasoning,
            current_food_cost_pct,
            projected_food_cost_pct,
        )
        return str(row_id)
    except Exception as e:
        print(
            f"[DB Error] save_pricing_recommendation"
            f"(restaurant_id={restaurant_id}, menu_item_id={menu_item_id}): {e}"
        )
        raise


async def get_existing_pricing_recommendation_today(
    pool: asyncpg.Pool, restaurant_id: str, menu_item_id: int
) -> Optional[str]:
    """Return the id of a pending pricing recommendation created today for this
    menu item, or None. Used to prevent duplicate nightly recommendations."""
    try:
        row = await pool.fetchrow(
            """
            SELECT id
            FROM ai_pricing_recommendations
            WHERE restaurant_id  = $1
              AND menu_item_id   = $2
              AND status         = 'pending'
              AND created_at    >= NOW()::date
            LIMIT 1
            """,
            restaurant_id,
            menu_item_id,
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(
            f"[DB Error] get_existing_pricing_recommendation_today"
            f"(restaurant_id={restaurant_id}, menu_item_id={menu_item_id}): {e}"
        )
        raise


async def get_sales_volume_by_menu_item(
    pool: asyncpg.Pool, restaurant_id: str, days: int = 30
) -> dict:
    """Return units sold per menu item over the last `days` days.

    Returns a dict of {menu_item_id (int): units_sold (int)}.
    Falls back to an empty dict if the query fails (e.g. unexpected schema).
    """
    try:
        rows = await pool.fetch(
            """
            SELECT oi.menu_item_id, SUM(oi.quantity)::int AS units_sold
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.restaurant_id = $1
              AND o.created_at >= NOW() - ($2 || ' days')::INTERVAL
              AND o.status NOT IN ('cancelled', 'voided')
            GROUP BY oi.menu_item_id
            """,
            restaurant_id,
            str(days),
        )
        return {int(row["menu_item_id"]): int(row["units_sold"]) for row in rows}
    except Exception as e:
        print(
            f"[DB] get_sales_volume_by_menu_item(restaurant_id={restaurant_id}): "
            f"{e} — volume data unavailable, defaulting to no-history mode."
        )
        return {}


async def get_approved_pricing_recommendations(
    pool: asyncpg.Pool, restaurant_id: str
) -> list[dict]:
    """Return all pricing recommendations with status='approved' for a restaurant.

    These have been accepted by the user in the POS dashboard and need to be
    applied to menu_items.price.
    """
    try:
        rows = await pool.fetch(
            """
            SELECT id, menu_item_id, recommended_price, current_price, reasoning
            FROM ai_pricing_recommendations
            WHERE restaurant_id = $1
              AND status = 'approved'
            ORDER BY created_at ASC
            """,
            restaurant_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(
            f"[DB Error] get_approved_pricing_recommendations"
            f"(restaurant_id={restaurant_id}): {e}"
        )
        raise


async def apply_pricing_recommendation(
    pool: asyncpg.Pool,
    rec_id: str,
    menu_item_id: int,
    new_price: float,
) -> None:
    """Update menu_items.price and mark the recommendation as 'applied' in one transaction."""
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE menu_items SET price = $1 WHERE id = $2",
                    new_price,
                    menu_item_id,
                )
                await conn.execute(
                    "UPDATE ai_pricing_recommendations SET status = 'applied' WHERE id = $1",
                    rec_id,
                )
    except Exception as e:
        print(
            f"[DB Error] apply_pricing_recommendation"
            f"(rec_id={rec_id}, menu_item_id={menu_item_id}): {e}"
        )
        raise


async def get_manager_email(pool: asyncpg.Pool, restaurant_id: str) -> Optional[str]:
    """Return the email of the first active manager or owner for a restaurant, or None."""
    try:
        row = await pool.fetchrow(
            """
            SELECT email
            FROM users
            WHERE restaurant_id = $1
              AND role IN ('manager', 'owner')
              AND is_active = true
            LIMIT 1
            """,
            restaurant_id,
        )
        return row["email"] if row else None
    except Exception as e:
        print(f"[DB Error] get_manager_email(restaurant_id={restaurant_id}): {e}")
        raise


# ---------------------------------------------------------------------------
# Phase 5: Customer Success Agent — DB helpers
# ---------------------------------------------------------------------------


async def get_days_since_last_login(
    pool: asyncpg.Pool, restaurant_id: str
) -> Optional[float]:
    """Return days since the most recent user login for a restaurant, or None.

    Uses users.last_login. Returns None if no login data exists or the column
    is absent (degrades gracefully so the health check still runs).
    """
    try:
        row = await pool.fetchrow(
            """
            SELECT EXTRACT(EPOCH FROM (NOW() - MAX(last_login))) / 86400 AS days_since
            FROM users
            WHERE restaurant_id = $1
              AND is_active = true
              AND last_login IS NOT NULL
            """,
            restaurant_id,
        )
        if row and row["days_since"] is not None:
            return float(row["days_since"])
        return None
    except Exception as e:
        print(f"[DB] get_days_since_last_login(restaurant_id={restaurant_id}): {e} — defaulting to None.")
        return None


async def get_orders_count_this_week(pool: asyncpg.Pool, restaurant_id: str) -> int:
    """Return count of non-cancelled orders since the start of the current calendar week."""
    try:
        row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM orders
            WHERE restaurant_id = $1
              AND created_at >= date_trunc('week', NOW())
              AND status NOT IN ('cancelled', 'voided')
            """,
            restaurant_id,
        )
        return int(row["cnt"]) if row else 0
    except Exception as e:
        print(f"[DB Error] get_orders_count_this_week(restaurant_id={restaurant_id}): {e}")
        return 0


async def get_orders_count_last_week(pool: asyncpg.Pool, restaurant_id: str) -> int:
    """Return count of non-cancelled orders during the previous calendar week."""
    try:
        row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM orders
            WHERE restaurant_id = $1
              AND created_at >= date_trunc('week', NOW()) - INTERVAL '7 days'
              AND created_at <  date_trunc('week', NOW())
              AND status NOT IN ('cancelled', 'voided')
            """,
            restaurant_id,
        )
        return int(row["cnt"]) if row else 0
    except Exception as e:
        print(f"[DB Error] get_orders_count_last_week(restaurant_id={restaurant_id}): {e}")
        return 0


async def get_food_cost_trend_data(pool: asyncpg.Pool, restaurant_id: str) -> dict:
    """Compare avg food_cost_pct this week vs two weeks prior from food_cost_snapshots.

    Returns { trend: 'improving'|'stable'|'worsening', current_avg, prior_avg }.
    If no snapshot data exists returns trend='stable' with None averages.
    Threshold: ±1 pp change = trend signal.
    """
    try:
        row = await pool.fetchrow(
            """
            SELECT
                AVG(CASE WHEN snapshot_date >= NOW() - INTERVAL '7 days'
                         THEN food_cost_pct END) AS current_avg,
                AVG(CASE WHEN snapshot_date >= NOW() - INTERVAL '21 days'
                          AND snapshot_date <  NOW() - INTERVAL '14 days'
                         THEN food_cost_pct END) AS prior_avg
            FROM food_cost_snapshots
            WHERE restaurant_id = $1
              AND snapshot_date >= NOW() - INTERVAL '21 days'
            """,
            restaurant_id,
        )
        current_avg = float(row["current_avg"]) if row and row["current_avg"] is not None else None
        prior_avg = float(row["prior_avg"]) if row and row["prior_avg"] is not None else None

        if current_avg is None or prior_avg is None:
            trend = "stable"
        elif current_avg < prior_avg - 1.0:
            trend = "improving"
        elif current_avg > prior_avg + 1.0:
            trend = "worsening"
        else:
            trend = "stable"

        return {"trend": trend, "current_avg": current_avg, "prior_avg": prior_avg}
    except Exception as e:
        print(f"[DB Error] get_food_cost_trend_data(restaurant_id={restaurant_id}): {e}")
        return {"trend": "stable", "current_avg": None, "prior_avg": None}


async def get_recipe_coverage_pct(pool: asyncpg.Pool, restaurant_id: str) -> float:
    """Return what % of available menu items have at least one recipe linked.

    Returns 100.0 if there are no available menu items (no onboarding issue).
    """
    try:
        row = await pool.fetchrow(
            """
            SELECT
                COUNT(DISTINCT mi.id)          AS total_items,
                COUNT(DISTINCT r.menu_item_id) AS items_with_recipe
            FROM menu_items mi
            LEFT JOIN recipes r ON r.menu_item_id = mi.id
            WHERE mi.restaurant_id = $1
              AND mi.is_available = true
            """,
            restaurant_id,
        )
        total = int(row["total_items"]) if row else 0
        with_recipe = int(row["items_with_recipe"]) if row else 0
        if total == 0:
            return 100.0
        return round((with_recipe / total) * 100, 1)
    except Exception as e:
        print(f"[DB Error] get_recipe_coverage_pct(restaurant_id={restaurant_id}): {e}")
        return 100.0


# ---------------------------------------------------------------------------
# Phase 6: Reporting & Analytics Agent — DB helpers
# ---------------------------------------------------------------------------


async def get_active_clients(pool: asyncpg.Pool) -> list[dict]:
    """Return all restaurants (alias for get_all_restaurants for semantic clarity)."""
    return await get_all_restaurants(pool)


async def mark_report_sent(pool: asyncpg.Pool, restaurant_id: str, week_start) -> None:
    """Set report_sent = TRUE on weekly_report_snapshots for this restaurant/week."""
    try:
        await pool.execute(
            """
            UPDATE weekly_report_snapshots
            SET report_sent = TRUE
            WHERE restaurant_id = $1
              AND week_start = $2
            """,
            restaurant_id,
            week_start,
        )
    except Exception as e:
        print(f"[DB Error] mark_report_sent(restaurant_id={restaurant_id}): {e}")


async def upsert_platform_weekly_summary(
    pool: asyncpg.Pool,
    week_start,
    week_end,
    metrics: dict,
) -> None:
    """Upsert a row to platform_weekly_summaries for the given week."""
    try:
        await pool.execute(
            """
            INSERT INTO platform_weekly_summaries (
                week_start, week_end,
                total_active_clients, total_mrr, mrr_at_risk, avg_client_health,
                new_clients_this_week, churned_this_week,
                total_platform_revenue, total_platform_covers,
                avg_food_cost_pct, agent_total_runs,
                feature_adoption_pct, clients_by_band,
                created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::jsonb, NOW()
            )
            ON CONFLICT (week_start) DO UPDATE SET
                week_end               = EXCLUDED.week_end,
                total_active_clients   = EXCLUDED.total_active_clients,
                total_mrr              = EXCLUDED.total_mrr,
                mrr_at_risk            = EXCLUDED.mrr_at_risk,
                avg_client_health      = EXCLUDED.avg_client_health,
                new_clients_this_week  = EXCLUDED.new_clients_this_week,
                churned_this_week      = EXCLUDED.churned_this_week,
                total_platform_revenue = EXCLUDED.total_platform_revenue,
                total_platform_covers  = EXCLUDED.total_platform_covers,
                avg_food_cost_pct      = EXCLUDED.avg_food_cost_pct,
                agent_total_runs       = EXCLUDED.agent_total_runs,
                feature_adoption_pct   = EXCLUDED.feature_adoption_pct,
                clients_by_band        = EXCLUDED.clients_by_band
            """,
            week_start,
            week_end,
            metrics.get("total_active_clients", 0),
            metrics.get("total_mrr", 0.0),
            metrics.get("mrr_at_risk", 0.0),
            metrics.get("avg_client_health", 0.0),
            metrics.get("new_clients_this_week", 0),
            metrics.get("churned_this_week", 0),
            metrics.get("total_platform_revenue", 0.0),
            metrics.get("total_platform_covers", 0),
            metrics.get("avg_food_cost_pct", 0.0),
            metrics.get("agent_total_runs", 0),
            metrics.get("feature_adoption_pct", 0.0),
            json.dumps(metrics.get("clients_by_band", {})),
        )
    except Exception as e:
        print(f"[DB Error] upsert_platform_weekly_summary(week_start={week_start}): {e}")


async def get_monthly_roi_data(pool: asyncpg.Pool, restaurant_id: str) -> dict:
    """Compute monthly ROI metrics for the ROI summary email.

    Returns:
        month_name, total_orders, total_waste_cost_saved (formatted string),
        purchase_orders_approved, estimated_hours_saved, food_cost_improvement_pct.

    All queries are wrapped defensively — returns sensible defaults on failure.
    """
    month_name = calendar.month_name[date.today().month]
    try:
        orders_row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM orders
            WHERE restaurant_id = $1
              AND created_at >= date_trunc('month', NOW())
              AND status NOT IN ('cancelled', 'voided')
            """,
            restaurant_id,
        )
        total_orders = int(orders_row["cnt"]) if orders_row else 0

        waste_row = await pool.fetchrow(
            """
            SELECT COALESCE(SUM(wr.quantity_wasted * i.cost_per_unit), 0) AS waste_cost
            FROM waste_records wr
            JOIN ingredients i ON i.id = wr.ingredient_id
            WHERE wr.restaurant_id = $1
              AND wr.created_at >= date_trunc('month', NOW())
            """,
            restaurant_id,
        )
        waste_cost = float(waste_row["waste_cost"]) if waste_row else 0.0

        po_row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM purchase_orders
            WHERE restaurant_id = $1
              AND status IN ('approved', 'received')
              AND created_at >= date_trunc('month', NOW())
            """,
            restaurant_id,
        )
        po_approved = int(po_row["cnt"]) if po_row else 0

        fc_row = await pool.fetchrow(
            """
            SELECT
                AVG(CASE WHEN snapshot_date >= date_trunc('month', NOW())
                         THEN food_cost_pct END) AS this_month,
                AVG(CASE WHEN snapshot_date >= date_trunc('month', NOW()) - INTERVAL '1 month'
                          AND snapshot_date <  date_trunc('month', NOW())
                         THEN food_cost_pct END) AS last_month
            FROM food_cost_snapshots
            WHERE restaurant_id = $1
              AND snapshot_date >= date_trunc('month', NOW()) - INTERVAL '1 month'
            """,
            restaurant_id,
        )
        this_month_fc = float(fc_row["this_month"]) if fc_row and fc_row["this_month"] is not None else None
        last_month_fc = float(fc_row["last_month"]) if fc_row and fc_row["last_month"] is not None else None
        fc_improvement = (
            round(last_month_fc - this_month_fc, 1)
            if this_month_fc is not None and last_month_fc is not None
            else None
        )

        # Estimate hours saved: 2 min per order + 5 min per PO approved
        estimated_hours_saved = round((total_orders * 2 + po_approved * 5) / 60, 1)

        return {
            "month_name": month_name,
            "total_orders": total_orders,
            "total_waste_cost_saved": f"AED {waste_cost:.2f}",
            "purchase_orders_approved": po_approved,
            "estimated_hours_saved": estimated_hours_saved,
            "food_cost_improvement_pct": fc_improvement,
        }
    except Exception as e:
        print(f"[DB Error] get_monthly_roi_data(restaurant_id={restaurant_id}): {e}")
        return {
            "month_name": month_name,
            "total_orders": 0,
            "total_waste_cost_saved": "—",
            "purchase_orders_approved": 0,
            "estimated_hours_saved": 0.0,
            "food_cost_improvement_pct": None,
        }
