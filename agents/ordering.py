"""
agents/ordering.py — Ordering Agent

Responsibilities:
  1. draft_purchase_orders(pool, restaurant_id, restaurant_name, low_stock_items)
     - Calculates recommended order quantities for each low-stock ingredient
     - Sends the full payload to Claude (Haiku) to review and annotate
     - Saves approved draft purchase orders to the database (one per supplier)
     - Skips suppliers that already have a draft PO created today (duplicate guard)
     - Logs every order (and every failure) to agent_logs

  2. send_approval_email(pool, restaurant_id, restaurant_name, orders_created)
     - Fetches the manager's email address
     - Sends a low-stock alert email with an "Approve Orders" button

low_stock_items is the list returned by agents/inventory.run_inventory_check().
Each element is: { ingredient: dict, daily_usage: float, days_until_stockout: float }
"""

import asyncio
import json
import math
import os
from pathlib import Path

import anthropic

from tools.database import (
    get_existing_draft_po_today,
    get_manager_email,
    log_agent_action,
    save_purchase_order,
)
from tools.email_sender import send_low_stock_alert
from tools.order_calculator import calculate_order_quantity

AGENT_NAME = "ordering_agent"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "ordering_system.txt"


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def draft_purchase_orders(
    pool,
    restaurant_id: str,
    restaurant_name: str,
    low_stock_items: list[dict],
) -> list[dict]:
    """Draft purchase orders for a restaurant's low-stock ingredients.

    Args:
        pool:             asyncpg connection pool
        restaurant_id:    UUID string
        restaurant_name:  Human-readable name (used in Claude prompt + logs)
        low_stock_items:  Output of run_inventory_check — list of
                          { ingredient, daily_usage, days_until_stockout }

    Returns:
        List of successfully saved order dicts, each containing:
          supplier_id, supplier_name, po_id, items (list), total_cost, notes
    """
    if not low_stock_items:
        return []

    # ------------------------------------------------------------------
    # Step 1: Calculate recommended order quantities for every item.
    # Skip items with no supplier — we can't order without one.
    # ------------------------------------------------------------------
    enriched_items = []
    for entry in low_stock_items:
        ingredient = entry["ingredient"]
        daily_usage = entry["daily_usage"]
        days_until_stockout = entry["days_until_stockout"]

        if not ingredient.get("supplier_id"):
            print(
                f"[Ordering] Skipping {ingredient['name']} — no supplier assigned."
            )
            continue

        lead_time = int(ingredient.get("lead_time_days") or 2)

        calc = calculate_order_quantity(
            current_stock=float(ingredient["stock_qty"]),
            reorder_point=float(ingredient["reorder_point"]),
            par_level=float(ingredient["par_level"]),
            daily_usage=daily_usage,
            lead_time_days=lead_time,
        )

        enriched_items.append(
            {
                "ingredient_id": str(ingredient["id"]),
                "name": ingredient["name"],
                "unit": ingredient["unit"],
                "current_stock": float(ingredient["stock_qty"]),
                "reorder_point": float(ingredient["reorder_point"]),
                "par_level": float(ingredient["par_level"]),
                "daily_usage": daily_usage,
                "days_until_stockout": (
                    None if days_until_stockout == math.inf else days_until_stockout
                ),
                "supplier_id": str(ingredient["supplier_id"]),
                "supplier_name": ingredient.get("supplier_name") or "Unknown Supplier",
                "lead_time_days": lead_time,
                "cost_per_unit": float(ingredient.get("cost_per_unit") or 0),
                "recommended_qty": calc["recommended_qty"],
                "calc_reasoning": calc["reasoning"],
            }
        )

    if not enriched_items:
        print(f"[Ordering] No orderable items for restaurant {restaurant_id}.")
        return []

    # ------------------------------------------------------------------
    # Step 2: Call Claude to review and annotate the orders.
    # ------------------------------------------------------------------
    claude_payload = {
        "restaurant_name": restaurant_name,
        "items": enriched_items,
    }

    try:
        claude_orders = await _call_claude(claude_payload)
    except Exception as e:
        await log_agent_action(
            pool=pool,
            restaurant_id=restaurant_id,
            agent_name=AGENT_NAME,
            action_type="service_error",
            summary=f"Could not generate purchase orders for {restaurant_name}. The AI service returned an unexpected response.",
            data={"error": str(e)},
            status="failed",
        )
        print(f"[Ordering] Claude call failed for {restaurant_id}: {e}")
        return []

    # ------------------------------------------------------------------
    # Step 3: Save each supplier's order to the database.
    # ------------------------------------------------------------------
    created_orders = []

    for order in claude_orders:
        supplier_id = order.get("supplier_id")
        supplier_name = order.get("supplier_name", "Unknown")
        items = order.get("items", [])
        notes = order.get("notes", "")

        if not supplier_id or not items:
            print(f"[Ordering] Skipping order with missing supplier_id or items.")
            continue

        # Duplicate guard: skip if a draft PO for this supplier already exists today
        try:
            existing_po_id = await get_existing_draft_po_today(
                pool, restaurant_id, supplier_id
            )
        except Exception:
            existing_po_id = None  # be conservative — try to save anyway

        if existing_po_id:
            print(
                f"[Ordering] Skipping {supplier_name} — draft PO {existing_po_id} "
                f"already exists for today."
            )
            continue

        # Build DB lines from Claude's output
        lines = [
            {
                "ingredient_id": item["ingredient_id"],
                "quantity_ordered": float(item["quantity"]),
                "cost_per_unit": float(item["cost_per_unit"]),
            }
            for item in items
            if item.get("ingredient_id") and item.get("quantity", 0) > 0
        ]

        if not lines:
            continue

        try:
            po_id = await save_purchase_order(
                pool, restaurant_id, supplier_id, lines, notes
            )
        except Exception as e:
            await log_agent_action(
                pool=pool,
                restaurant_id=restaurant_id,
                agent_name=AGENT_NAME,
                action_type="draft_purchase_order",
                summary=f"Failed to save PO for {supplier_name}: {e}",
                data={"supplier_id": supplier_id, "error": str(e)},
                status="failed",
            )
            print(f"[Ordering] Failed to save PO for {supplier_name}: {e}")
            continue

        total_cost = order.get("total_cost") or sum(
            l["quantity_ordered"] * l["cost_per_unit"] for l in lines
        )

        saved_order = {
            "po_id": po_id,
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "items": items,
            "total_cost": round(total_cost, 2),
            "notes": notes,
        }
        created_orders.append(saved_order)

        await log_agent_action(
            pool=pool,
            restaurant_id=restaurant_id,
            agent_name=AGENT_NAME,
            action_type="draft_purchase_order",
            summary=(
                f"Drafted PO #{po_id} for {supplier_name} — "
                f"{len(items)} item(s), total ${total_cost:.2f}."
            ),
            data=saved_order,
            status="completed",
            requires_approval=True,
        )

        print(
            f"[Ordering] Saved PO {po_id} for {supplier_name} "
            f"({len(items)} items, ${total_cost:.2f})"
        )

    return created_orders


