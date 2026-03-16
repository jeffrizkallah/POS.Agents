"""Revenue metrics for the weekly analytics report (Phase 6C)."""

import asyncpg
from datetime import date


async def get_revenue_metrics(
    pool: asyncpg.Pool, restaurant_id: str, week_start: date, week_end: date
) -> dict:
    """Compute all revenue metrics for a restaurant over the given week window.

    Returns a dict matching weekly_report_snapshots revenue columns.
    All values COALESCE to 0 on NULL. Handles missing tables gracefully.
    """
    try:
        # Core revenue + covers for this week
        revenue_row = await pool.fetchrow(
            """
            SELECT
                COALESCE(SUM(oi.quantity * mi.price), 0)    AS gross_revenue,
                COUNT(DISTINCT o.id)                         AS total_covers,
                COALESCE(
                    SUM(oi.quantity * mi.price) / NULLIF(COUNT(DISTINCT o.id), 0),
                    0
                )                                            AS avg_spend_per_cover
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN menu_items  mi ON mi.id = oi.menu_item_id
            WHERE o.restaurant_id = $1
              AND o.created_at >= $2
              AND o.created_at <  $3
              AND o.status NOT IN ('cancelled', 'voided')
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        gross_revenue = float(revenue_row["gross_revenue"] or 0)
        total_covers = int(revenue_row["total_covers"] or 0)
        avg_spend = float(revenue_row["avg_spend_per_cover"] or 0)

        # Previous week revenue (for WoW comparison)
        from datetime import timedelta
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = week_start
        prev_row = await pool.fetchrow(
            """
            SELECT COALESCE(SUM(oi.quantity * mi.price), 0) AS revenue
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN menu_items  mi ON mi.id = oi.menu_item_id
            WHERE o.restaurant_id = $1
              AND o.created_at >= $2
              AND o.created_at <  $3
              AND o.status NOT IN ('cancelled', 'voided')
            """,
            restaurant_id,
            prev_week_start,
            prev_week_end,
        )
        prev_week_revenue = float(prev_row["revenue"] or 0)
        revenue_wow_pct = (
            round((gross_revenue - prev_week_revenue) / prev_week_revenue * 100, 2)
            if prev_week_revenue > 0
            else 0.0
        )

        # Month-over-month: compare this week vs same-week four weeks ago
        mom_start = week_start - timedelta(days=28)
        mom_end = week_end - timedelta(days=28)
        mom_row = await pool.fetchrow(
            """
            SELECT COALESCE(SUM(oi.quantity * mi.price), 0) AS revenue
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN menu_items  mi ON mi.id = oi.menu_item_id
            WHERE o.restaurant_id = $1
              AND o.created_at >= $2
              AND o.created_at <  $3
              AND o.status NOT IN ('cancelled', 'voided')
            """,
            restaurant_id,
            mom_start,
            mom_end,
        )
        mom_revenue = float(mom_row["revenue"] or 0)
        revenue_mom_pct = (
            round((gross_revenue - mom_revenue) / mom_revenue * 100, 2)
            if mom_revenue > 0
            else 0.0
        )

        # Void count + void rate
        void_row = await pool.fetchrow(
            """
            SELECT COUNT(*) AS void_count
            FROM orders
            WHERE restaurant_id = $1
              AND created_at >= $2
              AND created_at <  $3
              AND status = 'voided'
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        void_count = int(void_row["void_count"] or 0)
        total_with_voids = total_covers + void_count
        void_rate_pct = (
            round(void_count / total_with_voids * 100, 2)
            if total_with_voids > 0
            else 0.0
        )

        # Peak hour (0-23) by revenue
        peak_row = await pool.fetchrow(
            """
            SELECT
                EXTRACT(HOUR FROM o.created_at)::int          AS peak_hour,
                COALESCE(SUM(oi.quantity * mi.price), 0)       AS peak_revenue
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN menu_items  mi ON mi.id = oi.menu_item_id
            WHERE o.restaurant_id = $1
              AND o.created_at >= $2
              AND o.created_at <  $3
              AND o.status NOT IN ('cancelled', 'voided')
            GROUP BY EXTRACT(HOUR FROM o.created_at)
            ORDER BY peak_revenue DESC
            LIMIT 1
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        peak_hour = int(peak_row["peak_hour"]) if peak_row else None
        peak_hour_revenue = float(peak_row["peak_revenue"]) if peak_row else 0.0

        return {
            "gross_revenue": round(gross_revenue, 2),
            "total_covers": total_covers,
            "avg_spend_per_cover": round(avg_spend, 2),
            "revenue_wow_pct": revenue_wow_pct,
            "revenue_mom_pct": revenue_mom_pct,
            "void_count": void_count,
            "void_rate_pct": void_rate_pct,
            "peak_hour": peak_hour,
            "peak_hour_revenue": round(peak_hour_revenue, 2),
        }

    except Exception as e:
        print(f"[Metrics Error] get_revenue_metrics(restaurant_id={restaurant_id}): {e}")
        return {
            "gross_revenue": 0.0,
            "total_covers": 0,
            "avg_spend_per_cover": 0.0,
            "revenue_wow_pct": 0.0,
            "revenue_mom_pct": 0.0,
            "void_count": 0,
            "void_rate_pct": 0.0,
            "peak_hour": None,
            "peak_hour_revenue": 0.0,
        }


async def get_revenue_by_category(
    pool: asyncpg.Pool, restaurant_id: str, week_start: date, week_end: date
) -> list:
    """Revenue breakdown by menu category, sorted by revenue desc.

    Returns list of {category, revenue, pct_of_total}.
    """
    try:
        rows = await pool.fetch(
            """
            SELECT
                COALESCE(mc.name, 'Uncategorised')  AS category,
                SUM(oi.quantity * mi.price)          AS revenue
            FROM orders o
            JOIN order_items     oi ON oi.order_id   = o.id
            JOIN menu_items      mi ON mi.id          = oi.menu_item_id
            LEFT JOIN menu_categories mc ON mc.id     = mi.category_id
            WHERE o.restaurant_id = $1
              AND o.created_at >= $2
              AND o.created_at <  $3
              AND o.status NOT IN ('cancelled', 'voided')
            GROUP BY mc.name
            ORDER BY revenue DESC
            """,
            restaurant_id,
            week_start,
            week_end,
        )
        total = sum(float(r["revenue"] or 0) for r in rows)
        return [
            {
                "category": r["category"],
                "revenue": round(float(r["revenue"] or 0), 2),
                "pct_of_total": round(float(r["revenue"] or 0) / total * 100, 1)
                if total > 0
                else 0.0,
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[Metrics Error] get_revenue_by_category(restaurant_id={restaurant_id}): {e}")
        return []
