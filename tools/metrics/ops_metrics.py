"""Operations metrics for the weekly analytics report (Phase 6F)."""

import asyncpg
from datetime import date


async def get_ops_metrics(
    pool: asyncpg.Pool, restaurant_id: str, week_start: date, week_end: date
) -> dict:
    """Compute operational metrics for the given window.

    Returns: table_turn_rate, orders_by_hour, recommendation_action_rate,
             agent_run_count, login_frequency.
    """
    try:
        # Table turn rate: paid orders per table per day over 7 days
        # Try to count tables from a tables table; fall back to 10 as default
        table_count = 10
        try:
            table_row = await pool.fetchrow(
                "SELECT COUNT(*) AS cnt FROM tables WHERE restaurant_id = $1",
                restaurant_id,
            )
            if table_row and int(table_row["cnt"]) > 0:
                table_count = int(table_row["cnt"])
        except Exception:
            pass  # tables table may not exist — use default

        order_count_row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM orders
            WHERE restaurant_id = $1
              AND created_at >= $2
              AND created_at <  $3
              AND status NOT IN ('cancelled', 'voided')
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        weekly_orders = int(order_count_row["cnt"] or 0)
        table_turn_rate = round(weekly_orders / table_count / 7, 4)

        # Orders by hour (0-23)
        hour_rows = await pool.fetch(
            """
            SELECT
                EXTRACT(HOUR FROM created_at)::int AS hour,
                COUNT(*)::int                       AS count
            FROM orders
            WHERE restaurant_id = $1
              AND created_at >= $2
              AND created_at <  $3
              AND status NOT IN ('cancelled', 'voided')
            GROUP BY EXTRACT(HOUR FROM created_at)
            ORDER BY hour
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        # Fill in all 24 hours
        hour_map = {int(r["hour"]): int(r["count"]) for r in hour_rows}
        orders_by_hour = [{"hour": h, "count": hour_map.get(h, 0)} for h in range(24)]

        # Recommendation action rate: applied/total in window
        rec_row = await pool.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE status IN ('applied', 'approved')) AS actioned,
                COUNT(*)                                                    AS total
            FROM ai_pricing_recommendations
            WHERE restaurant_id = $1
              AND created_at >= $2
              AND created_at <  $3
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        actioned = int(rec_row["actioned"] or 0) if rec_row else 0
        total_recs = int(rec_row["total"] or 0) if rec_row else 0
        recommendation_action_rate = (
            round(actioned / total_recs * 100, 2) if total_recs > 0 else 0.0
        )

        # Agent run count from agent_logs
        agent_row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM agent_logs
            WHERE restaurant_id = $1
              AND created_at >= $2
              AND created_at <  $3
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        agent_run_count = int(agent_row["cnt"] or 0) if agent_row else 0

        # Login frequency from users.last_login (fallback if login_events doesn't exist)
        login_frequency = {"total_logins": 0, "unique_days": 0}
        try:
            login_row = await pool.fetchrow(
                """
                SELECT
                    COUNT(*) AS total_logins,
                    COUNT(DISTINCT created_at::date) AS unique_days
                FROM login_events
                WHERE restaurant_id = $1
                  AND created_at >= $2
                  AND created_at <  $3
                """,
                restaurant_id,
                week_start,
                week_end,
            )
            if login_row:
                login_frequency = {
                    "total_logins": int(login_row["total_logins"] or 0),
                    "unique_days": int(login_row["unique_days"] or 0),
                }
        except Exception:
            pass  # login_events table may not exist

        return {
            "table_turn_rate": table_turn_rate,
            "orders_by_hour": orders_by_hour,
            "recommendation_action_rate": recommendation_action_rate,
            "agent_run_count": agent_run_count,
            "login_frequency": login_frequency,
        }

    except Exception as e:
        print(f"[Metrics Error] get_ops_metrics(restaurant_id={restaurant_id}): {e}")
        return {
            "table_turn_rate": 0.0,
            "orders_by_hour": [{"hour": h, "count": 0} for h in range(24)],
            "recommendation_action_rate": 0.0,
            "agent_run_count": 0,
            "login_frequency": {"total_logins": 0, "unique_days": 0},
        }
