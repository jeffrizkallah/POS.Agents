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


# ---------------------------------------------------------------------------
# Phase 7: Multi-Client Foundation — DB helpers
# ---------------------------------------------------------------------------


async def get_all_clients(pool: asyncpg.Pool) -> list[dict]:
    """Return all active clients from the clients table."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, name, owner_email, owner_whatsapp, timezone, currency, is_active, created_at
            FROM clients
            WHERE is_active = TRUE
            ORDER BY name
            """
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_all_clients: {e}")
        raise


async def get_brands_for_client(pool: asyncpg.Pool, client_id: str) -> list[dict]:
    """Return all active brands for a client."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, client_id, name, industry, business_model, primary_channel,
                   tone, language_primary, language_secondary, target_audience,
                   avg_deal_value, avg_customer_ltv, currency, roi_target_multiplier,
                   is_active, created_at
            FROM brands
            WHERE client_id = $1
              AND is_active = TRUE
            ORDER BY name
            """,
            client_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_brands_for_client(client_id={client_id}): {e}")
        raise


async def get_brand_channels(pool: asyncpg.Pool, brand_id: str) -> list[dict]:
    """Return all active platform credentials for a brand."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, brand_id, platform, account_id, access_token, is_active, created_at
            FROM brand_channels
            WHERE brand_id = $1
              AND is_active = TRUE
            ORDER BY platform
            """,
            brand_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_brand_channels(brand_id={brand_id}): {e}")
        raise


async def get_brand_config(pool: asyncpg.Pool, brand_id: str) -> Optional[dict]:
    """Return the full brand row (tone, language, audience, ROI target, etc.), or None."""
    try:
        row = await pool.fetchrow(
            """
            SELECT id, client_id, name, industry, business_model, primary_channel,
                   tone, language_primary, language_secondary, target_audience,
                   avg_deal_value, avg_customer_ltv, currency, roi_target_multiplier,
                   is_active, created_at
            FROM brands
            WHERE id = $1
            """,
            brand_id,
        )
        return dict(row) if row else None
    except Exception as e:
        print(f"[DB Error] get_brand_config(brand_id={brand_id}): {e}")
        raise


async def get_brand_content_config(pool: asyncpg.Pool, brand_id: str) -> list[dict]:
    """Return content schedule config (one row per platform) for a brand."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, brand_id, platform, posts_per_week, content_pillars,
                   word_limit_step1, word_limit_subsequent, created_at
            FROM brand_content_config
            WHERE brand_id = $1
            ORDER BY platform
            """,
            brand_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_brand_content_config(brand_id={brand_id}): {e}")
        raise


async def get_brand_care_config(pool: asyncpg.Pool, brand_id: str) -> Optional[dict]:
    """Return at-risk keywords + escalation rules + retention offer for a brand, or None."""
    try:
        row = await pool.fetchrow(
            """
            SELECT id, brand_id, at_risk_keywords, escalation_triggers,
                   retention_offer_template, created_at
            FROM brand_care_config
            WHERE brand_id = $1
            """,
            brand_id,
        )
        return dict(row) if row else None
    except Exception as e:
        print(f"[DB Error] get_brand_care_config(brand_id={brand_id}): {e}")
        raise


async def get_industry_benchmarks(pool: asyncpg.Pool, industry: str) -> list[dict]:
    """Return ROI benchmarks for a given industry (all channels)."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, industry, channel, typical_roi_min, typical_roi_max, created_at
            FROM industry_roi_benchmarks
            WHERE industry = $1
            ORDER BY channel
            """,
            industry,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_industry_benchmarks(industry={industry}): {e}")
        raise


async def log_client_agent_action(
    pool: asyncpg.Pool,
    client_id: str,
    brand_id: Optional[str],
    agent_name: str,
    action_type: str,
    summary: str,
    data: dict,
    status: str = "completed",
    duration_ms: Optional[int] = None,
) -> str:
    """Write a row to client_agent_activity. Returns the new row UUID as a string."""
    try:
        log_id = await pool.fetchval(
            """
            INSERT INTO client_agent_activity
                (client_id, brand_id, agent_name, action_type, summary, data, status, duration_ms, created_at)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, NOW())
            RETURNING id
            """,
            client_id,
            brand_id,
            agent_name,
            action_type,
            summary,
            json.dumps(data),
            status,
            duration_ms,
        )
        return str(log_id)
    except Exception as e:
        print(f"[DB Error] log_client_agent_action(agent={agent_name}, type={action_type}): {e}")
        raise


# ---------------------------------------------------------------------------
# Phase 8: Orchestrator Agent — DB helpers
# ---------------------------------------------------------------------------


async def get_pending_approvals(pool: asyncpg.Pool, client_id: str) -> list[dict]:
    """Return all status=pending approval requests for a client, oldest first."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, client_id, brand_id, agent_name, approval_type,
                   payload, status, expires_at, decided_at, created_at
            FROM client_approval_requests
            WHERE client_id = $1
              AND status = 'pending'
            ORDER BY created_at ASC
            """,
            client_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_pending_approvals(client_id={client_id}): {e}")
        raise


