# RestaurantOS Agents — Build Progress Tracker

> This file tracks every chunk of work across all build phases for the **Python AI Agents** repository.
> This is a **separate codebase** from the Next.js POS app (`restaurant-os-app`).
> The two projects share the same Neon PostgreSQL database — that is how they communicate.
> **Update this file every time a chunk is started, completed, or modified.**
> Reference docs: `BIBLE.md` (in this repo), `Company Bible.md` (in the POS repo)

---

## Current Status

- **Current Phase:** 3 — Inventory & Ordering Agents
- **Current Chunk:** 3D complete, 3E next (Railway deployment)
- **Last Updated:** March 11, 2026

---

## Important Notes

- **Language:** Python 3.11+
- **Hosting:** Railway.app (Hobby plan, ~$5-10/mo). This is a 24/7 background worker, NOT a web server.
- **Database:** Same Neon PostgreSQL database as the POS app. Never create new tables here — Drizzle ORM in the Next.js repo manages the schema.
- **AI Model:** Start with Claude Haiku 4.5 for cost efficiency. Upgrade to Sonnet if quality is insufficient.
- **Agent Mode:** Always deploy in "recommend" mode first (agents suggest, humans approve). Only enable autonomous mode after 20+ correct recommendations.
- **The Golden Rule:** Agents observe → reason → act → report. Every action must be logged to `agent_logs`.
- **Email:** Use Resend API for all notifications. Free tier = 100 emails/day, which is plenty.
- **Testing:** Always test locally against the real Neon database (use a test restaurant row) before deploying.

---

## Future Phases (not in current plan, add later)

- Apollo.io integration for sales outreach leads
- Buffer API for social media scheduling
- Autonomous ordering mode (Phase 8A — only after 20+ correct recommendations)
- Multi-language email support
- Twilio SMS alerts as alternative to email
- Slack/WhatsApp notifications for restaurant managers
- Demand forecasting with weather/event data

---

## Phase 1: Project Foundation

> Create the repository, connect to the database, and get the scheduler skeleton running on Railway.

- [x] **1A — Project Setup**
  - Create new GitHub repo: `restaurant-os-agents`
  - Create folder structure: `agents/`, `tools/`, `prompts/`, `tests/`
  - Create `requirements.txt` with all dependencies (asyncpg, anthropic, apscheduler, resend, python-dotenv, sentry-sdk)
  - Create `Procfile` with Railway start command: `worker: python main.py`
  - Create `.env.example` file listing all required environment variables (never commit `.env`)
  - Create `.gitignore` (ignore `.env`, `__pycache__`, `.pytest_cache`)
  - Create empty `__init__.py` in each folder

- [x] **1B — Database Connection Module**
  - Build `tools/database.py` with 8 async functions (see BIBLE.md § Tools Reference):
    - `get_low_stock_ingredients(restaurant_id)` — returns ingredients below reorder_point
    - `get_all_restaurants()` — returns all active restaurant rows
    - `get_depletion_rate(ingredient_id)` — returns daily_usage from ingredient_depletion_rates
    - `save_purchase_order(restaurant_id, supplier_id, lines)` — creates draft PO + lines
    - `log_agent_action(restaurant_id, agent_name, action_type, summary, data, status)` — writes to agent_logs
    - `get_ingredient_by_id(ingredient_id)` — returns full ingredient row
    - `update_depletion_rate(ingredient_id, daily_usage, days_analysed)` — upserts into ingredient_depletion_rates
    - `calculate_depletion_from_sales(ingredient_id, days)` — queries inventory_transactions for daily avg
  - Use `asyncpg` for all queries (async, faster than psycopg2)
  - Use connection pooling (asyncpg.create_pool on startup, close on shutdown)
  - Add error handling: log exceptions to console, never crash the whole process

- [x] **1C — Health Check Server + main.py Skeleton**
  - Create `main.py` as the entry point Railway will run
  - Add a simple HTTP health-check server on port 8080 (see BIBLE.md § Health Check)
  - Add APScheduler with `BackgroundScheduler`
  - Add placeholder job that logs "Scheduler tick" every 15 minutes (proves Railway is running)
  - Add graceful shutdown (catches SIGTERM/SIGINT, stops scheduler cleanly)
  - Deploy to Railway and verify the health endpoint responds with 200 OK

