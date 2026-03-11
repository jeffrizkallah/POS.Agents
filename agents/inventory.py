"""
agents/inventory.py — Inventory Scanner Agent

Responsibilities:
  1. run_inventory_check(pool, restaurant_id)
     - Fetch ingredients below their reorder_point
     - Calculate daily depletion rate from the last 7 days of sales
     - Save the updated rate to ingredient_depletion_rates
     - Return a list of low-stock items with days_until_stockout
     - Log "no action" to agent_logs if everything is fine

  2. detect_waste_anomalies(pool, restaurant_id)
     - Compare this week's waste per ingredient vs the prior 4-week average
     - Flag any ingredient that is 3× above its average
     - Log each anomaly to agent_logs (status='pending_approval', requires_approval=True)
     - Return the list of flagged anomalies (so the caller can send an alert email)
"""

import math
from tools.database import (
    get_low_stock_ingredients,
    calculate_depletion_from_sales,
    update_depletion_rate,
    log_agent_action,
    get_waste_by_ingredient,
)

AGENT_NAME = "inventory_agent"
DEPLETION_WINDOW_DAYS = 7
WASTE_ANOMALY_MULTIPLIER = 3.0  # flag if current week > 3× prior 4-week average


async def run_inventory_check(pool, restaurant_id: str) -> list[dict]:
    """Scan a single restaurant for low-stock ingredients.

    Steps:
      1. Fetch all ingredients at or below their reorder_point.
      2. For each, calculate the 7-day average daily usage from inventory_transactions.
      3. Upsert that rate into ingredient_depletion_rates.
      4. Compute days_until_stockout = stock_qty / daily_usage (inf if usage == 0).
      5. Log to agent_logs and return the enriched list.

    Returns:
        List of dicts with keys:
          ingredient  — full ingredient dict from get_low_stock_ingredients
          daily_usage — float, units/day (0.0 if no sales data)
          days_until_stockout — float (math.inf when daily_usage == 0)
    """
    print(f"[Inventory] Scanning restaurant {restaurant_id}")

    low_stock = await get_low_stock_ingredients(pool, restaurant_id)

    if not low_stock:
        await log_agent_action(
            pool=pool,
            restaurant_id=restaurant_id,
            agent_name=AGENT_NAME,
            action_type="inventory_scan",
            summary="Inventory scan complete — no low-stock items found.",
            data={"low_stock_count": 0},
            status="completed",
        )
        print(f"[Inventory] No low-stock items for restaurant {restaurant_id}")
        return []

    enriched = []
    for ingredient in low_stock:
        ingredient_id = str(ingredient["id"])
        stock_qty = float(ingredient["stock_qty"])

        try:
            daily_usage = await calculate_depletion_from_sales(
                pool, ingredient_id, DEPLETION_WINDOW_DAYS
            )
        except Exception as e:
            print(
                f"[Inventory] Failed to calculate depletion for {ingredient['name']}: {e}"
            )
            daily_usage = 0.0

        # Upsert the freshly calculated rate so ordering agent has it
        try:
            await update_depletion_rate(
                pool, ingredient_id, daily_usage, DEPLETION_WINDOW_DAYS
            )
        except Exception as e:
            print(
                f"[Inventory] Failed to save depletion rate for {ingredient['name']}: {e}"
            )

        days_until_stockout = (
            stock_qty / daily_usage if daily_usage > 0 else math.inf
        )

        enriched.append(
            {
                "ingredient": ingredient,
                "daily_usage": daily_usage,
                "days_until_stockout": days_until_stockout,
            }
        )

        print(
            f"[Inventory]   {ingredient['name']}: stock={stock_qty} {ingredient['unit']}, "
            f"daily_usage={daily_usage:.4f}, days_remaining={days_until_stockout:.1f}"
        )

    # Build a compact summary list for the log payload
    items_summary = [
        {
            "ingredient_id": str(item["ingredient"]["id"]),
            "name": item["ingredient"]["name"],
            "stock_qty": float(item["ingredient"]["stock_qty"]),
            "reorder_point": float(item["ingredient"]["reorder_point"]),
            "daily_usage": item["daily_usage"],
            "days_until_stockout": (
                item["days_until_stockout"]
                if item["days_until_stockout"] != math.inf
                else None
            ),
        }
        for item in enriched
    ]

    await log_agent_action(
        pool=pool,
        restaurant_id=restaurant_id,
        agent_name=AGENT_NAME,
        action_type="inventory_scan",
        summary=(
            f"Inventory scan complete — {len(enriched)} low-stock item(s) found. "
            f"Handing off to ordering agent."
        ),
        data={"low_stock_count": len(enriched), "items": items_summary},
        status="completed",
    )

    return enriched


async def detect_waste_anomalies(pool, restaurant_id: str) -> list[dict]:
    """Compare this week's waste per ingredient against the prior 4-week average.

    Flags any ingredient where current_week_qty > WASTE_ANOMALY_MULTIPLIER × avg_4week_qty
    and avg_4week_qty > 0 (i.e. there is a meaningful baseline to compare against).

    For each anomaly:
      - Logs a row to agent_logs with status='pending_approval', requires_approval=True
      - Returns the list of anomaly dicts so the caller can send an alert email.

    Returns:
        List of dicts with keys:
          ingredient_id, ingredient_name,
          current_week_qty, avg_4week_qty, ratio
    """
    print(f"[Inventory] Checking waste anomalies for restaurant {restaurant_id}")

    waste_rows = await get_waste_by_ingredient(pool, restaurant_id)

    anomalies = []
    for row in waste_rows:
        current = float(row["current_week_qty"])
        average = float(row["avg_4week_qty"])

        # Only flag if there is a meaningful 4-week baseline
        if average > 0 and current >= WASTE_ANOMALY_MULTIPLIER * average:
            ratio = round(current / average, 2)
            anomaly = {
                "ingredient_id": str(row["ingredient_id"]),
                "ingredient_name": row["ingredient_name"],
                "current_week_qty": current,
                "avg_4week_qty": average,
                "ratio": ratio,
            }
            anomalies.append(anomaly)

            await log_agent_action(
                pool=pool,
                restaurant_id=restaurant_id,
                agent_name=AGENT_NAME,
                action_type="waste_anomaly",
                summary=(
                    f"Waste anomaly detected: {row['ingredient_name']} is {ratio}× "
                    f"above the 4-week average this week ({current:.2f} vs avg {average:.2f})."
                ),
                data=anomaly,
                status="pending_approval",
                requires_approval=True,
            )

            print(
                f"[Inventory]   ANOMALY: {row['ingredient_name']} "
                f"current={current:.2f} avg={average:.2f} ratio={ratio}×"
            )

    if not anomalies:
        print(f"[Inventory] No waste anomalies for restaurant {restaurant_id}")
    else:
        print(
            f"[Inventory] {len(anomalies)} waste anomaly(s) flagged for restaurant {restaurant_id}"
        )

    return anomalies