async def save_approval_request(
    pool: asyncpg.Pool,
    client_id: str,
    brand_id: Optional[str],
    agent_name: str,
    approval_type: str,
    payload: dict,
    expires_at=None,
) -> str:
    """Insert an approval request. Returns the new row UUID as a string."""
    try:
        row_id = await pool.fetchval(
            """
            INSERT INTO client_approval_requests
                (client_id, brand_id, agent_name, approval_type, payload, expires_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            RETURNING id
            """,
            client_id,
            brand_id,
            agent_name,
            approval_type,
            json.dumps(payload),
            expires_at,
        )
        return str(row_id)
    except Exception as e:
        print(f"[DB Error] save_approval_request(client_id={client_id}, type={approval_type}): {e}")
        raise


async def update_approval_status(
    pool: asyncpg.Pool, approval_id: str, status: str
) -> None:
    """Set status to approved/rejected/expired and record decided_at."""
    try:
        await pool.execute(
            """
            UPDATE client_approval_requests
            SET status = $1, decided_at = NOW()
            WHERE id = $2
            """,
            status,
            approval_id,
        )
    except Exception as e:
        print(f"[DB Error] update_approval_status(approval_id={approval_id}): {e}")
        raise


async def get_roi_by_channel(
    pool: asyncpg.Pool, client_id: str, days: int = 30
) -> list[dict]:
    """Compute rolling ROI per channel from spend + revenue tables.

    Returns rows with: channel, total_spend, total_revenue, roi (revenue/spend).
    Channels with zero spend are excluded. Sorted by roi DESC.
    """
    try:
        rows = await pool.fetch(
            """
            WITH spend AS (
                SELECT channel, SUM(amount) AS total_spend
                FROM client_spend_entries
                WHERE client_id = $1
                  AND recorded_at >= NOW() - ($2 || ' days')::INTERVAL
                GROUP BY channel
            ),
            revenue AS (
                SELECT channel, SUM(amount) AS total_revenue
                FROM client_revenue_entries
                WHERE client_id = $1
                  AND recorded_at >= NOW() - ($2 || ' days')::INTERVAL
                GROUP BY channel
            )
            SELECT
                s.channel,
                s.total_spend,
                COALESCE(r.total_revenue, 0) AS total_revenue,
                CASE WHEN s.total_spend > 0
                     THEN COALESCE(r.total_revenue, 0) / s.total_spend
                     ELSE 0
                END AS roi
            FROM spend s
            LEFT JOIN revenue r ON r.channel = s.channel
            ORDER BY roi DESC
            """,
            client_id,
            str(days),
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_roi_by_channel(client_id={client_id}): {e}")
        return []


async def get_budget_envelopes(pool: asyncpg.Pool, client_id: str) -> list[dict]:
    """Return all channel budget envelopes for a client."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, client_id, channel, allocated_amount, spent_amount,
                   roi_current, consecutive_below_roi_months, status, updated_at
            FROM client_budget_envelopes
            WHERE client_id = $1
            ORDER BY channel
            """,
            client_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_budget_envelopes(client_id={client_id}): {e}")
        return []


async def save_roi_snapshot(
    pool: asyncpg.Pool, client_id: str, snapshot_data: dict
) -> str:
    """Insert an ROI snapshot for today's 30-day rolling window. Returns new row UUID."""
    from datetime import date, timedelta
    period_end = date.today()
    period_start = period_end - timedelta(days=30)
    try:
        row_id = await pool.fetchval(
            """
            INSERT INTO client_roi_snapshots (
                client_id, period_start, period_end,
                total_spend, total_revenue, platform_cost,
                spend_by_channel, revenue_by_channel,
                channels_below_target, compounding_channels
            ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9::jsonb, $10::jsonb)
            RETURNING id
            """,
            client_id,
            period_start,
            period_end,
            snapshot_data.get("total_spend", 0.0),
            snapshot_data.get("total_revenue", 0.0),
            snapshot_data.get("platform_cost", 0.0),
            json.dumps(snapshot_data.get("spend_by_channel", {})),
            json.dumps(snapshot_data.get("revenue_by_channel", {})),
            json.dumps(snapshot_data.get("channels_below_target", {})),
            json.dumps(snapshot_data.get("compounding_channels", {})),
        )
        return str(row_id)
    except Exception as e:
        print(f"[DB Error] save_roi_snapshot(client_id={client_id}): {e}")
        raise


async def save_intelligence(
    pool: asyncpg.Pool,
    client_id: str,
    report_type: str,
    content: dict,
    urgency: str = "normal",
) -> str:
    """Save a briefing or alert to client_intelligence. Returns new row UUID."""
    try:
        row_id = await pool.fetchval(
            """
            INSERT INTO client_intelligence (client_id, report_type, content, urgency)
            VALUES ($1, $2, $3::jsonb, $4)
            RETURNING id
            """,
            client_id,
            report_type,
            json.dumps(content),
            urgency,
        )
        return str(row_id)
    except Exception as e:
        print(f"[DB Error] save_intelligence(client_id={client_id}, type={report_type}): {e}")
        raise


async def get_recent_intelligence(
    pool: asyncpg.Pool, client_id: str, limit: int = 5
) -> list[dict]:
    """Return the most recent intelligence items for a client (for daily briefing)."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, report_type, content, urgency, created_at
            FROM client_intelligence
            WHERE client_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            client_id,
            limit,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_recent_intelligence(client_id={client_id}): {e}")
        return []


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


# ---------------------------------------------------------------------------
# Phase 9: Scout Agent DB functions
# ---------------------------------------------------------------------------

async def get_unqualified_prospects(
    pool: asyncpg.Pool, client_id: str, brand_id: str, limit: int = 3
) -> list[dict]:
    """Return prospects with status='researched' (not yet scored) for a brand."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, client_id, brand_id, name, website, industry,
                   size_signal, location, source, status, created_at
            FROM client_prospects
            WHERE client_id = $1
              AND brand_id  = $2
              AND status    = 'researched'
            ORDER BY created_at ASC
            LIMIT $3
            """,
            client_id,
            brand_id,
            limit,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_unqualified_prospects(client_id={client_id}): {e}")
        return []


async def save_prospect(
    pool: asyncpg.Pool, client_id: str, brand_id: str, prospect_data: dict
) -> str:
    """Insert a new prospect row. Returns the new UUID as a string."""
    try:
        row = await pool.fetchrow(
            """
            INSERT INTO client_prospects
                (client_id, brand_id, name, website, industry,
                 size_signal, location, source, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'researched')
            RETURNING id::TEXT
            """,
            client_id,
            brand_id,
            prospect_data.get("name", ""),
            prospect_data.get("website"),
            prospect_data.get("industry"),
            prospect_data.get("size_signal"),
            prospect_data.get("location"),
            prospect_data.get("source", "manual"),
        )
        return row["id"] if row else ""
    except Exception as e:
        print(f"[DB Error] save_prospect(client_id={client_id}): {e}")
        return ""


async def update_prospect_score(
    pool: asyncpg.Pool,
    prospect_id: str,
    score: float,
    fit_signals: list,
    roi_estimate: Optional[float] = None,
    status: str = "qualified",
) -> None:
    """Update a prospect's qualification score, signals, ROI estimate, and status."""
    try:
        await pool.execute(
            """
            UPDATE client_prospects
            SET qualification_score = $1,
                fit_signals         = $2::JSONB,
                roi_estimate        = $3,
                status              = $4
            WHERE id = $5
            """,
            score,
            json.dumps(fit_signals),
            roi_estimate,
            status,
            prospect_id,
        )
    except Exception as e:
        print(f"[DB Error] update_prospect_score(prospect_id={prospect_id}): {e}")


async def save_lead(
    pool: asyncpg.Pool,
    client_id: str,
    brand_id: str,
    prospect_id: str,
    stage: str = "pending_approval",
    contract_value_estimate: Optional[float] = None,
) -> str:
    """Create a lead from a qualified prospect. Returns the new lead UUID."""
    try:
        row = await pool.fetchrow(
            """
            INSERT INTO client_leads
                (client_id, brand_id, prospect_id, stage, contract_value_estimate)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id::TEXT
            """,
            client_id,
            brand_id,
            prospect_id,
            stage,
            contract_value_estimate,
        )
        return row["id"] if row else ""
    except Exception as e:
        print(f"[DB Error] save_lead(prospect_id={prospect_id}): {e}")
        return ""


async def get_contracts_nearing_renewal(
    pool: asyncpg.Pool, client_id: str, days: int = 90
) -> list[dict]:
    """Return active contracts with renewal_date within the next N days."""
    try:
        rows = await pool.fetch(
            """
            SELECT c.id, c.client_id, c.brand_id, c.lead_id,
                   c.value, c.renewal_date, c.status,
                   p.name AS prospect_name
            FROM client_contracts c
            LEFT JOIN client_leads l ON l.id = c.lead_id
            LEFT JOIN client_prospects p ON p.id = l.prospect_id
            WHERE c.client_id   = $1
              AND c.status      = 'active'
              AND c.renewal_date IS NOT NULL
              AND c.renewal_date BETWEEN CURRENT_DATE AND CURRENT_DATE + $2
            ORDER BY c.renewal_date ASC
            """,
            client_id,
            days,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_contracts_nearing_renewal(client_id={client_id}): {e}")
        return []


# ---------------------------------------------------------------------------
# Phase 10: Pipeline Agent DB functions
# ---------------------------------------------------------------------------


async def get_approved_leads(
    pool: asyncpg.Pool, client_id: str, brand_id: str
) -> list[dict]:
    """Return leads with stage='identified' (approved by Orchestrator) that have
    no existing outreach sequence yet."""
    try:
        rows = await pool.fetch(
            """
            SELECT l.id, l.client_id, l.brand_id, l.prospect_id,
                   l.stage, l.contract_value_estimate, l.created_at,
                   p.name AS prospect_name, p.website, p.industry,
                   p.size_signal, p.location, p.qualification_score,
                   p.fit_signals, p.roi_estimate
            FROM client_leads l
            LEFT JOIN client_prospects p ON p.id = l.prospect_id
            WHERE l.client_id = $1
              AND l.brand_id  = $2
              AND l.stage     = 'identified'
              AND NOT EXISTS (
                  SELECT 1 FROM client_outreach o
                  WHERE o.lead_id = l.id
              )
            ORDER BY l.created_at ASC
            """,
            client_id,
            brand_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_approved_leads(client_id={client_id}): {e}")
        return []


async def get_outreach_sequence(pool: asyncpg.Pool, lead_id: str) -> list[dict]:
    """Return all outreach steps for a lead, ordered by step_number."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, lead_id, step_number, channel, subject, body,
                   word_count, status, sequence_type, scheduled_for, sent_at, created_at
            FROM client_outreach
            WHERE lead_id = $1
            ORDER BY step_number ASC
            """,
            lead_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_outreach_sequence(lead_id={lead_id}): {e}")
        return []


async def save_outreach_step(
    pool: asyncpg.Pool,
    client_id: str,
    brand_id: str,
    lead_id: str,
    step_data: dict,
) -> str:
    """Insert one outreach sequence step. Returns new UUID as string.

    step_data keys: step_number, sequence_type, channel, subject, body,
                    word_count, status, scheduled_for (optional)
    """
    try:
        row_id = await pool.fetchval(
            """
            INSERT INTO client_outreach
                (client_id, brand_id, lead_id, sequence_type, step_number,
                 channel, subject, body, word_count, status, scheduled_for)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (lead_id, step_number) DO NOTHING
            RETURNING id
            """,
            client_id,
            brand_id,
            lead_id,
            step_data.get("sequence_type", "new_acquisition"),
            int(step_data["step_number"]),
            step_data.get("channel", "email"),
            step_data.get("subject"),
            step_data["body"],
            step_data.get("word_count"),
            step_data.get("status", "draft"),
            step_data.get("scheduled_for"),
        )
        return str(row_id) if row_id else ""
    except Exception as e:
        print(f"[DB Error] save_outreach_step(lead_id={lead_id}, step={step_data.get('step_number')}): {e}")
        return ""


async def get_due_outreach_steps(pool: asyncpg.Pool, client_id: str) -> list[dict]:
    """Return approved outreach steps whose scheduled_for is in the past (due to send).

    Joins to client_leads to include prospect context.
    """
    try:
        rows = await pool.fetch(
            """
            SELECT o.id, o.client_id, o.brand_id, o.lead_id, o.step_number,
                   o.sequence_type, o.channel, o.subject, o.body,
                   o.word_count, o.status, o.scheduled_for,
                   l.stage AS lead_stage,
                   p.name AS prospect_name
            FROM client_outreach o
            JOIN client_leads l ON l.id = o.lead_id
            LEFT JOIN client_prospects p ON p.id = l.prospect_id
            WHERE o.client_id   = $1
              AND o.status      = 'approved'
              AND (o.scheduled_for IS NULL OR o.scheduled_for <= NOW())
            ORDER BY o.scheduled_for ASC NULLS FIRST
            """,
            client_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_due_outreach_steps(client_id={client_id}): {e}")
        return []


async def mark_outreach_sent(pool: asyncpg.Pool, outreach_id: str) -> None:
    """Update an outreach step: status → sent, sent_at → now."""
    try:
        await pool.execute(
            """
            UPDATE client_outreach
            SET status = 'sent', sent_at = NOW()
            WHERE id = $1
            """,
            outreach_id,
        )
    except Exception as e:
        print(f"[DB Error] mark_outreach_sent(outreach_id={outreach_id}): {e}")
        raise


async def get_draft_steps_due_for_promotion(
    pool: asyncpg.Pool, client_id: str
) -> list[dict]:
    """Return draft outreach steps whose scheduled_for <= now AND whose
    previous step (step_number - 1) is 'sent'.

    These are ready to be promoted to pending_approval.
    """
    try:
        rows = await pool.fetch(
            """
            SELECT o.id, o.client_id, o.brand_id, o.lead_id, o.step_number,
                   o.sequence_type, o.channel, o.subject, o.body, o.word_count,
                   o.scheduled_for, p.name AS prospect_name
            FROM client_outreach o
            LEFT JOIN client_leads l ON l.id = o.lead_id
            LEFT JOIN client_prospects p ON p.id = l.prospect_id
            WHERE o.client_id = $1
              AND o.status    = 'draft'
              AND (o.scheduled_for IS NULL OR o.scheduled_for <= NOW())
              AND EXISTS (
                  SELECT 1 FROM client_outreach prev
                  WHERE prev.lead_id     = o.lead_id
                    AND prev.step_number = o.step_number - 1
                    AND prev.status      = 'sent'
              )
            ORDER BY o.scheduled_for ASC NULLS FIRST
            """,
            client_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_draft_steps_due_for_promotion(client_id={client_id}): {e}")
        return []


async def update_outreach_status(
    pool: asyncpg.Pool, outreach_id: str, status: str
) -> None:
    """Set status on an outreach step (draft → pending_approval, etc.)."""
    try:
        await pool.execute(
            "UPDATE client_outreach SET status = $1 WHERE id = $2",
            status,
            outreach_id,
        )
    except Exception as e:
        print(f"[DB Error] update_outreach_status(outreach_id={outreach_id}): {e}")
        raise


# =============================================================================
# Phase 11: Customer Care Agent
# =============================================================================


async def get_new_feedback(
    pool: asyncpg.Pool, client_id: str, brand_id: str
) -> list[dict]:
    """Return all unprocessed (status='new') feedback for a brand."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, client_id, brand_id, channel, text, status, created_at
            FROM client_feedback
            WHERE client_id = $1
              AND brand_id  = $2
              AND status    = 'new'
            ORDER BY created_at ASC
            """,
            client_id,
            brand_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_new_feedback(client_id={client_id}): {e}")
        return []


async def save_feedback_classification(
    pool: asyncpg.Pool, feedback_id: str, classification_data: dict
) -> None:
    """Update a feedback row with classification results and response draft.

    classification_data keys: feedback_type, urgency, sentiment_score,
    is_at_risk_flag, response_draft, status (defaults to 'pending_approval').
    """
    try:
        await pool.execute(
            """
            UPDATE client_feedback
            SET feedback_type   = $1,
                urgency         = $2,
                sentiment_score = $3,
                is_at_risk_flag = $4,
                response_draft  = $5,
                status          = $6
            WHERE id = $7
            """,
            classification_data.get("feedback_type"),
            classification_data.get("urgency", "normal"),
            classification_data.get("sentiment_score"),
            bool(classification_data.get("is_at_risk_flag", False)),
            classification_data.get("response_draft"),
            classification_data.get("status", "pending_approval"),
            feedback_id,
        )
    except Exception as e:
        print(f"[DB Error] save_feedback_classification(feedback_id={feedback_id}): {e}")
        raise


async def save_testimonial(
    pool: asyncpg.Pool, client_id: str, brand_id: str, feedback_id: str, quote: str
) -> str | None:
    """Insert a pending-permission testimonial row. Returns new id or None."""
    try:
        row = await pool.fetchrow(
            """
            INSERT INTO client_testimonials
                (client_id, brand_id, feedback_id, quote_original, status)
            VALUES ($1, $2, $3, $4, 'pending_permission')
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            client_id,
            brand_id,
            feedback_id,
            quote,
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(f"[DB Error] save_testimonial(feedback_id={feedback_id}): {e}")
        return None


async def get_competitors(
    pool: asyncpg.Pool, client_id: str, brand_id: str
) -> list[dict]:
    """Return all active competitors for a brand."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, client_id, brand_id, name, website_url,
                   instagram_handle, google_maps_place_id
            FROM client_competitors
            WHERE client_id = $1
              AND brand_id  = $2
              AND is_active = TRUE
            ORDER BY name
            """,
            client_id,
            brand_id,
        )
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB Error] get_competitors(client_id={client_id}): {e}")
        return []


async def save_competitor_snapshot(
    pool: asyncpg.Pool,
    client_id: str,
    competitor_id: str,
    snapshot_data: dict,
) -> None:
    """Upsert a monthly competitor snapshot (unique on competitor_id + snapshot_month)."""
    import json as _json
    try:
        await pool.execute(
            """
            INSERT INTO client_competitor_snapshots
                (client_id, competitor_id, snapshot_month, website_summary,
                 google_rating, google_reviews_sample, instagram_data,
                 actual_strengths, actual_weaknesses, positioning_summary)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (competitor_id, snapshot_month)
            DO UPDATE SET
                website_summary       = EXCLUDED.website_summary,
                google_rating         = EXCLUDED.google_rating,
                google_reviews_sample = EXCLUDED.google_reviews_sample,
                instagram_data        = EXCLUDED.instagram_data,
                actual_strengths      = EXCLUDED.actual_strengths,
                actual_weaknesses     = EXCLUDED.actual_weaknesses,
                positioning_summary   = EXCLUDED.positioning_summary
            """,
            client_id,
            competitor_id,
            snapshot_data.get("snapshot_month"),
            snapshot_data.get("website_summary"),
            snapshot_data.get("google_rating"),
            _json.dumps(snapshot_data.get("google_reviews_sample") or []),
            _json.dumps(snapshot_data.get("instagram_data") or {}),
            snapshot_data.get("actual_strengths") or [],
            snapshot_data.get("actual_weaknesses") or [],
            snapshot_data.get("positioning_summary"),
        )
    except Exception as e:
        print(f"[DB Error] save_competitor_snapshot(competitor_id={competitor_id}): {e}")
        raise


async def save_strategic_report(
    pool: asyncpg.Pool, client_id: str, brand_id: str, report_data: dict
) -> str | None:
    """Insert a strategic report (status=pending_approval). Returns new id or None."""
    import json as _json
    try:
        row = await pool.fetchrow(
            """
            INSERT INTO client_strategic_reports
                (client_id, brand_id, competitors_analysed, landscape_summary,
                 universal_complaints, unserved_needs, opportunities,
                 executive_summary, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending_approval')
            RETURNING id
            """,
            client_id,
            brand_id,
            int(report_data.get("competitors_analysed", 0)),
            report_data.get("landscape_summary"),
            report_data.get("universal_complaints") or [],
            report_data.get("unserved_needs") or [],
            _json.dumps(report_data.get("opportunities") or []),
            report_data.get("executive_summary"),
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(f"[DB Error] save_strategic_report(client_id={client_id}): {e}")
        return None


# ---------------------------------------------------------------------------
# Phase 12: Broadcast Agent — social posts + comments
# ---------------------------------------------------------------------------

async def save_social_post(
    pool: asyncpg.Pool, client_id: str, brand_id: str, post_data: dict
) -> str | None:
    """Insert a draft social post (status=pending_approval). Returns new id or None."""
    try:
        row = await pool.fetchrow(
            """
            INSERT INTO client_social_posts
                (client_id, brand_id, platform, post_type, content_pillar,
                 caption, caption_secondary_language, visual_brief, hashtags,
                 status, scheduled_for)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending_approval', $10)
            RETURNING id
            """,
            client_id,
            brand_id,
            post_data.get("platform"),
            post_data.get("post_type"),
            post_data.get("content_pillar"),
            post_data.get("caption"),
            post_data.get("caption_secondary_language"),
            post_data.get("visual_brief"),
            post_data.get("hashtags") or [],
            post_data.get("scheduled_for"),
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(f"[DB Error] save_social_post(client_id={client_id}): {e}")
        return None


async def get_approved_posts(pool: asyncpg.Pool, client_id: str) -> list[dict]:
    """Return approved posts with scheduled_for <= now (ready to publish)."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, client_id, brand_id, platform, caption,
                   caption_secondary_language, hashtags, scheduled_for
            FROM client_social_posts
            WHERE client_id = $1
              AND status = 'approved'
              AND scheduled_for <= NOW()
            ORDER BY scheduled_for ASC
            """,
            client_id,
        )
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB Error] get_approved_posts(client_id={client_id}): {e}")
        return []


async def update_post_status(
    pool: asyncpg.Pool, post_id: str, status: str
) -> None:
    """Update the status of a social post (e.g. 'published' or 'failed')."""
    try:
        published_at_clause = ", published_at = NOW()" if status == "published" else ""
        await pool.execute(
            f"UPDATE client_social_posts SET status = $1{published_at_clause} WHERE id = $2",
            status,
            post_id,
        )
    except Exception as e:
        print(f"[DB Error] update_post_status(post_id={post_id}): {e}")


async def update_post_engagement(
    pool: asyncpg.Pool, post_id: str, metrics: dict
) -> None:
    """Update engagement counters on a published post."""
    try:
        await pool.execute(
            """
            UPDATE client_social_posts
            SET likes_count          = $1,
                comments_count       = $2,
                reach                = $3,
                impressions          = $4,
                engagement_rate      = $5,
                last_engagement_sync = NOW()
            WHERE id = $6
            """,
            int(metrics.get("likes_count", 0)),
            int(metrics.get("comments_count", 0)),
            int(metrics.get("reach", 0)),
            int(metrics.get("impressions", 0)),
            float(metrics.get("engagement_rate", 0.0)),
            post_id,
        )
    except Exception as e:
        print(f"[DB Error] update_post_engagement(post_id={post_id}): {e}")


async def get_recent_comments(
    pool: asyncpg.Pool, client_id: str, brand_id: str, since_iso: str
) -> list[dict]:
    """Return unprocessed (new) social comments since the given ISO timestamp."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, post_id, platform_comment_id, text, created_at
            FROM client_social_comments
            WHERE client_id = $1
              AND brand_id  = $2
              AND status    = 'pending_approval'
              AND created_at >= $3::timestamptz
            ORDER BY created_at ASC
            """,
            client_id,
            brand_id,
            since_iso,
        )
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB Error] get_recent_comments(client_id={client_id}): {e}")
        return []


async def save_comment_classification(
    pool: asyncpg.Pool, comment_id: str, classification_data: dict
) -> None:
    """Save sentiment, reply draft, and escalation info on a social comment."""
    try:
        await pool.execute(
            """
            UPDATE client_social_comments
            SET sentiment         = $1,
                requires_reply    = $2,
                reply_draft       = $3,
                status            = $4,
                escalation_reason = $5
            WHERE id = $6
            """,
            classification_data.get("sentiment"),
            bool(classification_data.get("requires_reply", False)),
            classification_data.get("reply_draft"),
            "escalated" if classification_data.get("escalate_to_human") else "pending_approval",
            classification_data.get("escalation_reason"),
            comment_id,
        )
    except Exception as e:
        print(f"[DB Error] save_comment_classification(comment_id={comment_id}): {e}")


# ---------------------------------------------------------------------------
# Phase 13: SEO Engine Agent — DB helpers
# ---------------------------------------------------------------------------


async def get_priority_keywords(
    pool: asyncpg.Pool, brand_id: str, limit: int = 4
) -> list[dict]:
    """Return keywords with status='identified', ordered by is_priority DESC."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, brand_id, keyword, intent, cluster_topic, is_priority, status
            FROM brand_keywords
            WHERE brand_id = $1
              AND status   = 'identified'
            ORDER BY is_priority DESC, created_at ASC
            LIMIT $2
            """,
            brand_id,
            limit,
        )
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB Error] get_priority_keywords(brand_id={brand_id}): {e}")
        return []


async def get_published_slugs(
    pool: asyncpg.Pool, client_id: str, brand_id: str
) -> list[str]:
    """Return slugs of all published (or approved) SEO articles to prevent duplication."""
    try:
        rows = await pool.fetch(
            """
            SELECT slug
            FROM client_seo_content
            WHERE client_id = $1
              AND brand_id  = $2
              AND status    IN ('approved', 'published')
            """,
            client_id,
            brand_id,
        )
        return [r["slug"] for r in rows]
    except Exception as e:
        print(f"[DB Error] get_published_slugs(client_id={client_id}): {e}")
        return []


async def save_seo_article(
    pool: asyncpg.Pool,
    client_id: str,
    brand_id: str,
    keyword_id: Optional[str],
    article_data: dict,
) -> str | None:
    """Insert an SEO article as pending_approval. Returns new UUID or None."""
    try:
        row = await pool.fetchrow(
            """
            INSERT INTO client_seo_content
                (client_id, brand_id, keyword_id, title, slug, content_markdown,
                 meta_title, meta_description, schema_markup,
                 word_count, seo_score, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11, 'pending_approval')
            ON CONFLICT (client_id, brand_id, slug) DO NOTHING
            RETURNING id
            """,
            client_id,
            brand_id,
            keyword_id,
            article_data.get("title"),
            article_data.get("slug"),
            article_data.get("content_markdown"),
            article_data.get("meta_title"),
            article_data.get("meta_description"),
            json.dumps(article_data.get("schema_markup") or {}),
            article_data.get("word_count"),
            article_data.get("seo_score"),
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(f"[DB Error] save_seo_article(client_id={client_id}, slug={article_data.get('slug')}): {e}")
        return None


async def update_keyword_status(
    pool: asyncpg.Pool, keyword_id: str, status: str
) -> None:
    """Update a brand_keyword row's status (identified → in_progress → published)."""
    try:
        await pool.execute(
            "UPDATE brand_keywords SET status = $1 WHERE id = $2",
            status,
            keyword_id,
        )
    except Exception as e:
        print(f"[DB Error] update_keyword_status(keyword_id={keyword_id}): {e}")


async def save_keyword_cluster(
    pool: asyncpg.Pool, brand_id: str, keywords: list[dict]
) -> int:
    """Insert new keyword cluster rows, skipping duplicates. Returns count inserted."""
    inserted = 0
    for kw in keywords:
        try:
            result = await pool.execute(
                """
                INSERT INTO brand_keywords
                    (brand_id, keyword, intent, cluster_topic, is_priority, status)
                VALUES ($1, $2, $3, $4, $5, 'identified')
                ON CONFLICT DO NOTHING
                """,
                brand_id,
                kw.get("keyword"),
                kw.get("intent"),
                kw.get("cluster_topic"),
                bool(kw.get("is_priority", False)),
            )
            if result and result != "INSERT 0 0":
                inserted += 1
        except Exception as e:
            print(f"[DB Error] save_keyword_cluster(brand_id={brand_id}, kw={kw.get('keyword')}): {e}")
    return inserted


# ---------------------------------------------------------------------------
# Phase 14A: Sales Outreach Agent — DB helpers
# ---------------------------------------------------------------------------


async def get_new_company_leads(
    pool: asyncpg.Pool, limit: int = 30
) -> list[dict]:
    """Return company leads with status='new' that have not yet been emailed."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, apollo_id, company_name, owner_name, owner_email,
                   phone, website, location, employee_count, industry,
                   pain_points, qualification_score, fit_signals, source
            FROM company_leads
            WHERE status = 'new'
              AND owner_email IS NOT NULL
            ORDER BY qualification_score DESC, created_at ASC
            LIMIT $1
            """,
            limit,
        )
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB Error] get_new_company_leads: {e}")
        return []


async def save_company_lead(
    pool: asyncpg.Pool, lead_data: dict
) -> Optional[str]:
    """Upsert a company lead from Apollo.io. Returns UUID or None on conflict."""
    try:
        row = await pool.fetchrow(
            """
            INSERT INTO company_leads
                (apollo_id, company_name, owner_name, owner_email, phone,
                 website, location, employee_count, industry, source)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (apollo_id) DO NOTHING
            RETURNING id
            """,
            lead_data.get("apollo_id"),
            lead_data.get("company_name"),
            lead_data.get("owner_name"),
            lead_data.get("owner_email"),
            lead_data.get("phone"),
            lead_data.get("website"),
            lead_data.get("location"),
            lead_data.get("employee_count"),
            lead_data.get("industry"),
            lead_data.get("source", "apollo"),
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(f"[DB Error] save_company_lead(company={lead_data.get('company_name')}): {e}")
        return None


async def update_company_lead_score(
    pool: asyncpg.Pool,
    lead_id: str,
    score: float,
    fit_signals: dict,
    pain_points: list[str],
) -> None:
    """Update qualification score and signals on a company lead."""
    try:
        await pool.execute(
            """
            UPDATE company_leads
            SET qualification_score = $1,
                fit_signals          = $2::jsonb,
                pain_points          = $3
            WHERE id = $4
            """,
            score,
            json.dumps(fit_signals),
            pain_points,
            lead_id,
        )
    except Exception as e:
        print(f"[DB Error] update_company_lead_score(lead_id={lead_id}): {e}")


async def save_outreach_draft(
    pool: asyncpg.Pool,
    lead_id: str,
    sequence_step: int,
    subject: str,
    body: str,
    scheduled_for,
) -> Optional[str]:
    """Save a cold email draft for a company lead. Returns UUID or None."""
    try:
        row = await pool.fetchrow(
            """
            INSERT INTO company_outreach
                (lead_id, sequence_step, subject, body, status, scheduled_for)
            VALUES ($1, $2, $3, $4, 'approved', $5)
            ON CONFLICT (lead_id, sequence_step) DO NOTHING
            RETURNING id
            """,
            lead_id,
            sequence_step,
            subject,
            body,
            scheduled_for,
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(f"[DB Error] save_outreach_draft(lead_id={lead_id}): {e}")
        return None


async def get_approved_outreach_batch(
    pool: asyncpg.Pool, limit: int = 20
) -> list[dict]:
    """Return approved outreach steps with scheduled_for <= now, up to batch limit."""
    try:
        rows = await pool.fetch(
            """
            SELECT o.id, o.lead_id, o.sequence_step, o.subject, o.body,
                   l.owner_name, l.owner_email, l.company_name
            FROM company_outreach o
            JOIN company_leads l ON l.id = o.lead_id
            WHERE o.status = 'approved'
              AND o.scheduled_for <= NOW()
              AND l.status NOT IN ('unsubscribed', 'lost')
              AND l.owner_email IS NOT NULL
            ORDER BY o.scheduled_for ASC
            LIMIT $1
            """,
            limit,
        )
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB Error] get_approved_outreach_batch: {e}")
        return []


async def mark_company_outreach_sent(
    pool: asyncpg.Pool, outreach_id: str, resend_email_id: str
) -> None:
    """Mark a company outreach step as sent and record the Resend email ID."""
    try:
        await pool.execute(
            """
            UPDATE company_outreach
            SET status          = 'sent',
                sent_at         = NOW(),
                resend_email_id = $2
            WHERE id = $1
            """,
            outreach_id,
            resend_email_id,
        )
        # Also update the lead's last_contacted_at
        await pool.execute(
            """
            UPDATE company_leads
            SET last_contacted_at = NOW(),
                status            = CASE WHEN status = 'new' THEN 'emailed' ELSE status END
            WHERE id = (SELECT lead_id FROM company_outreach WHERE id = $1)
            """,
            outreach_id,
        )
    except Exception as e:
        print(f"[DB Error] mark_company_outreach_sent(outreach_id={outreach_id}): {e}")


async def record_email_engagement(
    pool: asyncpg.Pool, resend_email_id: str, event: str
) -> None:
    """Record an open or click event on a company outreach email (from Resend webhook).

    event: 'open' | 'click'
    """
    try:
        if event == "open":
            await pool.execute(
                """
                UPDATE company_outreach SET opened_at = NOW() WHERE resend_email_id = $1
                """,
                resend_email_id,
            )
            await pool.execute(
                """
                UPDATE company_leads SET email_opens = email_opens + 1
                WHERE id = (SELECT lead_id FROM company_outreach WHERE resend_email_id = $1)
                """,
                resend_email_id,
            )
        elif event == "click":
            await pool.execute(
                """
                UPDATE company_outreach SET clicked_at = NOW() WHERE resend_email_id = $1
                """,
                resend_email_id,
            )
            await pool.execute(
                """
                UPDATE company_leads SET email_clicks = email_clicks + 1
                WHERE id = (SELECT lead_id FROM company_outreach WHERE resend_email_id = $1)
                """,
                resend_email_id,
            )
    except Exception as e:
        print(f"[DB Error] record_email_engagement(resend_id={resend_email_id}, event={event}): {e}")


# ---------------------------------------------------------------------------
# Phase 14B: Marketing Content Agent — DB helpers
# ---------------------------------------------------------------------------


async def get_pending_marketing_keywords(
    pool: asyncpg.Pool, limit: int = 3
) -> list[dict]:
    """Return company marketing keywords with status='identified', priority first."""
    try:
        rows = await pool.fetch(
            """
            SELECT id, keyword, intent, cluster_topic, is_priority, status
            FROM company_marketing_keywords
            WHERE status = 'identified'
            ORDER BY is_priority DESC, created_at ASC
            LIMIT $1
            """,
            limit,
        )
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB Error] get_pending_marketing_keywords: {e}")
        return []


async def get_published_blog_slugs(pool: asyncpg.Pool) -> list[str]:
    """Return slugs of all approved or published blog posts (to avoid duplication)."""
    try:
        rows = await pool.fetch(
            """
            SELECT slug
            FROM company_blog_posts
            WHERE status IN ('approved', 'published', 'pending_approval')
            """
        )
        return [r["slug"] for r in rows]
    except Exception as e:
        print(f"[DB Error] get_published_blog_slugs: {e}")
        return []


async def save_blog_post(
    pool: asyncpg.Pool, keyword_id: Optional[str], post_data: dict
) -> Optional[str]:
    """Insert a generated blog post as pending_approval. Returns UUID or None."""
    try:
        row = await pool.fetchrow(
            """
            INSERT INTO company_blog_posts
                (keyword_id, title, slug, content_markdown,
                 meta_title, meta_description, word_count, seo_score)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (slug) DO NOTHING
            RETURNING id
            """,
            keyword_id,
            post_data.get("title"),
            post_data.get("slug"),
            post_data.get("content_markdown"),
            post_data.get("meta_title"),
            post_data.get("meta_description"),
            post_data.get("word_count"),
            post_data.get("seo_score"),
        )
        return str(row["id"]) if row else None
    except Exception as e:
        print(f"[DB Error] save_blog_post(slug={post_data.get('slug')}): {e}")
        return None


async def update_marketing_keyword_status(
    pool: asyncpg.Pool, keyword_id: str, status: str
) -> None:
    """Update a company_marketing_keywords status (identified → in_progress → published)."""
    try:
        await pool.execute(
            "UPDATE company_marketing_keywords SET status = $1 WHERE id = $2",
            status,
            keyword_id,
        )
    except Exception as e:
        print(f"[DB Error] update_marketing_keyword_status(keyword_id={keyword_id}): {e}")


async def save_marketing_keyword_cluster(
    pool: asyncpg.Pool, keywords: list[dict]
) -> int:
    """Insert new company marketing keywords, skipping duplicates. Returns count inserted."""
    inserted = 0
    for kw in keywords:
        try:
            result = await pool.execute(
                """
                INSERT INTO company_marketing_keywords
                    (keyword, intent, cluster_topic, is_priority, status)
                VALUES ($1, $2, $3, $4, 'identified')
                ON CONFLICT (keyword) DO NOTHING
                """,
                kw.get("keyword"),
                kw.get("intent"),
                kw.get("cluster_topic"),
                bool(kw.get("is_priority", False)),
            )
            if result and result != "INSERT 0 0":
                inserted += 1
        except Exception as e:
            print(f"[DB Error] save_marketing_keyword_cluster(kw={kw.get('keyword')}): {e}")
    return inserted
