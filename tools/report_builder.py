"""Report builder — assembles the full weekly report package (Phase 6I).

Runs all 5 metric modules concurrently with asyncio.gather(), fetches
benchmarks, upserts the snapshot row, runs anomaly detection, and
returns the complete package dict ready for Claude + email.
"""

import asyncio
import asyncpg
from datetime import date

from tools.metrics.revenue_metrics import get_revenue_metrics, get_revenue_by_category
from tools.metrics.food_cost_metrics import get_food_cost_metrics, get_dish_performance
from tools.metrics.inventory_metrics import get_inventory_metrics, get_waste_by_ingredient
from tools.metrics.menu_metrics import get_menu_metrics, get_full_menu_performance
from tools.metrics.ops_metrics import get_ops_metrics
from tools.anomaly_detector import detect_anomalies


async def build_report_package(
    pool: asyncpg.Pool,
    restaurant_id: str,
    restaurant_name: str,
    week_start: date,
    week_end: date,
) -> dict:
    """Build the full analytics report package for one restaurant.

    Steps:
    1. Run all 5 metric modules concurrently
    2. Fetch benchmarks from metric_benchmarks
    3. Fetch previous week snapshot for comparison
    4. Compute benchmark comparisons
    5. Upsert core metrics to weekly_report_snapshots
    6. Run detect_anomalies()
    7. Return full package dict

    Returns {} on any top-level failure (caller should skip the restaurant).
    """
    try:
        # --- Step 1: Run all metrics concurrently ---
        (
            revenue,
            food_cost,
            inventory,
            menu,
            ops,
            revenue_by_category,
            dish_performance,
            waste_by_ingredient,
            full_menu,
        ) = await asyncio.gather(
            get_revenue_metrics(pool, restaurant_id, week_start, week_end),
            get_food_cost_metrics(pool, restaurant_id, week_start, week_end),
            get_inventory_metrics(pool, restaurant_id, week_start, week_end),
            get_menu_metrics(pool, restaurant_id, week_start, week_end),
            get_ops_metrics(pool, restaurant_id, week_start, week_end),
            get_revenue_by_category(pool, restaurant_id, week_start, week_end),
            get_dish_performance(pool, restaurant_id, week_start, week_end),
            get_waste_by_ingredient(pool, restaurant_id, week_start, week_end),
            get_full_menu_performance(pool, restaurant_id, week_start, week_end),
        )

        # --- Step 2: Fetch benchmarks ---
        benchmarks = await _get_benchmarks(pool)

        # --- Step 3: Fetch previous week snapshot ---
        previous_week = await _get_previous_week_snapshot(pool, restaurant_id, week_start)

        # --- Step 4: Benchmark comparisons ---
        benchmark_comparisons = _compute_benchmark_comparisons(
            revenue, food_cost, inventory, ops, benchmarks
        )

        # --- Step 5: Upsert snapshot ---
        merged = {**revenue, **food_cost, **inventory, **menu, **ops}
        await _upsert_weekly_snapshot(
            pool, restaurant_id, week_start, week_end, merged
        )

        # --- Step 6: Anomaly detection ---
        anomalies = []
        if previous_week:
            prev_merged = {
                "gross_revenue": previous_week.get("gross_revenue", 0),
                "food_cost_pct": previous_week.get("food_cost_pct", 0),
                "waste_rate_pct": previous_week.get("waste_rate_pct", 0),
                "stock_out_count": previous_week.get("stock_out_count", 0),
                "top_margin_killer_pct": None,
            }
            anomalies = await detect_anomalies(
                pool, restaurant_id, merged, prev_merged, week_start
            )
        else:
            # No prior week — still check for margin collapse
            anomalies = await detect_anomalies(pool, restaurant_id, merged, {}, week_start)

        # --- Step 7: Return package ---
        return {
            "restaurant_id": restaurant_id,
            "restaurant_name": restaurant_name,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "revenue": revenue,
            "food_cost": food_cost,
            "inventory": inventory,
            "menu": menu,
            "ops": ops,
            "revenue_by_category": revenue_by_category,
            "dish_performance": dish_performance,
            "waste_by_ingredient": waste_by_ingredient,
            "full_menu_performance": full_menu,
            "benchmarks": benchmarks,
            "benchmark_comparisons": benchmark_comparisons,
            "anomalies": anomalies,
            "previous_week": previous_week,
        }

    except Exception as e:
        print(f"[ReportBuilder] build_report_package failed for {restaurant_name}: {e}")
        return {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_benchmarks(pool: asyncpg.Pool) -> dict:
    """Fetch metric_benchmarks table as {metric_name: benchmark_value}."""
    try:
        rows = await pool.fetch("SELECT metric_name, benchmark_value FROM metric_benchmarks")
        return {r["metric_name"]: float(r["benchmark_value"]) for r in rows}
    except Exception as e:
        print(f"[ReportBuilder] _get_benchmarks failed: {e}")
        # Return hard-coded defaults as fallback
        return {
            "food_cost_pct": 30.0,
            "waste_rate_pct": 5.0,
            "avg_spend_per_cover": 28.0,
            "table_turn_rate": 2.5,
            "void_rate_pct": 2.0,
            "attachment_rate": 0.6,
            "recommendation_action_rate": 60.0,
        }


async def _get_previous_week_snapshot(
    pool: asyncpg.Pool, restaurant_id: str, current_week_start: date
) -> dict:
    """Return the prior week's snapshot dict, or {} if not found."""
    from datetime import timedelta
    prev_start = current_week_start - timedelta(days=7)
    try:
        row = await pool.fetchrow(
            """
            SELECT *
            FROM weekly_report_snapshots
            WHERE restaurant_id = $1
              AND week_start = $2
            """,
            restaurant_id,
            prev_start,
        )
        return dict(row) if row else {}
    except Exception as e:
        print(f"[ReportBuilder] _get_previous_week_snapshot failed: {e}")
        return {}


def _compute_benchmark_comparisons(
    revenue: dict, food_cost: dict, inventory: dict, ops: dict, benchmarks: dict
) -> dict:
    """For 4 key metrics, compare actual vs benchmark."""
    comparisons = {}

    def _compare(value: float, benchmark_key: str, lower_is_better: bool = False) -> dict:
        benchmark = benchmarks.get(benchmark_key, 0)
        if benchmark == 0:
            return {"value": value, "benchmark": benchmark, "vs_benchmark": 0.0, "better_than_benchmark": False}
        diff = value - benchmark
        better = diff < 0 if lower_is_better else diff > 0
        return {
            "value": value,
            "benchmark": benchmark,
            "vs_benchmark": round(diff, 2),
            "better_than_benchmark": better,
        }

    comparisons["food_cost_pct"] = _compare(
        food_cost.get("food_cost_pct", 0), "food_cost_pct", lower_is_better=True
    )
    comparisons["waste_rate_pct"] = _compare(
        inventory.get("waste_rate_pct", 0), "waste_rate_pct", lower_is_better=True
    )
    comparisons["avg_spend_per_cover"] = _compare(
        revenue.get("avg_spend_per_cover", 0), "avg_spend_per_cover"
    )
    comparisons["table_turn_rate"] = _compare(
        ops.get("table_turn_rate", 0), "table_turn_rate"
    )

    return comparisons


async def _upsert_weekly_snapshot(
    pool: asyncpg.Pool,
    restaurant_id: str,
    week_start: date,
    week_end: date,
    metrics: dict,
) -> None:
    """Upsert core metrics to weekly_report_snapshots."""
    try:
        await pool.execute(
            """
            INSERT INTO weekly_report_snapshots (
                restaurant_id, week_start, week_end,
                gross_revenue, total_covers, avg_spend_per_cover,
                revenue_wow_pct, revenue_mom_pct,
                void_count, void_rate_pct, peak_hour, peak_hour_revenue,
                food_cost_pct, food_cost_trend,
                top_margin_killer_name, top_margin_killer_pct,
                top_star_dish_name, top_star_dish_pct,
                estimated_margin_loss, pricing_agent_recovery,
                waste_qty, waste_event_count, waste_rate_pct,
                stock_out_count, avg_days_stock_cover, po_cycle_time_days,
                top_dish_name, top_dish_count,
                star_to_dog_ratio, attachment_rate,
                table_turn_rate, recommendation_action_rate, agent_run_count,
                created_at
            ) VALUES (
                $1, $2, $3,
                $4, $5, $6,
                $7, $8,
                $9, $10, $11, $12,
                $13, $14,
                $15, $16,
                $17, $18,
                $19, $20,
                $21, $22, $23,
                $24, $25, $26,
                $27, $28,
                $29, $30,
                $31, $32, $33,
                NOW()
            )
            ON CONFLICT (restaurant_id, week_start) DO UPDATE SET
                week_end                  = EXCLUDED.week_end,
                gross_revenue             = EXCLUDED.gross_revenue,
                total_covers              = EXCLUDED.total_covers,
                avg_spend_per_cover       = EXCLUDED.avg_spend_per_cover,
                revenue_wow_pct           = EXCLUDED.revenue_wow_pct,
                revenue_mom_pct           = EXCLUDED.revenue_mom_pct,
                void_count                = EXCLUDED.void_count,
                void_rate_pct             = EXCLUDED.void_rate_pct,
                peak_hour                 = EXCLUDED.peak_hour,
                peak_hour_revenue         = EXCLUDED.peak_hour_revenue,
                food_cost_pct             = EXCLUDED.food_cost_pct,
                food_cost_trend           = EXCLUDED.food_cost_trend,
                top_margin_killer_name    = EXCLUDED.top_margin_killer_name,
                top_margin_killer_pct     = EXCLUDED.top_margin_killer_pct,
                top_star_dish_name        = EXCLUDED.top_star_dish_name,
                top_star_dish_pct         = EXCLUDED.top_star_dish_pct,
                estimated_margin_loss     = EXCLUDED.estimated_margin_loss,
                pricing_agent_recovery    = EXCLUDED.pricing_agent_recovery,
                waste_qty                 = EXCLUDED.waste_qty,
                waste_event_count         = EXCLUDED.waste_event_count,
                waste_rate_pct            = EXCLUDED.waste_rate_pct,
                stock_out_count           = EXCLUDED.stock_out_count,
                avg_days_stock_cover      = EXCLUDED.avg_days_stock_cover,
                po_cycle_time_days        = EXCLUDED.po_cycle_time_days,
                top_dish_name             = EXCLUDED.top_dish_name,
                top_dish_count            = EXCLUDED.top_dish_count,
                star_to_dog_ratio         = EXCLUDED.star_to_dog_ratio,
                attachment_rate           = EXCLUDED.attachment_rate,
                table_turn_rate           = EXCLUDED.table_turn_rate,
                recommendation_action_rate = EXCLUDED.recommendation_action_rate,
                agent_run_count           = EXCLUDED.agent_run_count
            """,
            restaurant_id, week_start, week_end,
            metrics.get("gross_revenue", 0),
            metrics.get("total_covers", 0),
            metrics.get("avg_spend_per_cover", 0),
            metrics.get("revenue_wow_pct", 0),
            metrics.get("revenue_mom_pct", 0),
            metrics.get("void_count", 0),
            metrics.get("void_rate_pct", 0),
            metrics.get("peak_hour"),
            metrics.get("peak_hour_revenue", 0),
            metrics.get("food_cost_pct", 0),
            metrics.get("food_cost_trend"),
            metrics.get("top_margin_killer_name"),
            metrics.get("top_margin_killer_pct"),
            metrics.get("top_star_dish_name"),
            metrics.get("top_star_dish_pct"),
            metrics.get("estimated_margin_loss", 0),
            metrics.get("pricing_agent_recovery", 0),
            metrics.get("waste_qty", 0),
            metrics.get("waste_event_count", 0),
            metrics.get("waste_rate_pct", 0),
            metrics.get("stock_out_count", 0),
            metrics.get("avg_days_stock_cover"),
            metrics.get("po_cycle_time_days"),
            metrics.get("top_dish_name"),
            metrics.get("top_dish_count", 0),
            metrics.get("star_to_dog_ratio", 0),
            metrics.get("attachment_rate", 0),
            metrics.get("table_turn_rate", 0),
            metrics.get("recommendation_action_rate", 0),
            metrics.get("agent_run_count", 0),
        )
    except Exception as e:
        print(f"[ReportBuilder] _upsert_weekly_snapshot failed: {e}")
