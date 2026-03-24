"""Inventory metrics for the weekly analytics report (Phase 6E)."""

import asyncpg
from datetime import date, timedelta


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

        # PO cycle time: purchase_orders only has created_at (no completion timestamp)
        po_cycle_time_days = None

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


async def get_consumption_analysis(
    pool: asyncpg.Pool, restaurant_id: str, week_start: date, week_end: date
) -> dict:
    """Consumption reconciliation: Opening + Purchased = Production + Closing.

    Splits ingredients into two categories:
    - Recipe ingredients: consumed via production_batch_inputs (kitchen batches)
    - Unitary items: sold directly, tracked via inventory_transactions type='sale'

    Variance = Actual Closing - Expected Closing
      Positive → over-purchased (more stock left than production accounts for)
      Negative → production discrepancy (less stock than expected — recipe wrong,
                 over-portioning, or unrecorded consumption)

    Waste is intentionally excluded from the formula so it cannot mask discrepancies.

    Tables used:
      ingredients              → closing stock (stock_qty)
      inventory_transactions   → net period change (to reconstruct opening stock)
                                 purchases (type='purchase')
                                 unitary sales (type='sale')
      production_batches       → batch records for the period (created_at window)
      production_batch_inputs  → raw ingredient quantities consumed per batch
    """
    period_end = week_end + timedelta(days=1)  # exclusive upper bound

    try:
        # --- 1. All ingredients for this restaurant ---
        ingredients = await pool.fetch(
            """
            SELECT id, name, unit, stock_qty
            FROM ingredients
            WHERE restaurant_id = $1
            """,
            restaurant_id,
        )
        if not ingredients:
            return _empty_consumption()

        ing_ids = [r["id"] for r in ingredients]

        # --- 2. Net inventory change in period (all transaction types combined) ---
        # Opening = Closing - net_change  (rolls back all recorded movements)
        net_rows = await pool.fetch(
            """
            SELECT ingredient_id, SUM(quantity_change) AS net_change
            FROM inventory_transactions
            WHERE ingredient_id = ANY($1::uuid[])
              AND created_at >= $2
              AND created_at <  $3
            GROUP BY ingredient_id
            """,
            ing_ids, week_start, period_end,
        )
        net_change_map = {str(r["ingredient_id"]): float(r["net_change"] or 0) for r in net_rows}

        # --- 3. Purchases in period (type='purchase') ---
        purchase_rows = await pool.fetch(
            """
            SELECT ingredient_id, SUM(quantity_change) AS purchased
            FROM inventory_transactions
            WHERE ingredient_id = ANY($1::uuid[])
              AND type = 'purchase'
              AND created_at >= $2
              AND created_at <  $3
            GROUP BY ingredient_id
            """,
            ing_ids, week_start, period_end,
        )
        purchase_map = {str(r["ingredient_id"]): float(r["purchased"] or 0) for r in purchase_rows}

        # --- 4. Production consumed in period (from production_batch_inputs) ---
        # These are recipe ingredients consumed by kitchen production batches.
        production_rows = await pool.fetch(
            """
            SELECT pbi.ingredient_id, SUM(pbi.quantity_used) AS production_used
            FROM production_batch_inputs pbi
            JOIN production_batches pb ON pb.id = pbi.batch_id
            WHERE pb.restaurant_id = $1
              AND pb.created_at >= $2
              AND pb.created_at <  $3
            GROUP BY pbi.ingredient_id
            """,
            restaurant_id, week_start, period_end,
        )
        production_map = {str(r["ingredient_id"]): float(r["production_used"] or 0) for r in production_rows}

        # --- 5. Sale transactions per ingredient (for unitary items) ---
        # Unitary items have no production batch — they deplete stock directly on sale.
        sale_rows = await pool.fetch(
            """
            SELECT ingredient_id, SUM(ABS(quantity_change)) AS sold
            FROM inventory_transactions
            WHERE ingredient_id = ANY($1::uuid[])
              AND type = 'sale'
              AND created_at >= $2
              AND created_at <  $3
            GROUP BY ingredient_id
            """,
            ing_ids, week_start, period_end,
        )
        sale_map = {str(r["ingredient_id"]): float(r["sold"] or 0) for r in sale_rows}

        # --- 6. Per-ingredient reconciliation ---
        recipe_ingredients = []
        unitary_items = []

        for ing in ingredients:
            iid = str(ing["id"])
            closing = float(ing["stock_qty"] or 0)
            net_change = net_change_map.get(iid, 0.0)
            purchased = purchase_map.get(iid, 0.0)
            production_used = production_map.get(iid, 0.0)
            sold = sale_map.get(iid, 0.0)

            # Opening stock: roll back all recorded movements in the period
            opening = closing - net_change

            if production_used > 0:
                # Recipe ingredient — consumed via production batches
                expected_closing = opening + purchased - production_used
                variance = round(closing - expected_closing, 4)
                recipe_ingredients.append({
                    "ingredient_name": ing["name"],
                    "unit": ing["unit"],
                    "opening_stock": round(opening, 3),
                    "purchased": round(purchased, 3),
                    "production_consumed": round(production_used, 3),
                    "closing_stock": round(closing, 3),
                    "expected_closing": round(expected_closing, 3),
                    "variance": variance,
                    "verdict": _consumption_verdict(variance),
                })
            elif sold > 0 or purchased > 0:
                # Unitary item — no production batch, depleted directly via sales
                expected_closing = opening + purchased - sold
                variance = round(closing - expected_closing, 4)
                unitary_items.append({
                    "ingredient_name": ing["name"],
                    "unit": ing["unit"],
                    "opening_stock": round(opening, 3),
                    "purchased": round(purchased, 3),
                    "sold": round(sold, 3),
                    "closing_stock": round(closing, 3),
                    "expected_closing": round(expected_closing, 3),
                    "variance": variance,
                    "verdict": _consumption_verdict(variance),
                })
            # Ingredients with zero activity this period are skipped

        # Sort by absolute variance descending — biggest discrepancies first
        recipe_ingredients.sort(key=lambda x: abs(x["variance"]), reverse=True)
        unitary_items.sort(key=lambda x: abs(x["variance"]), reverse=True)

        all_items = recipe_ingredients + unitary_items
        over_purchased = sum(1 for x in all_items if x["variance"] > 0.01)
        discrepancies = sum(1 for x in all_items if x["variance"] < -0.01)

        if discrepancies > 0:
            overall_verdict = "discrepancy_detected"
        elif over_purchased > 0:
            overall_verdict = "over_purchased"
        else:
            overall_verdict = "balanced"

        return {
            "recipe_ingredients": recipe_ingredients,
            "unitary_items": unitary_items,
            "summary": {
                "recipe_ingredient_count": len(recipe_ingredients),
                "unitary_item_count": len(unitary_items),
                "ingredients_over_purchased": over_purchased,
                "ingredients_with_discrepancy": discrepancies,
                "overall_verdict": overall_verdict,
            },
        }

    except Exception as e:
        print(f"[Metrics Error] get_consumption_analysis(restaurant_id={restaurant_id}): {e}")
        return _empty_consumption()


def _consumption_verdict(variance: float) -> str:
    if variance > 0.01:
        return "over_purchased"
    elif variance < -0.01:
        return "production_discrepancy"
    return "balanced"


def _empty_consumption() -> dict:
    return {
        "recipe_ingredients": [],
        "unitary_items": [],
        "summary": {
            "recipe_ingredient_count": 0,
            "unitary_item_count": 0,
            "ingredients_over_purchased": 0,
            "ingredients_with_discrepancy": 0,
            "overall_verdict": "no_data",
        },
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
