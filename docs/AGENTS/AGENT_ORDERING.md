# Ordering Agent

**File:** `agents/ordering.py`
**Runs:** Every 15 minutes, immediately after the Inventory Scanner if low-stock items are found

---

## What it does in plain English

The Ordering Agent takes the list of low-stock ingredients identified by the Inventory Scanner and turns them into draft purchase orders. It calculates how much to order for each ingredient, sends that information to Claude (an AI) for review and annotation, saves the orders to the database, and emails the restaurant manager asking them to approve.

The manager is always in the loop — nothing is sent to a supplier automatically.

---

## How it works — Step by step

### 1. Receive the low-stock items
The agent receives the output from the Inventory Scanner: a list of ingredients that are running low, including each one's current stock level, daily usage rate, and how many days until stockout.

### 2. Calculate how much to order
For every low-stock ingredient, the agent runs a quantity calculation:

- **Formula:** `order_qty = max(par_level − current_stock, daily_usage × (lead_time + 3 days))`
- The "+3 days" is a safety buffer so the restaurant doesn't run out while waiting for the delivery.
- If an ingredient has no supplier assigned, it's skipped — you can't order without knowing who to order from.

### 3. Check for duplicate orders (before calling Claude)
Before making any AI call (which costs money), the agent checks whether a draft purchase order already exists for each supplier *today*. If a supplier already has a draft PO created in the last 24 hours, all their items are skipped. This prevents the agent from creating duplicate orders every 15 minutes.

If all suppliers already have POs for today, the agent stops here and does nothing.

### 4. Ask Claude to review and annotate the orders
The agent sends the full list of orderable items to Claude (the Haiku model, chosen for cost efficiency). Claude receives:
- The restaurant name
- Each ingredient's name, unit, current stock, reorder point, daily usage, days until stockout, supplier, and recommended quantity

Claude's job is to confirm the quantities make sense, group items by supplier, flag anything urgent, and write a short reasoning note for each item. Claude returns structured JSON — a list of orders, one per supplier.

If Claude returns invalid JSON or fails entirely, the error is logged and the agent stops cleanly without crashing.

### 5. Save each order to the database
For every supplier group Claude returned, the agent creates a draft Purchase Order in the database:
- One PO record per supplier
- Each PO contains line items (ingredient, quantity, unit cost)
- Status is `draft` — no money is spent, no email goes to the supplier

Every saved PO is also logged to `agent_logs` with `requires_approval = True`, so it appears in the POS dashboard for the manager to review.

### 6. Email the manager for approval
Once all orders are saved, the agent fetches the manager's email address from the database and sends a "low stock alert" email. The email lists all the items across all draft POs and includes a button linking to the POS dashboard where the manager can approve or reject each order.

---

## Key rules

| Rule | Detail |
|------|--------|
| AI model used | Claude Haiku 4.5 (fastest + cheapest) |
| Max output tokens | 4,096 |
| Duplicate guard | One draft PO per supplier per day |
| Safety buffer | Lead time + 3 extra days of stock |
| Crash protection | Each restaurant and each order is wrapped in its own try/except |

---

## What it does NOT do

- It does not automatically send anything to suppliers.
- It does not approve or execute orders — a human must do that in the dashboard.
- It does not run if the Inventory Scanner found zero low-stock items.
- It does not retry Claude if the AI call fails — it logs the failure and skips gracefully.
