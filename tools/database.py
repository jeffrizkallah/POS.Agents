import asyncpg
import json
import os
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
