"""
tools/pricing_calculator.py — Pure pricing math, no DB dependencies.

All functions in this module are stateless and fully testable without a database.
Full decision tree reference: docs/PRICING_DECISION_TREE.md

Classifications:
  underpriced_star  HIGH cost%, HIGH CM  → Raise price; food cost % resolves itself
  problem           HIGH cost%, LOW CM   → Recipe re-engineering + conservative increase
  true_star         OK cost%,  HIGH CM   → No action needed — protect it
  plowhorse         OK cost%,  LOW CM    → Price increase opportunity despite OK food cost %
"""


def calculate_cm(selling_price: float, ingredient_cost: float) -> float:
    """Contribution margin = selling price minus ingredient cost."""
    return round(selling_price - ingredient_cost, 2)


def calculate_avg_cm(items: list[dict]) -> float:
    """Calculate average contribution margin across a list of menu items.

    Each item must have 'price' and 'food_cost' keys (both numeric or string-numeric).
    Returns 0.0 for an empty list.
    """
    if not items:
        return 0.0
    cms = [
        float(item.get("price") or 0) - float(item.get("food_cost") or 0)
        for item in items
    ]
    return round(sum(cms) / len(cms), 2)


def classify_menu_item(
    food_cost_pct: float,
    target_food_cost_pct: float,
    cm: float,
    avg_cm: float,
) -> str:
    """Classify a menu item into one of four pricing categories.

    Returns one of:
      "underpriced_star"  — food cost over target but CM above average
                            (like Salmon: expensive to make, but best dollar contributor)
      "problem"           — food cost over target AND CM below average
                            (double problem: bad ratio + low absolute contribution)
      "true_star"         — food cost within target AND CM above average
                            (ideal item — protect it, small increases only)
      "plowhorse"         — food cost within target but CM below average
                            (food cost ratio is fine, but underpriced for volume)
    """
    cost_over_target = food_cost_pct > target_food_cost_pct
    cm_above_avg = cm > avg_cm

    if cost_over_target and cm_above_avg:
        return "underpriced_star"
    elif cost_over_target and not cm_above_avg:
        return "problem"
    elif not cost_over_target and cm_above_avg:
        return "true_star"
    else:
        return "plowhorse"


def requires_multi_cycle_flag(
    current_price: float,
    ingredient_cost: float,
    target_food_cost_pct: float,
    max_increase_pct: float,
) -> bool:
    """Return True if a single max-allowed increase cannot reach the food cost target.

    Used to flag items in the recommendation reasoning:
    "Full correction needs X%. Applying 8% this cycle — further increases needed."
    """
    if current_price <= 0 or target_food_cost_pct <= 0:
        return False
    max_allowed_price = current_price * (1 + max_increase_pct / 100)
    target_price_needed = ingredient_cost / (target_food_cost_pct / 100)
    return target_price_needed > max_allowed_price
