"""Platform-wide metrics for the weekly intelligence briefing (Phase 6G).

All functions are platform-wide (no restaurant_id filter).
Tables like subscriptions and client_health_scores are queried defensively.
"""

import asyncpg
from datetime import date


async def get_platform_metrics(
    pool: asyncpg.Pool, week_start: date, week_end: date
) -> dict:
    """Platform-wide aggregates for the given week window.

    Returns a dict matching platform_weekly_summaries columns.
    All sub-queries are wrapped defensively — missing tables return 0.
    """
    result = {
        "total_active_clients": 0,
        "total_mrr": 0.0,
        "mrr_at_risk": 0.0,
        "avg_client_health": 0.0,
        "new_clients_this_week": 0,
        "churned_this_week": 0,
        "total_platform_revenue": 0.0,
        "total_platform_covers": 0,
        "avg_food_cost_pct": 0.0,
        "agent_total_runs": 0,
        "feature_adoption_pct": 0.0,
        "clients_by_band": {},
    }

    # Total active clients
    try:
        row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM subscriptions
            WHERE status IN ('active', 'trialing')
            """
        )
        result["total_active_clients"] = int(row["cnt"] or 0)
    except Exception:
        # Fall back to restaurant count
        try:
            row = await pool.fetchrow("SELECT COUNT(*) AS cnt FROM restaurants")
            result["total_active_clients"] = int(row["cnt"] or 0)
        except Exception:
            pass

    # Total MRR
    try:
        row = await pool.fetchrow(
            """
            SELECT COALESCE(SUM(mrr), 0) AS total_mrr
            FROM subscriptions
            WHERE status IN ('active', 'trialing')
            """
        )
        result["total_mrr"] = float(row["total_mrr"] or 0)
    except Exception:
        pass

    # MRR at risk (from client_health_scores if it exists)
    try:
        row = await pool.fetchrow(
            """
            SELECT COALESCE(SUM(s.mrr), 0) AS mrr_at_risk
            FROM subscriptions s
            JOIN client_health_scores chs ON chs.restaurant_id = s.restaurant_id
            WHERE s.status IN ('active', 'trialing')
              AND chs.score_band IN ('at_risk', 'critical', 'churning')
              AND chs.score_date = CURRENT_DATE
            """
        )
        result["mrr_at_risk"] = float(row["mrr_at_risk"] or 0)
    except Exception:
        pass

    # Average client health score
    try:
        row = await pool.fetchrow(
            """
            SELECT AVG(total_score) AS avg_health
            FROM client_health_scores
            WHERE score_date = CURRENT_DATE
            """
        )
        if row and row["avg_health"] is not None:
            result["avg_client_health"] = round(float(row["avg_health"]), 1)
    except Exception:
        pass

    # Clients by health band
    try:
        rows = await pool.fetch(
            """
            SELECT score_band, COUNT(*) AS cnt
            FROM client_health_scores
            WHERE score_date = CURRENT_DATE
            GROUP BY score_band
            """
        )
        result["clients_by_band"] = {r["score_band"]: int(r["cnt"]) for r in rows}
    except Exception:
        pass

    # New clients this week
    try:
        row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM subscriptions
            WHERE created_at >= $1 AND created_at < $2
            """,
            week_start,
            week_end,
        )
        result["new_clients_this_week"] = int(row["cnt"] or 0)
    except Exception:
        pass

    # Churned this week
    try:
        row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM subscriptions
            WHERE status = 'cancelled'
              AND updated_at >= $1 AND updated_at < $2
            """,
            week_start,
            week_end,
        )
        result["churned_this_week"] = int(row["cnt"] or 0)
    except Exception:
        pass

    # Total platform revenue (all restaurants)
    try:
        row = await pool.fetchrow(
            """
            SELECT
                COALESCE(SUM(oi.quantity * mi.price), 0) AS total_revenue,
                COUNT(DISTINCT o.id)                      AS total_covers
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN menu_items  mi ON mi.id = oi.menu_item_id
            WHERE o.created_at >= $1
              AND o.created_at <  $2
              AND o.status NOT IN ('cancelled', 'voided')
            """,
            week_start,
            week_end,
        )
        result["total_platform_revenue"] = round(float(row["total_revenue"] or 0), 2)
        result["total_platform_covers"] = int(row["total_covers"] or 0)
    except Exception as e:
        print(f"[Platform Metrics] Revenue query failed: {e}")

    # Average food cost % across platform
    try:
        row = await pool.fetchrow(
            """
            SELECT AVG(food_cost_pct) AS avg_pct
            FROM food_cost_snapshots
            WHERE snapshot_date >= $1 AND snapshot_date < $2
            """,
            week_start,
            week_end,
        )
        if row and row["avg_pct"] is not None:
            result["avg_food_cost_pct"] = round(float(row["avg_pct"]), 2)
    except Exception:
        pass

    # Total agent runs
    try:
        row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM agent_logs
            WHERE created_at >= $1 AND created_at < $2
            """,
            week_start,
            week_end,
        )
        result["agent_total_runs"] = int(row["cnt"] or 0)
    except Exception:
        pass

    # Feature adoption: % of restaurants using pricing + POs + waste logging this week
    try:
        total_row = await pool.fetchrow("SELECT COUNT(*) AS cnt FROM restaurants")
        total = int(total_row["cnt"] or 0)

        if total > 0:
            using_pricing = await pool.fetchval(
                """
                SELECT COUNT(DISTINCT restaurant_id) FROM ai_pricing_recommendations
                WHERE created_at >= $1 AND created_at < $2
                """,
                week_start, week_end,
            )
            using_pos = await pool.fetchval(
                """
                SELECT COUNT(DISTINCT restaurant_id) FROM purchase_orders
                WHERE created_at >= $1 AND created_at < $2
                """,
                week_start, week_end,
            )
            using_waste = await pool.fetchval(
                """
                SELECT COUNT(DISTINCT restaurant_id) FROM waste_records
                WHERE created_at >= $1 AND created_at < $2
                """,
                week_start, week_end,
            )
            # % using ALL 3 features (approximate: average adoption across features)
            using_all = min(int(using_pricing or 0), int(using_pos or 0), int(using_waste or 0))
            result["feature_adoption_pct"] = round(using_all / total * 100, 1)
    except Exception:
        pass

    return result