---

## Phase 2: Core Tools

> Build the shared utility modules that all agents will use.

- [x] **2A — Order Quantity Calculator**
  - Build `tools/order_calculator.py`
  - Implement `calculate_order_quantity(current_stock, reorder_point, par_level, daily_usage, lead_time_days)` function
  - Formula: `days_of_stock_needed = lead_time_days + 3` (3-day safety buffer)
  - `order_qty = max(par_level - current_stock, daily_usage × days_of_stock_needed)`
  - Round up to nearest supplier unit (e.g. full kg, full case)
  - Return a dict with: `{ recommended_qty, days_of_coverage, reasoning }`
  - Write tests in `tests/test_calc.py` and verify all edge cases (zero stock, zero depletion rate, etc.)

- [x] **2B — Email Sender**
  - Build `tools/email_sender.py`
  - Use Resend Python SDK
  - Implement `send_low_stock_alert(manager_email, restaurant_name, items, dashboard_url)` — sends formatted HTML email listing all low stock items with "Approve Orders" button
  - Implement `send_weekly_report(manager_email, restaurant_name, report_data, dashboard_url)` — sends weekly margin/waste summary
  - Implement `send_urgent_alert(manager_email, restaurant_name, subject, message)` — for critical issues (stockout imminent, waste spike)
  - All emails use HTML templates with the restaurant name in the subject line
  - Test by sending to your own email first

- [x] **2C — Claude Ordering Prompt**
  - Create `prompts/ordering_system.txt`
  - Write the system prompt Claude receives when drafting purchase orders
  - Prompt must instruct Claude to return **valid JSON only** (no extra text, no markdown fences)
  - JSON schema: `{ "orders": [{ "supplier_id": "...", "supplier_name": "...", "items": [{ "ingredient_id": "...", "name": "...", "quantity": 0.0, "unit": "...", "cost_per_unit": 0.0, "reasoning": "..." }], "total_cost": 0.0, "notes": "..." }] }`
  - Include instructions: group by supplier, flag urgent items, include reasoning for each quantity
  - Keep prompt under 1,000 tokens to minimise API cost

---

## Phase 3: Inventory & Ordering Agents (Core Product)

> Build and deploy the two agents that form the core of the product. This is what generates value for restaurants from day one.

- [x] **3A — Inventory Scanner Agent**
  - Build `agents/inventory.py`
  - Implement `run_inventory_check(restaurant_id)` async function:
    1. Call `get_low_stock_ingredients(restaurant_id)` from database.py
    2. For each low-stock ingredient, call `calculate_depletion_from_sales(ingredient_id, 7)` to get daily usage
    3. Call `update_depletion_rate(ingredient_id, daily_usage, 7)` to save the rate
    4. Return a list of `{ ingredient, daily_usage, days_until_stockout }` dicts
  - If no low-stock items found: log a "No action needed" agent_log and return
  - If items found: hand off to ordering agent
  - Implement `detect_waste_anomalies(restaurant_id)` — compare current week waste vs 4-week average per ingredient; flag if 3× above average; log to agent_logs with status `pending_approval`

- [x] **3B — Ordering Agent**
  - Build `agents/ordering.py`
  - Implement `draft_purchase_orders(restaurant_id, low_stock_items)` async function:
    1. Fetch full ingredient + supplier data for each low-stock item
    2. Run `calculate_order_quantity()` for each item
    3. Build the input payload for Claude (ingredient name, stock, reorder point, daily usage, lead time, cost)
    4. Call Claude API (Haiku 4.5) with the ordering_system.txt prompt
    5. Parse Claude's JSON response
    6. Call `save_purchase_order()` for each supplier group
    7. Call `log_agent_action()` for each order drafted
  - Implement `send_approval_email(restaurant_id, orders_created)` — uses email_sender.py to notify the manager
  - Error handling: if Claude returns invalid JSON, log the failure to agent_logs and skip (do NOT crash)

