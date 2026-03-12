"""
agents/pricing.py — Pricing Strategy Agent

Responsibilities:
  1. save_food_cost_snapshots(pool, restaurant_id, restaurant_name)
     - Fetches all available menu items with their recipe costs
     - Calculates food_cost and food_cost_pct for each item
     - Writes a row to food_cost_snapshots for every item
     - Runs nightly at 02:00

  2. generate_pricing_recommendations(pool, restaurant_id, restaurant_name, target_pct)
     - Reads the latest food_cost_snapshots for items above the target food cost %
     - Sends those items to Claude (Haiku) to suggest price increases
     - Saves each recommendation to pricing_recommendations with status 'pending'
     - Skips items that already have a pending recommendation created today
     - Runs nightly at 02:30 (after snapshots are saved)
"""

import asyncio
import json
import os
from pathlib import Path

import anthropic

from tools.database import (
    get_menu_items_with_costs,
    get_over_target_menu_items,
    get_existing_pricing_recommendation_today,
    log_agent_action,
    save_food_cost_snapshot,
    save_pricing_recommendation,
)
from tools.pricing_calculator import (
    calculate_avg_cm,
    calculate_cm,
    classify_menu_item,
    requires_multi_cycle_flag,
)

AGENT_NAME = "pricing_agent"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
MAX_PRICE_INCREASE_PCT = 8.0  # never suggest more than 8% in one step

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "pricing_system.txt"


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Part 1: Food Cost Snapshot Worker (runs at 02:00)
# ---------------------------------------------------------------------------


async def save_food_cost_snapshots(
    pool,
    restaurant_id: str,
    restaurant_name: str,
) -> list[dict]:
    """Calculate and save nightly food cost snapshots for every available menu item.

    Returns a list of snapshot dicts: { menu_item_id, menu_item_name, food_cost,
    food_cost_pct, price_at_snapshot }.
    """
    items = await get_menu_items_with_costs(pool, restaurant_id)

    if not items:
        print(f"[Pricing] No menu items found for {restaurant_name} — skipping snapshot.")
        await log_agent_action(
            pool=pool,
            restaurant_id=restaurant_id,
            agent_name=AGENT_NAME,
            action_type="food_cost_snapshot",
            summary=f"No menu items found for {restaurant_name}.",
            data={"item_count": 0},
            status="completed",
        )
        return []

    snapshots = []
    errors = 0

    for item in items:
        menu_item_id = int(item["menu_item_id"])
        price = float(item["price"] or 0)
        food_cost = float(item["food_cost"] or 0)

        if price <= 0:
            # Cannot calculate a percentage — skip gracefully
            print(
                f"[Pricing] Skipping {item['menu_item_name']} — price is zero or null."
            )
            continue

        food_cost_pct = round((food_cost / price) * 100, 2)

        try:
            await save_food_cost_snapshot(
                pool=pool,
                restaurant_id=restaurant_id,
                menu_item_id=menu_item_id,
                food_cost=food_cost,
                food_cost_pct=food_cost_pct,
                price_at_snapshot=price,
            )
        except Exception as e:
            print(
                f"[Pricing] Failed to save snapshot for "
                f"{item['menu_item_name']}: {e}"
            )
            errors += 1
            continue

        snapshots.append(
            {
                "menu_item_id": menu_item_id,
                "menu_item_name": item["menu_item_name"],
                "food_cost": food_cost,
                "food_cost_pct": food_cost_pct,
                "price_at_snapshot": price,
            }
        )

    await log_agent_action(
        pool=pool,
        restaurant_id=restaurant_id,
        agent_name=AGENT_NAME,
        action_type="food_cost_snapshot",
        summary=(
            f"Saved food cost snapshots for {len(snapshots)} item(s) "
            f"at {restaurant_name}."
            + (f" {errors} error(s) skipped." if errors else "")
        ),
        data={"snapshots_saved": len(snapshots), "errors": errors},
        status="completed",
    )

    print(
        f"[Pricing] Saved {len(snapshots)} food cost snapshots for {restaurant_name}."
    )
    return snapshots


