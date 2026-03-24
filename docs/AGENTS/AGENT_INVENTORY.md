# Inventory Scanner Agent

**File:** `agents/inventory.py`
**Runs:** Every 15 minutes (alongside the ordering agent)

---

## What it does in plain English

The Inventory Scanner is the first agent that runs in every cycle. Its job is simple: look at every ingredient in the restaurant's kitchen and figure out which ones are running low. Then, for each low ingredient, work out how fast it's being used so the ordering agent can decide how much to order.

It also separately checks for unusual spikes in food waste — if a restaurant suddenly wastes 3× more of an ingredient than normal, that's worth flagging.

---

## How it works — Step by step

### Part 1: Stock Check (`run_inventory_check`)

1. **Fetch low-stock ingredients**
   The agent queries the database for any ingredient whose current stock (`stock_qty`) has fallen at or below its `reorder_point`. This is the threshold the restaurant owner has set to say "we need more of this."

2. **Calculate daily usage for each item**
   For every low-stock ingredient, the agent looks back at the last 7 days of sales data from `inventory_transactions`. It calculates how many units of that ingredient were used per day on average. This is called the **depletion rate**.

3. **Save the updated depletion rate**
   The freshly calculated daily usage is saved to the `ingredient_depletion_rates` table. The ordering agent will use this number when deciding how much to order.

4. **Calculate days until stockout**
   Using the formula `current stock ÷ daily usage`, the agent estimates how many days are left before the ingredient runs out completely. If an ingredient has no sales data (daily usage = 0), it's treated as "unknown" rather than crashing.

5. **Return the results**
   The agent returns a list of enriched items — each one containing the ingredient details, its daily usage rate, and how many days until it runs out. This list is handed off directly to the Ordering Agent.

6. **Log the result**
   Whatever happened (low-stock items found, or everything fine) is written to `agent_logs` so it appears in the POS dashboard's Agents page.

**If nothing is low:** It logs a "no action needed" message and stops. No ordering agent is triggered.

---

### Part 2: Waste Anomaly Detection (`detect_waste_anomalies`)

This runs separately after the stock check. Its goal is to catch unusual waste spikes before they become a bigger problem.

1. **Fetch this week's waste vs. the 4-week average**
   For every ingredient, the agent compares how much was wasted *this week* against the average waste over the prior 4 weeks.

2. **Flag anything 3× above average**
   If an ingredient's waste this week is 3 or more times higher than its 4-week average, it's flagged as an anomaly. There has to be a meaningful 4-week baseline — if the ingredient was never wasted before, there's nothing to compare against.

3. **Log each anomaly for human review**
   Every anomaly gets logged to `agent_logs` with status `pending_approval` and `requires_approval = True`. This means it shows up in the dashboard as something that needs a human to look at, not an automatic action.

4. **Return the anomaly list**
   The list of flagged anomalies is returned to the main scheduler, which can then trigger an alert email to the restaurant manager.

---

## Key thresholds

| Signal | Threshold |
|--------|-----------|
| Low stock trigger | `stock_qty <= reorder_point` |
| Depletion window | Last 7 days of sales |
| Waste anomaly trigger | Current week > 3× prior 4-week average |

---

## What it does NOT do

- It does not place or draft any orders — that's the Ordering Agent's job.
- It does not send any emails directly — the scheduler handles that.
- It never crashes the whole system if one restaurant or one ingredient fails — each error is caught individually.