- [x] **3C — Scheduler Integration**
  - Wire both agents into `main.py`
  - Add `inventory_and_ordering_job()` that:
    1. Calls `get_all_restaurants()`
    2. For each restaurant, runs `run_inventory_check(restaurant_id)`
    3. If low-stock items found, runs `draft_purchase_orders(restaurant_id, items)`
    4. Catches all exceptions per restaurant (one failing restaurant must NOT stop others)
  - Schedule job: every 15 minutes using APScheduler `CronTrigger` (not `IntervalTrigger`, for precision)
  - Add startup log: "RestaurantOS Agents started. Monitoring X restaurants."

- [x] **3D — Test Suite**
  - Build `tests/test_db.py`: test each database function against the real Neon DB using a demo restaurant
  - Build `tests/test_calc.py`: unit tests for order_calculator (no DB needed, pure math)
  - Build `tests/test_agents.py`: integration test that runs a full inventory check → draft cycle against demo data
  - Run `pytest` locally and confirm all pass before deploying

- [ ] **3E — Railway Deployment**
  - Push repo to GitHub
  - Connect GitHub repo to Railway
  - Add all environment variables in Railway dashboard (see BIBLE.md § Environment Variables)
  - Deploy and confirm Railway shows "Running" status
  - Check Railway logs: verify scheduler starts, first job runs, no errors
  - Verify draft purchase orders appear in the POS dashboard's Purchase Orders page
  - Verify agent_logs entries appear in the POS dashboard's Agents page

---

## Phase 4: Pricing Agent

> Build the nightly agent that calculates food costs and generates price recommendations, feeding the Pricing page in the POS dashboard.

- [ ] **4A — Food Cost Snapshot Worker**
  - Build `agents/pricing.py` (part 1: snapshot)
  - Implement `save_food_cost_snapshot(restaurant_id)` async function:
    1. Fetch all active menu items with their recipe_items and ingredient costs
    2. For each item: `food_cost = SUM(ingredient.cost_per_unit × recipe_item.quantity_needed)`
    3. `food_cost_pct = food_cost / menu_item.price × 100`
    4. Write a row to `food_cost_snapshots` table for each item
  - Schedule: run nightly at 02:00 (restaurant is closed, data is stable)
  - This table is what powers the Food Cost Trend chart in the Reports page

- [ ] **4B — Pricing Recommendation Generator**
  - Build pricing recommendation logic inside `agents/pricing.py` (part 2)
  - Implement `generate_pricing_recommendations(restaurant_id)`:
    1. Fetch all items where `food_cost_pct > target_food_cost_pct` (from restaurant settings)
    2. Build input for Claude: item name, current price, food cost, food_cost_pct, target_pct
    3. Claude prompt: "Suggest a new price for each item to bring food cost % to target, within an 8% max increase guardrail. Return JSON."
    4. JSON schema: `{ "recommendations": [{ "menu_item_id": "...", "current_price": 0.0, "recommended_price": 0.0, "reasoning": "...", "projected_food_cost_pct": 0.0 }] }`
    5. Save each recommendation to `pricing_recommendations` table with status `pending`
    6. Log action to agent_logs
  - Create `prompts/pricing_system.txt` with the Claude system prompt
  - Schedule: run nightly at 02:30 (after snapshots are saved)

- [ ] **4C — Pricing Prompt + Test**
  - Write and refine `prompts/pricing_system.txt`
  - Test with real Demo Bistro data: confirm recommendations are sensible
  - Verify recommendations appear in POS dashboard Pricing page (`/dashboard/pricing`)
  - Check that accepting a recommendation in the dashboard updates the menu item price in DB

---

## Phase 5: Customer Success Agent

> Monitors how restaurants are engaging with the platform and sends proactive check-ins to prevent churn.