async def get_client_league_table(
    pool: asyncpg.Pool, week_start: date, week_end: date
) -> list:
    """Per-restaurant performance league table for the platform intelligence briefing.

    Returns top restaurants ordered by gross revenue desc.
    """
    try:
        rows = await pool.fetch(
            """
            WITH revenue AS (
                SELECT
                    o.restaurant_id,
                    COALESCE(SUM(oi.quantity * mi.price), 0) AS gross_revenue,
                    COUNT(DISTINCT o.id)                      AS covers
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN menu_items  mi ON mi.id = oi.menu_item_id
                WHERE o.created_at >= $1
                  AND o.created_at <  $2
                  AND o.status NOT IN ('cancelled', 'voided')
                GROUP BY o.restaurant_id
            ),
            food_cost AS (
                SELECT
                    restaurant_id,
                    AVG(food_cost_pct) AS avg_food_cost_pct
                FROM food_cost_snapshots
                WHERE snapshot_date >= $1 AND snapshot_date < $2
                GROUP BY restaurant_id
            ),
            action_rate AS (
                SELECT
                    restaurant_id,
                    COUNT(*) FILTER (WHERE status IN ('applied', 'approved')) * 100.0
                        / NULLIF(COUNT(*), 0) AS rate
                FROM ai_pricing_recommendations
                WHERE created_at >= $1 AND created_at < $2
                GROUP BY restaurant_id
            )
            SELECT
                r.name                                          AS restaurant_name,
                COALESCE(rev.gross_revenue, 0)                  AS gross_revenue,
                COALESCE(fc.avg_food_cost_pct, 0)               AS food_cost_pct,
                COALESCE(ar.rate, 0)                            AS recommendation_action_rate
            FROM restaurants r
            LEFT JOIN revenue     rev ON rev.restaurant_id = r.id
            LEFT JOIN food_cost   fc  ON fc.restaurant_id  = r.id
            LEFT JOIN action_rate ar  ON ar.restaurant_id  = r.id
            ORDER BY gross_revenue DESC
            LIMIT 10
            """,
            week_start,
            week_end,
        )
        return [
            {
                "restaurant_name": r["restaurant_name"],
                "gross_revenue": round(float(r["gross_revenue"] or 0), 2),
                "food_cost_pct": round(float(r["food_cost_pct"] or 0), 2),
                "recommendation_action_rate": round(float(r["recommendation_action_rate"] or 0), 1),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[Platform Metrics] get_client_league_table failed: {e}")
        return []