async def send_approval_email(
    pool,
    restaurant_id: str,
    restaurant_name: str,
    orders_created: list[dict],
) -> None:
    """Email the restaurant manager to review and approve the drafted orders.

    Builds a flat item list from all orders so the manager sees everything at a glance.
    """
    if not orders_created:
        return

    manager_email = await get_manager_email(pool, restaurant_id)
    if not manager_email:
        print(
            f"[Ordering] No manager email found for restaurant {restaurant_id} — "
            f"skipping approval email."
        )
        return

    dashboard_url = os.environ.get("APP_URL", "https://app.restaurantos.com")

    # Flatten all items across all orders for the email summary table
    email_items = []
    for order in orders_created:
        for item in order.get("items", []):
            email_items.append(
                {
                    "name": item.get("name", "Unknown"),
                    "unit": item.get("unit", ""),
                    "stock_qty": None,   # not shown in this summary view
                    "reorder_point": None,
                    "recommended_qty": item.get("quantity"),
                    "days_remaining": None,
                }
            )

    try:
        await send_low_stock_alert(
            to_email=manager_email,
            restaurant_name=restaurant_name,
            items=email_items,
            dashboard_url=dashboard_url,
        )
    except Exception as e:
        print(f"[Ordering] Failed to send approval email to {manager_email}: {e}")


# ---------------------------------------------------------------------------
# Internal: Claude API call (sync SDK wrapped in asyncio.to_thread)
# ---------------------------------------------------------------------------


def _call_claude_sync(payload: dict) -> list[dict]:
    """Synchronous call to Claude. Returns the parsed list of order objects.

    Raises ValueError if Claude returns invalid JSON or an unexpected schema.
    """
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    system_prompt = _load_system_prompt()

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Here is the low-stock inventory data for {payload['restaurant_name']}:\n"
                    f"{json.dumps(payload, indent=2)}"
                ),
            }
        ],
    )

    raw_text = response.content[0].text.strip()
    # Strip markdown code fences if Claude wraps the JSON in ```json ... ```
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[-1]
        raw_text = raw_text.rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Claude returned invalid JSON: {exc}\n\nRaw response:\n{raw_text[:500]}"
        ) from exc

    orders = parsed.get("orders")
    if not isinstance(orders, list):
        raise ValueError(
            f"Claude response missing 'orders' list. Got keys: {list(parsed.keys())}"
        )

    return orders


async def _call_claude(payload: dict) -> list[dict]:
    """Async wrapper around _call_claude_sync."""
    return await asyncio.to_thread(_call_claude_sync, payload)