# ---------------------------------------------------------------------------
# Part 2: Pricing Recommendation Generator (runs at 02:30)
# ---------------------------------------------------------------------------


async def generate_pricing_recommendations(
    pool,
    restaurant_id: str,
    restaurant_name: str,
    target_food_cost_pct: float,
) -> list[dict]:
    """Generate price recommendations for items whose food cost % exceeds the target.

    Returns a list of saved recommendation dicts.
    """
    over_target = await get_over_target_menu_items(
        pool, restaurant_id, target_food_cost_pct
    )

    if not over_target:
        print(
            f"[Pricing] All items within target for {restaurant_name} — "
            f"no recommendations needed."
        )
        await log_agent_action(
            pool=pool,
            restaurant_id=restaurant_id,
            agent_name=AGENT_NAME,
            action_type="price_recommendation",
            summary=f"All menu items within target food cost % for {restaurant_name}.",
            data={"items_over_target": 0},
            status="completed",
        )
        return []

    # Duplicate guard: filter out items already recommended today
    pending_items = []
    for item in over_target:
        existing = await get_existing_pricing_recommendation_today(
            pool, restaurant_id, int(item["menu_item_id"])
        )
        if existing:
            print(
                f"[Pricing] Skipping {item['menu_item_name']} — "
                f"recommendation {existing} already created today."
            )
        else:
            pending_items.append(item)

    if not pending_items:
        print(
            f"[Pricing] All over-target items already have recommendations today "
            f"for {restaurant_name}."
        )
        return []

    # Compute avg CM across all menu items (not just over-target) for classification
    all_items = await get_menu_items_with_costs(pool, restaurant_id)
    avg_cm = calculate_avg_cm(
        [{"price": float(i["price"] or 0), "food_cost": float(i["food_cost"] or 0)}
         for i in all_items]
    )

    # Call Claude for pricing suggestions
    classified_items = []
    for item in pending_items:
        current_price = float(item["current_price"])
        food_cost = float(item["food_cost"])
        food_cost_pct = float(item["food_cost_pct"])
        cm = calculate_cm(current_price, food_cost)
        classification = classify_menu_item(food_cost_pct, target_food_cost_pct, cm, avg_cm)
        multi_cycle = requires_multi_cycle_flag(
            current_price, food_cost, target_food_cost_pct, MAX_PRICE_INCREASE_PCT
        )
        classified_items.append({
            "menu_item_id": int(item["menu_item_id"]),
            "name": item["menu_item_name"],
            "current_price": current_price,
            "food_cost": food_cost,
            "food_cost_pct": food_cost_pct,
            "cm": cm,
            "avg_cm": avg_cm,
            "classification": classification,
            "multi_cycle_flag": multi_cycle,
        })

    claude_payload = {
        "restaurant_name": restaurant_name,
        "target_food_cost_pct": target_food_cost_pct,
        "max_price_increase_pct": MAX_PRICE_INCREASE_PCT,
        "items": classified_items,
    }

    try:
        claude_recs = await _call_claude(claude_payload)
    except Exception as e:
        await log_agent_action(
            pool=pool,
            restaurant_id=restaurant_id,
            agent_name=AGENT_NAME,
            action_type="claude_error",
            summary=f"Claude API call failed for pricing at {restaurant_name}: {e}",
            data={"error": str(e)},
            status="failed",
        )
        print(f"[Pricing] Claude call failed for {restaurant_id}: {e}")
        return []

    # Save each recommendation
    saved = []

    for rec in claude_recs:
        raw_menu_item_id = rec.get("menu_item_id")
        current_price = float(rec.get("current_price", 0))
        recommended_price = float(rec.get("recommended_price", 0))
        reasoning = rec.get("reasoning", "")
        projected_pct = float(rec.get("projected_food_cost_pct", 0))

        if not raw_menu_item_id or recommended_price <= 0:
            print(f"[Pricing] Skipping recommendation with missing data: {rec}")
            continue

        try:
            menu_item_id = int(raw_menu_item_id)
        except (ValueError, TypeError):
            print(f"[Pricing] Invalid menu_item_id in Claude response: {raw_menu_item_id}")
            continue

        # Look up the current food cost % for this item from our pending_items list
        current_food_cost_pct = float(
            next(
                (i["food_cost_pct"] for i in pending_items
                 if int(i["menu_item_id"]) == menu_item_id),
                0.0,
            )
        )
        item_food_cost = float(
            next(
                (i["food_cost"] for i in pending_items
                 if int(i["menu_item_id"]) == menu_item_id),
                0.0,
            )
        )

        # Enforce the 8% max increase guardrail
        if current_price > 0:
            increase_pct = ((recommended_price - current_price) / current_price) * 100
            if increase_pct > MAX_PRICE_INCREASE_PCT:
                recommended_price = round(
                    current_price * (1 + MAX_PRICE_INCREASE_PCT / 100), 2
                )
                projected_pct = round(
                    (item_food_cost / recommended_price) * 100, 2
                ) if recommended_price > 0 else projected_pct
                reasoning += (
                    f" (Capped at {MAX_PRICE_INCREASE_PCT}% max increase guardrail.)"
                )

        try:
            rec_id = await save_pricing_recommendation(
                pool=pool,
                restaurant_id=restaurant_id,
                menu_item_id=menu_item_id,
                current_price=current_price,
                recommended_price=recommended_price,
                reasoning=reasoning,
                current_food_cost_pct=current_food_cost_pct,
                projected_food_cost_pct=projected_pct,
            )
        except Exception as e:
            print(f"[Pricing] Failed to save recommendation for {menu_item_id}: {e}")
            continue

        item_name = next(
            (i["menu_item_name"] for i in pending_items
             if int(i["menu_item_id"]) == menu_item_id),
            str(menu_item_id),
        )

        saved_rec = {
            "rec_id": rec_id,
            "menu_item_id": menu_item_id,
            "menu_item_name": item_name,
            "current_price": current_price,
            "recommended_price": recommended_price,
            "reasoning": reasoning,
            "projected_food_cost_pct": projected_pct,
        }
        saved.append(saved_rec)

        await log_agent_action(
            pool=pool,
            restaurant_id=restaurant_id,
            agent_name=AGENT_NAME,
            action_type="price_recommendation",
            summary=(
                f"Price recommendation for {item_name}: "
                f"AED {current_price:.2f} -> AED {recommended_price:.2f} "
                f"(food cost {projected_pct:.1f}%)."
            ),
            data=saved_rec,
            status="pending_approval",
            requires_approval=True,
        )

        print(
            f"[Pricing] Recommendation: {item_name} "
            f"AED {current_price:.2f} -> AED {recommended_price:.2f} "
            f"(food cost {projected_pct:.1f}%)"
        )

    print(
        f"[Pricing] Saved {len(saved)} pricing recommendations for {restaurant_name}."
    )
    return saved


# ---------------------------------------------------------------------------
# Internal: Claude API call (sync SDK wrapped in asyncio.to_thread)
# ---------------------------------------------------------------------------


def _call_claude_sync(payload: dict) -> list[dict]:
    """Synchronous call to Claude. Returns the parsed list of recommendation objects.

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
                    f"Here is the pricing data for {payload['restaurant_name']}:\n"
                    f"{json.dumps(payload, indent=2)}"
                ),
            }
        ],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown code fences if Claude added them despite prompt instructions
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:])  # drop the opening ```json line
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Claude returned invalid JSON: {exc}\n\nRaw response:\n{raw_text[:500]}"
        ) from exc

    recommendations = parsed.get("recommendations")
    if not isinstance(recommendations, list):
        raise ValueError(
            f"Claude response missing 'recommendations' list. "
            f"Got keys: {list(parsed.keys())}"
        )

    return recommendations


async def _call_claude(payload: dict) -> list[dict]:
    """Async wrapper around _call_claude_sync."""
    return await asyncio.to_thread(_call_claude_sync, payload)