- [ ] **5A — Engagement Monitor**
  - Build `agents/customer_success.py`
  - Implement `check_restaurant_health(restaurant_id)` that scores:
    - Days since last login (check users.last_login or recent orders as proxy)
    - Orders processed this week vs last week (>20% drop = warning)
    - Food cost % trend (worsening over 2 weeks = warning)
    - Recipes linked to menu items (< 50% linked = onboarding incomplete warning)
  - Return a health score object: `{ score: 0-100, flags: [...], risk_level: "ok"|"at_risk"|"churning" }`
  - Log health checks to agent_logs (status: `completed`, action_type: `health_check`)

- [ ] **5B — Proactive Check-in Emails**
  - Implement `send_checkin_if_needed(restaurant_id, health)`:
    - If `risk_level == "at_risk"`: send a personalised check-in email with specific insights
    - If `risk_level == "churning"`: send an urgent email with a direct offer to help
    - Include 2-3 specific data points in the email body ("Your waste this week was 15% higher than usual")
    - Use `send_urgent_alert()` from email_sender.py
  - Add `customer_success_job()` to main.py, scheduled daily at 08:00

- [ ] **5C — Monthly ROI Summary Email**
  - Implement `send_monthly_roi_summary(restaurant_id)`:
    - Calculate: total orders processed, total waste cost recorded, purchase orders approved, estimated time saved
    - Format as a clean HTML report email
    - Send on the 1st of each month at 09:00
  - Schedule in main.py

---

## Phase 6: Reporting Agent

> Automatically generates summaries and digests without anyone asking for them.

- [ ] **6A — Weekly Client Performance Summary**
  - Build `agents/reporting.py`
  - Implement `send_weekly_summary(restaurant_id)` that emails:
    - Weekly sales total and order count
    - Top 5 selling menu items
    - Food cost % vs target
    - Total waste cost and top waste reason
    - Purchase orders approved vs pending
  - Fetch all data from DB (orders, waste_records, purchase_orders, food_cost_snapshots)
  - Schedule: every Monday at 07:00

- [ ] **6B — Internal Business Metrics Report**
  - Implement `send_internal_report()` (for YOU, the SaaS owner, not the restaurant):
    - Total active restaurants
    - Total agent actions this week
    - Agents with most failures
    - Most active vs least active restaurants
  - Send to your own email
  - Schedule: every Monday at 06:00 (before client reports)

- [ ] **6C — Daily Operations Digest**
  - Implement `send_daily_digest(restaurant_id)` — a short morning email (like a daily briefing):
    - Yesterday's sales summary
    - Any pending purchase orders needing approval
    - Any critical stock warnings (< 1 day of stock)
    - Any waste anomalies flagged overnight
  - Schedule: daily at 07:30

---

## Phase 7: Sales & Marketing Agents (Later — Months 4-6)

> Only build these after you have paying customers and proven value. Do not rush this.

- [ ] **7A — Sales Outreach Agent**
  - `agents/sales.py`
  - Apollo.io API integration to pull restaurant leads weekly
  - Claude generates personalised cold emails referencing specific restaurant details
  - Resend sends emails in batches of 20/day
  - Lead scoring based on email opens/clicks (use Resend webhooks)

- [ ] **7B — Marketing Content Agent**
  - `agents/marketing.py`
  - Claude generates 3 SEO blog posts per week targeting "AI restaurant management" keywords
  - Posts drafted and saved; manual approval before publishing
  - Buffer API integration for LinkedIn/Instagram scheduling (Phase 2 of this agent)

---

## Phase 8: Hardening & Autonomous Mode

> Only build Phase 8A after 20+ consecutive correct recommendations. This is the trust milestone.

- [ ] **8A — Autonomous Ordering Mode**
  - Add `auto_ordering_enabled` flag to restaurant settings
  - If enabled: agents auto-approve and email suppliers directly (no human in the loop)
  - Add hard guardrails: max order value per supplier, max total spend per week
  - Log every autonomous action clearly to agent_logs
  - Send a "We ordered for you" email to manager with full details and a cancel window

- [ ] **8B — Waste Anomaly Detection (Enhanced)**
  - Improve `detect_waste_anomalies()` to use a rolling 28-day average (currently 4 weeks)
  - Add ingredient category context (produce anomalies in summer are expected)
  - Add photo evidence request: if waste spike detected, send manager a "please log this with a photo" nudge
  - Threshold: flag if current week > 2.5× 28-day average (not just 3×, for earlier detection)

