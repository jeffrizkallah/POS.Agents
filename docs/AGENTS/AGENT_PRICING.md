# Pricing Strategy Agent

**File:** `agents/pricing.py`
**Runs:** Nightly at 02:00 (snapshots) and 02:30 (recommendations), plus every 15 min (applying approved changes)

---

## What it does in plain English

The Pricing Agent has one goal: help restaurant owners charge the right price for their food. Every night, it calculates the true cost of making each dish and checks whether the current selling price is covering costs adequately. If something is priced too low (i.e. the food costs too much relative to what it sells for), the agent asks Claude to suggest a better price and saves that suggestion for the owner to review.

When the owner approves a suggestion in the dashboard, the agent automatically updates the menu item's price in the database.

---

## How it works — Step by step

### Part 1: Nightly Food Cost Snapshot (02:00)

Every night at 2am the agent takes a "photograph" of the financial state of every menu item. This snapshot is what powers the Food Cost Trend charts in the Reports page.

1. **Fetch all menu items with their recipe costs**
   For every menu item, the agent sums up the cost of all the ingredients in its recipe: `food_cost = SUM(ingredient cost × quantity needed)`.

2. **Calculate the food cost percentage**
   `food_cost_pct = (food_cost ÷ selling_price) × 100`
   This is the industry-standard metric. A 30% food cost means it costs $3 of ingredients to make a dish selling for $10.

3. **Save a snapshot row for every item**
   Each calculation is written to the `food_cost_snapshots` table with today's date. The restaurant owner can see this history as a trend over time.

Items with a zero or missing price are skipped cleanly.

---

### Part 2: Pricing Recommendations (02:30)

Runs 30 minutes after the snapshots, so it's working with fresh data.

1. **Find items over the target food cost %**
   The restaurant has a target food cost percentage set in their settings (e.g. 30%). The agent fetches every menu item where today's snapshot shows a food cost % above that target.

2. **Skip items already recommended today**
   If a recommendation was already generated for an item today, it's skipped. No point creating duplicates every time the agent runs.

3. **Classify each item using a decision matrix**
   Before calling Claude, the agent enriches each item with extra context:
   - **Contribution margin (CM):** How much money does this dish actually make after ingredient costs? `CM = selling_price − food_cost`
   - **Average CM across the menu:** Used to compare whether this dish is above or below average profitability.
   - **Classification:** Each item gets labelled as one of four types:
     - *True Star* — High CM, low food cost % (great dish, no action needed)
     - *Underpriced Star* — High CM, high food cost % (popular and profitable, but priced too low relative to ingredients)
     - *Problem* — Low CM, high food cost % (needs urgent repricing)
     - *Plowhorse* — Low CM, low food cost % (sells fine but doesn't make much money)
   - **Multi-cycle flag:** If the price gap is so large that a single 8% increase won't fix it, the item is flagged for multiple rounds of repricing over time.
   - **Sales volume (30 days):** How many units were sold in the last 30 days. This tells Claude whether the dish is popular or not.

4. **Ask Claude for price recommendations**
   The agent sends all classified over-target items to Claude (Haiku model). Claude knows:
   - The current price and food cost
   - The classification (what kind of problem this is)
   - The target food cost %
   - The maximum allowed price increase (8% per cycle)
   - Whether multiple price cycles will be needed
   - Sales volume data

   Claude returns a list of recommended prices with reasoning for each one.

5. **Enforce the 8% guardrail**
   Even if Claude suggests a larger increase, the agent caps every recommendation at 8% above the current price. This protects the restaurant from sudden large price jumps that might upset customers.

6. **Estimate volume impact**
   Using a standard price elasticity model, the agent estimates how many fewer customers might order the dish after a price increase. This estimate is added to the reasoning so the owner understands the trade-off.

7. **Save and log each recommendation**
   Each recommendation is saved to the `ai_pricing_recommendations` table with status `pending`. It appears in the POS dashboard's Pricing page for the owner to accept or reject. Every recommendation is also logged to `agent_logs`.

---

### Part 3: Applying Approved Recommendations (every 15 minutes)

When a manager clicks "Accept" on a recommendation in the dashboard, the row's status changes to `approved`. The next time this part of the agent runs (every 15 minutes alongside the inventory job), it:

1. Fetches all recommendations with status `approved`.
2. Updates the corresponding menu item's price in the `menu_items` table.
3. Marks the recommendation as `applied`.
4. Logs the price change to `agent_logs` so there's a clear audit trail.

---

## Key rules and limits

| Setting | Value |
|---------|-------|
| AI model used | Claude Haiku 4.5 |
| Max price increase per cycle | 8% |
| Snapshot time | 02:00 nightly |
| Recommendation time | 02:30 nightly |
| Price application | Every 15 minutes |
| Deduplication | One recommendation per item per day |

---

## The four item classifications

| Type | Food Cost % | Contribution Margin | What to do |
|------|-------------|--------------------|----|
| True Star | High | High | Raise price — people love it and it makes money |
| Problem | High | Low | Needs repricing urgently |
| Plowhorse | Low | Low | Lower priority — not losing money but not maximising it |
| Underpriced Star | High | High | Careful raise — it's popular so don't risk chasing people away |

---

## What it does NOT do

- It does not change prices automatically without manager approval.
- It does not raise prices more than 8% in one go.
- It does not create duplicate recommendations if one already exists for today.
