# Pricing Agent — Decision Tree Reference

> **Purpose:** This is the authoritative reference for how the pricing agent classifies menu items and decides what action to recommend.
> **Status:** Implemented in `tools/pricing_calculator.py` and `agents/pricing.py`
> **Last Updated:** 2026-03-12
> Update this document whenever the decision tree logic changes.

---

## The Four Quadrants

Each menu item is classified on two axes:
- **Food Cost %** — is the item's food cost percentage above or below the restaurant's target?
- **Contribution Margin (CM)** — is the item's CM (price − ingredient cost) above or below the menu average?

|  | **CM ≥ Avg CM** | **CM < Avg CM** |
|---|---|---|
| **Cost% > Target** | `underpriced_star` | `problem` |
| **Cost% ≤ Target** | `true_star` | `plowhorse` |

---

## Classifications & Actions

### `underpriced_star` — High cost%, High CM
> *Example: Seared Salmon costs AED 15 to make (44.78% food cost, over the 27% target), but contributes AED 18.5 CM — the highest on the menu.*

**What it means:** The item is expensive to produce relative to its price, but its absolute contribution toward covering fixed costs is above average. It is almost certainly priced below its market value.

**Why food cost % alone is misleading here:** A dish generating AED 18.5 per cover is a net positive for the business even if its cost ratio looks bad. Blindly flagging it as a "problem" misses that raising the price solves both issues simultaneously.

**Action:** Raise the price. As price rises, food cost % self-corrects. This item has low volume risk — customers are already paying a premium and expect it.

**Guardrail:** Apply the standard 8% per-cycle cap. If a single 8% increase is not enough to reach the food cost target, flag the item as **"multi-cycle repricing needed"** — do not block the recommendation, but include the flag in the reasoning.

**Do NOT recommend recipe re-engineering as the primary action.** High CM means the item is a net winner. Cost reduction is a secondary option only if market ceiling makes further price increases impossible.

---

### `problem` — High cost%, Low CM
> *"Expensive to make AND not contributing enough dollars. The double problem."*

**What it means:** The item has both a bad food cost ratio AND a below-average contribution margin. It is losing on two dimensions. A price increase alone will not solve this — the underlying recipe cost is likely the root issue.

**Action:**
1. Apply a conservative price increase (up to 8% cap).
2. Flag the item for **recipe re-engineering** — the reasoning must explicitly say the ingredient cost needs review.
3. If price is already near the market ceiling, the item may need to be removed from the menu.

---

### `true_star` — OK cost%, High CM
> *"The ideal menu item. Good ratio AND strong absolute contribution. Do not disrupt it."*

**What it means:** The item is priced correctly relative to its food cost AND generates above-average contribution margin. It is doing everything right.

**Action:** No pricing action needed. If a small increase is warranted by competitor data (future Phase B), keep it conservative (≤ 4% in one step). Protect volume — this item is likely popular.

---

### `plowhorse` — OK cost%, Low CM
> *"Food cost ratio is fine, but the absolute contribution is too low — this item is underpriced for what it could earn."*

**What it means:** The item is within the food cost target (so it's not flagged by ratio-based logic), but it contributes below-average dollars per cover. It is a candidate for a price increase even though the food cost % looks healthy.

**Action:** Price increase opportunity. A modest increase improves total margin without violating food cost discipline. Note in reasoning that this is a proactive increase, not a correction.

---

## Full Decision Flow

```
STEP 1 — Snapshot (runs at 02:00)
  For every menu item:
    food_cost     = SUM(ingredient.cost × recipe.quantity)
    food_cost_pct = (food_cost / selling_price) × 100
  Save to food_cost_snapshots.

STEP 2 — Classification (runs at 02:30)
  Fetch ALL menu items from today's snapshot data.
  avg_cm = mean(selling_price − food_cost) across all items.

  For each item:
    cm = selling_price − food_cost

    if food_cost_pct > target AND cm > avg_cm  → underpriced_star
    if food_cost_pct > target AND cm ≤ avg_cm  → problem
    if food_cost_pct ≤ target AND cm > avg_cm  → true_star
    if food_cost_pct ≤ target AND cm ≤ avg_cm  → plowhorse

STEP 3 — Action selection
  underpriced_star → Include in recommendation run; aggressive price increase
  problem          → Include in recommendation run; flag recipe re-engineering
  true_star        → Exclude (no action needed)
  plowhorse        → Include in recommendation run; proactive price increase

STEP 4 — Guardrail
  recommended_price = min(target_price, current_price × 1.08)
  if target_price > current_price × 1.08 → add multi_cycle_flag = true to payload

STEP 5 — Claude recommendation
  Claude receives classification + all pricing data per item.
  Claude selects a specific price with reasoning tailored to the classification.
  The reasoning must reflect the item's classification — not a generic formula.
```

---

## Claude Payload Per Item

```json
{
  "menu_item_id": 22,
  "name": "Seared Salmon",
  "current_price": 33.50,
  "food_cost": 15.00,
  "food_cost_pct": 44.78,
  "cm": 18.50,
  "avg_cm": 13.50,
  "classification": "underpriced_star",
  "multi_cycle_flag": true
}
```

---

## Future Layers (not yet implemented)

When additional data becomes available, the decision tree expands:

| Layer | What it adds | Dependency |
|---|---|---|
| Contribution Margin floor | Checks if viable_floor covers fixed costs per cover | `monthly_fixed_costs` field in restaurant settings |
| Competitor calibration | Anchors price to market midpoint, not just food cost % | `competitor_prices` table (manual input) |
| Volume-weighted classification | Confirms star/plowhorse with real demand data | `order_items` sales counts |
| Menu engineering matrix | Full Star/Plowhorse/Puzzle/Dog with sales + CM | Above + `menu_engineering_scores` table |

See [PRICING_AGENT_PLAN.md](PRICING_AGENT_PLAN.md) for the full roadmap.