- [ ] **8C — Sentry Error Tracking**
  - Add `sentry_sdk.init(dsn=...)` to main.py
  - Wrap all agent job functions in Sentry transaction spans
  - Add a custom tag for `restaurant_id` so errors are traceable per client
  - Test by intentionally throwing an error and verifying Sentry captures it

- [ ] **8D — UptimeRobot Monitoring**
  - Register at uptimerobot.com (free)
  - Add a monitor for the Railway health-check endpoint (port 8080)
  - Set alert threshold: 5-minute downtime = email alert to you
  - Verify the monitor shows "Up" in the UptimeRobot dashboard

---

## Chunk Completion Log

> Each time a chunk is completed, add an entry here with the date, what was done, and any notes.

| Date | Chunk | Summary | Notes |
|------|-------|---------|-------|
| 2026-03-11 | 1A | Created full project structure: agents/, tools/, prompts/, tests/, requirements.txt, Procfile, .env.example, .gitignore, __init__.py files | asyncpg bumped to 0.31.0 for Python 3.14 compatibility |
| 2026-03-11 | 1B | Built tools/database.py with 10 async functions using asyncpg; verified against real Neon DB (3 restaurants found, agent_logs row inserted) | Column names confirmed from schema.ts: stock_qty, quantity_ordered, data (jsonb), no is_active on restaurants |
| 2026-03-11 | 1C | Built main.py: health check server on port 8080, APScheduler with CronTrigger every 15 min, graceful SIGTERM/SIGINT shutdown, keep-alive loop | Health endpoint verified 200 OK; Unicode fix applied for Windows cp1252 console |
| 2026-03-11 | 2A | Built tools/order_calculator.py: calculate_order_quantity() with lead_time+3 buffer formula, rounds up to whole units, urgency flagging; 11 unit tests all pass | Removed tests/__init__.py to fix pytest-asyncio 0.23.0 bug with Python 3.14 |
| 2026-03-11 | 2B | Built tools/email_sender.py: send_low_stock_alert, send_weekly_report, send_urgent_alert, send_monthly_roi_summary — all HTML emails via Resend async wrapper | RESEND_API_KEY still placeholder; test with real key before deploying |
| 2026-03-11 | 2C | Created prompts/ordering_system.txt: strict JSON-only prompt with schema, grouping by supplier, urgency flagging, cost calculation rules | Under 1,000 tokens; covers all edge cases including empty input |
| 2026-03-11 | 3D | Built tests/conftest.py, tests/test_db.py (18 tests), tests/test_agents.py (10 tests); added pytest.ini (asyncio_mode=auto); all 39 tests pass. Fixed waste_records column name: quantity_wasted (not quantity). Function-scoped pool fixtures required for pytest-asyncio 0.23.0 + Python 3.14 event loop compatibility |
| 2026-03-11 | 3C | Wired agents into main.py: replaced placeholder tick with full _run_restaurant() pipeline (inventory scan → draft orders → approval email → waste anomaly check → alert email); per-restaurant try/except isolation; CronTrigger(minute='*/15'), max_instances=1 |
| 2026-03-11 | 3B | Built agents/ordering.py: draft_purchase_orders() calls calculate_order_quantity, sends payload to Claude Haiku, parses JSON, saves POs with duplicate guard (get_existing_draft_po_today added to DB); send_approval_email() fetches manager email + sends low_stock_alert | Claude call wrapped in asyncio.to_thread; invalid JSON logs failure and skips, never crashes |
| 2026-03-11 | 3A | Built agents/inventory.py: run_inventory_check() fetches low-stock items, calculates 7-day depletion rates, upserts rates, returns enriched list; detect_waste_anomalies() flags 3× anomalies with pending_approval logs. Added get_waste_by_ingredient() to tools/database.py | math.inf used for days_until_stockout when daily_usage=0 (serialised as null in JSON log) |
