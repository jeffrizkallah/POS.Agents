# RestaurantOS Agents — Build Progress Tracker

> This file tracks every chunk of work across all build phases for the **Python AI Agents** repository.
> This is a **separate codebase** from the Next.js POS app (`restaurant-os-app`).
> The two projects share the same Neon PostgreSQL database — that is how they communicate.
> **Update this file every time a chunk is started, completed, or modified.**
> Reference docs: `BIBLE.md` (in this repo), `Company Bible.md` (in the POS repo)

---

## Current Status

- **Current Phase:** 14 — Sales & Marketing Agents (complete)
- **Current Chunk:** Next: Phase 15A — Autonomous Ordering Mode (only after 20+ correct recommendations)
- **Last Updated:** March 24, 2026

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

## Internal Platform (New Project — Build After Phase 6)

> A standalone internal company platform, separate from the POS app and the agents repo. Product-agnostic — designed to manage all products the company sells, not just the POS system.

**Why a new project:** The POS app is a client-facing product. The agents repo is a background worker. Neither is the right place for internal company operations tooling.

**What it will include (v1):**
- Client management dashboard — all restaurants, health scores, risk levels across all products
- Subscription / MRR tracking per client
- Customer success tools — check-in email history, manual notes, onboarding status
- Agent monitoring — activity logs, last run, recommendations actioned per client
- Platform intelligence UI — reads from `platform_weekly_summaries` and `client_health_scores`
- Foundation for managing future products beyond the POS system

**Data source:** Same Neon PostgreSQL DB. The agents (Phase 5 + 6) populate `client_health_scores`, `platform_weekly_summaries`, `analytics_anomalies` — the internal platform just reads and displays them.

**Build order:** Finish Phase 5 + Phase 6 agents first. By then the DB will have real populated data to build the UI against.

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

- [x] **3E — Railway Deployment**
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

- [x] **4A — Food Cost Snapshot Worker**
  - Build `agents/pricing.py` (part 1: snapshot)
  - Implement `save_food_cost_snapshot(restaurant_id)` async function:
    1. Fetch all active menu items with their recipe_items and ingredient costs
    2. For each item: `food_cost = SUM(ingredient.cost_per_unit × recipe_item.quantity_needed)`
    3. `food_cost_pct = food_cost / menu_item.price × 100`
    4. Write a row to `food_cost_snapshots` table for each item
  - Schedule: run nightly at 02:00 (restaurant is closed, data is stable)
  - This table is what powers the Food Cost Trend chart in the Reports page

- [x] **4B — Pricing Recommendation Generator**
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

- [x] **4C — Pricing Prompt + Test**
  - Write and refine `prompts/pricing_system.txt`
  - Test with real Demo Bistro data: confirm recommendations are sensible
  - Verify recommendations appear in POS dashboard Pricing page (`/dashboard/pricing`)
  - Check that accepting a recommendation in the dashboard updates the menu item price in DB

- [x] **4D — Multi-Factor Classification Engine**
  - Created `tools/pricing_calculator.py`: pure-Python, no DB, fully testable
    - `calculate_cm(selling_price, ingredient_cost)`
    - `calculate_avg_cm(items)` — average CM across all menu items
    - `classify_menu_item(food_cost_pct, target, cm, avg_cm)` → underpriced_star / problem / true_star / plowhorse
    - `requires_multi_cycle_flag(current_price, ingredient_cost, target_pct, max_increase_pct)`
  - Updated `agents/pricing.py`: fetches all items to compute avg_cm, classifies each over-target item, enriches Claude payload with `cm`, `avg_cm`, `classification`, `multi_cycle_flag`
  - Updated `prompts/pricing_system.txt`: classification-aware reasoning rules per quadrant
  - Created `docs/PRICING_DECISION_TREE.md`: authoritative decision tree reference doc
  - Added 11 new unit tests (all 21 pricing tests pass)

---

## Phase 5: Customer Success Agent

> Monitors how restaurants are engaging with the platform and sends proactive check-ins to prevent churn.

- [x] **5A — Engagement Monitor**
  - Build `agents/customer_success.py`
  - Implement `check_restaurant_health(restaurant_id)` that scores:
    - Days since last login (check users.last_login or recent orders as proxy)
    - Orders processed this week vs last week (>20% drop = warning)
    - Food cost % trend (worsening over 2 weeks = warning)
    - Recipes linked to menu items (< 50% linked = onboarding incomplete warning)
  - Return a health score object: `{ score: 0-100, flags: [...], risk_level: "ok"|"at_risk"|"churning" }`
  - Log health checks to agent_logs (status: `completed`, action_type: `health_check`)

- [x] **5B — Proactive Check-in Emails**
  - Implement `send_checkin_if_needed(restaurant_id, health)`:
    - If `risk_level == "at_risk"`: send a personalised check-in email with specific insights
    - If `risk_level == "churning"`: send an urgent email with a direct offer to help
    - Include 2-3 specific data points in the email body ("Your waste this week was 15% higher than usual")
    - Use `send_urgent_alert()` from email_sender.py
  - Add `customer_success_job()` to main.py, scheduled daily at 08:00

- [x] **5C — Monthly ROI Summary Email**
  - Implement `send_monthly_roi_summary(restaurant_id)`:
    - Calculate: total orders processed, total waste cost recorded, purchase orders approved, estimated time saved
    - Format as a clean HTML report email
    - Send on the 1st of each month at 09:00
  - Schedule in main.py

---

## Phase 6: Reporting & Analytics Agent

> The intelligence layer. Every Monday at 6 AM UTC, calculates 40+ metrics per restaurant, detects anomalies, sends executive-level analytics reports to each owner, and generates an internal platform intelligence briefing. Full spec: `docs/RestaurantOS_Reporting_And_Analytics_Agent.md`.

- [x] **6A — Database Tables**
  - Run the following 4 new tables in Neon SQL Editor (spec Part 3):
    - `weekly_report_snapshots` — stores computed metrics per restaurant per week (revenue, food cost, inventory, menu, ops domains + metadata). UNIQUE(restaurant_id, week_start).
    - `analytics_anomalies` — flags unusual patterns (revenue_drop, food_cost_spike, waste_surge, stock_out_spike, dish_margin_collapse, new_record_high). Severity: info/warning/critical.
    - `platform_weekly_summaries` — one row per week; platform-wide aggregates (MRR, client health bands, churn, total revenue).
    - `metric_benchmarks` — pre-loaded industry benchmarks (food_cost_pct=30%, waste_rate_pct=5%, avg_spend_per_cover=$28, etc.). Seeded with 10 rows on CONFLICT DO NOTHING.
  - Create indexes: idx_weekly_snapshots_restaurant, idx_anomalies_restaurant
  - Verify all 4 tables exist in Neon console before proceeding

- [x] **6B — New File Structure**
  - Create folder `tools/metrics/` with empty `__init__.py`
  - Create 6 empty metric module files:
    - `tools/metrics/revenue_metrics.py`
    - `tools/metrics/food_cost_metrics.py`
    - `tools/metrics/inventory_metrics.py`
    - `tools/metrics/menu_metrics.py`
    - `tools/metrics/ops_metrics.py`
    - `tools/metrics/platform_metrics.py`
  - Create empty: `tools/anomaly_detector.py`, `tools/report_builder.py`, `agents/reporting.py`
  - Create empty: `prompts/analytics_narrator.txt`, `prompts/platform_intelligence.txt`

- [x] **6C — Revenue Metrics Module** (`tools/metrics/revenue_metrics.py`)
  - `async def get_revenue_metrics(restaurant_id, week_start, week_end) -> dict:`
    - gross_revenue (SUM paid orders), total_covers, avg_spend_per_cover
    - prev_week_revenue → revenue_wow_pct (week-over-week %)
    - four_weeks_ago_revenue → revenue_mom_pct (month-over-month %)
    - void_count, void_rate_pct
    - peak_hour (0-23), peak_hour_revenue (EXTRACT HOUR from created_at)
    - All keys match weekly_report_snapshots columns. COALESCE NULLs to 0.
  - `async def get_revenue_by_category(restaurant_id, week_start, week_end) -> list:`
    - JOIN order_items → menu_items → menu_categories
    - GROUP BY category, SUM revenue, compute pct_of_total. Sort DESC.

- [x] **6D — Food Cost Metrics Module** (`tools/metrics/food_cost_metrics.py`)
  - `async def get_food_cost_metrics(restaurant_id, week_start, week_end) -> dict:`
    - food_cost_pct: AVG(food_cost_pct) FROM food_cost_snapshots in window
    - food_cost_trend: compare current week avg vs 2-week prior avg → 'improving'/'deteriorating'/'stable' (±1% threshold)
    - top_margin_killer: dish with highest food_cost_pct in window (name + pct)
    - top_star_dish: dish with lowest food_cost_pct (name + pct)
    - estimated_margin_loss: SUM of (food_cost_pct - 30)/100 × selling_price × sales_count for dishes > 30%
    - pricing_agent_recovery: SUM of estimated recovery from accepted ai_pricing_recommendations in window
  - `async def get_dish_performance(restaurant_id, week_start, week_end) -> list:`
    - Per menu item: dish_name, food_cost_pct, selling_price, ingredient_cost, classification, sales_count, revenue_contribution. ORDER BY food_cost_pct DESC LIMIT 20.

- [x] **6E — Inventory Metrics Module** (`tools/metrics/inventory_metrics.py`)
  - `async def get_inventory_metrics(restaurant_id, week_start, week_end) -> dict:`
    - waste_events from inventory_transactions WHERE type='waste': total qty, event count
    - total_usage: SUM(ABS(quantity_change)) WHERE type='sale'
    - waste_rate_pct: waste_qty / (total_usage + waste_qty) × 100
    - stock_out_count: days where any ingredient had stock_qty = 0
    - avg_days_stock_cover: AVG(stock_qty / daily_usage) across ingredients with reorder_point > 0
    - po_cycle_time_days: AVG(received_at - created_at) for completed POs last 30 days
    - Handle division by zero and NULL with COALESCE
  - `async def get_waste_by_ingredient(restaurant_id, week_start, week_end) -> list:`
    - JOIN inventory_transactions → ingredients WHERE type='waste'. GROUP BY ingredient. ORDER BY total_wasted DESC LIMIT 10.

- [x] **6F — Menu + Ops Metrics Modules**
  - `tools/metrics/menu_metrics.py` — `async def get_menu_metrics(...) -> dict:`
    - top_dish (name + count from order_items for paid orders)
    - star_to_dog_ratio: count(classification IN ('Star','Plow Horse')) / total items
    - attachment_rate: COUNT sides+drinks order_items / COUNT mains order_items
    - category_mix: GROUP BY category, COUNT, percent of total
    - Returns: top_dish_name, top_dish_count, star_to_dog_ratio, attachment_rate
  - `async def get_full_menu_performance(...) -> list:` — name, category, sales_count, revenue, food_cost_pct, classification. ORDER BY sales_count DESC.
  - `tools/metrics/ops_metrics.py` — `async def get_ops_metrics(...) -> dict:`
    - table_turn_rate: COUNT(paid orders) / COUNT(tables) / 7
    - orders_by_hour: list of {hour: int, count: int} for all 24 hours
    - recommendation_action_rate: actioned ai_pricing_recommendations / total in window × 100
    - agent_run_count: COUNT FROM agent_logs in window for this restaurant
    - login_frequency: {total_logins, unique_days} from login_events in window

- [x] **6G — Platform Metrics Module** (`tools/metrics/platform_metrics.py`)
  - `async def get_platform_metrics(week_start, week_end) -> dict:` — NO restaurant_id filter, platform-wide:
    - total_active_clients (subscriptions WHERE status IN ('active','trialing'))
    - total_mrr, mrr_at_risk (JOIN client_health_scores WHERE score_band IN ('at_risk','critical'))
    - avg_client_health (AVG total_score from client_health_scores WHERE score_date = today)
    - clients_by_band: dict {band: count} from client_health_scores
    - new_clients_this_week, churned_this_week (from subscriptions created_at/cancelled_at)
    - total_platform_revenue, total_platform_covers (SUM across all restaurants)
    - avg_food_cost_pct (AVG from food_cost_snapshots in window)
    - agent_total_runs (COUNT from agent_logs in window)
    - feature_adoption_pct: % of restaurants using all 3 key features (pricing, POs, waste)
  - `async def get_client_league_table(week_start, week_end) -> list:`
    - Per active restaurant: name, gross_revenue, food_cost_pct, health_score, recommendation_action_rate. ORDER BY gross_revenue DESC.

- [x] **6H — Anomaly Detector** (`tools/anomaly_detector.py`)
  - `async def detect_anomalies(restaurant_id, current_metrics, previous_metrics) -> list:`
    - Revenue drop: current < previous × 0.80 → severity='critical', type='revenue_drop'
    - Revenue spike: current > previous × 1.25 → severity='info', type='revenue_spike'
    - Food cost spike: current food_cost_pct > previous + 3 → severity='warning', type='food_cost_spike'
    - Waste surge: current waste_rate_pct > previous + 2 → severity='warning', type='waste_surge'
    - Stock-out spike: current stock_out_count > previous + 2 → severity='warning', type='stock_out_spike'
    - New record: current gross_revenue > all-time max → severity='info', type='new_record_high'
    - Margin collapse: top_margin_killer_pct > 45 → severity='critical', type='dish_margin_collapse'
    - For each: calculate change_pct, save to analytics_anomalies (ON CONFLICT DO NOTHING), return list
  - Helper: `async def get_all_time_max_revenue(restaurant_id)` — SELECT MAX(gross_revenue) FROM weekly_report_snapshots
  - Helper: `async def get_previous_week_metrics(restaurant_id, week_start)` — fetch prior week snapshot dict
  - Helper: `async def save_anomaly(...)` — INSERT into analytics_anomalies

- [x] **6I — Report Builder** (`tools/report_builder.py`)
  - `async def build_report_package(restaurant_id, restaurant_name, week_start, week_end) -> dict:`
    1. Run all 5 metric modules concurrently with asyncio.gather()
    2. Fetch benchmarks from metric_benchmarks as {metric_name: benchmark_value}
    3. Fetch previous week's snapshot from weekly_report_snapshots for comparison
    4. Compute benchmark comparisons for food_cost_pct, waste_rate_pct, avg_spend_per_cover, table_turn_rate: {value, benchmark, vs_benchmark, better_than_benchmark}
    5. Upsert core metrics to weekly_report_snapshots
    6. Run detect_anomalies() comparing current vs previous week
    7. Return full package dict: {restaurant_name, week_start, week_end, revenue, food_cost, inventory, menu, ops, benchmarks, anomalies, previous_week}
  - Wrap in try/except — return empty dict on failure

- [x] **6J — Claude Prompts**
  - `prompts/analytics_narrator.txt` — instructs Claude to write report narrative sections as raw JSON only (no markdown fences). Fields: headline, executive_summary, revenue_narrative, food_cost_narrative, inventory_narrative, menu_narrative, ops_narrative, anomaly_highlights (array with title/description/severity/action), top_recommendation, benchmark_commentary, closing. Style rules: exact numbers, short paragraphs, write for busy restaurant owner, no buzzwords. (Full prompt text in spec Part 8 Step 9.)
  - `prompts/platform_intelligence.txt` — instructs Claude to write internal platform briefing as raw JSON. Fields: week_headline, mrr_commentary, health_distribution_commentary, top_performer, most_at_risk, platform_revenue_commentary, feature_adoption_commentary, agent_performance_commentary, three_priorities (array), one_thing_going_well, one_thing_to_watch. Rules: exact numbers, actionable priorities, write like briefing a co-founder. (Full prompt text in spec Part 8 Step 10.)

- [x] **6K — New Email Functions** (add to `tools/email_sender.py`)
  - `send_analytics_report(to_email, restaurant_name, report_package, narrative)`:
    - Header: indigo bg, white text, week dates
    - Headline (narrative['headline']) in large bold indigo
    - Executive Summary box
    - Anomaly alert cards (red=critical, amber=warning, blue=info) with title + description + action
    - 4 metric cards (2×2 grid): Revenue, Food Cost, Inventory, Menu — each with key numbers + narrative
    - Benchmark comparison section
    - Top Recommendation highlighted box
    - Footer with dashboard link
    - Subject: `f'Weekly Analytics: {restaurant_name} — w/e {week_end_date}'`
  - `send_platform_intelligence(to_email, platform_narrative, platform_metrics, league_table)`:
    - Dark header, week headline, 4 KPI cards (MRR, MRR at Risk, Avg Health Score, Active Clients)
    - Client health band visual, Three Priorities numbered list
    - Client League Table (top 5 by revenue), one_thing_going_well (green), one_thing_to_watch (amber)
    - Subject: `f'Platform Intelligence — Week of {date}'`

- [x] **6L — Main Reporting Agent** (`agents/reporting.py`)
  - `async def run_reporting_agent():`
    - Calculate window: week_end = today - 1 day, week_start = week_end - 6 days
    - **Phase 1 — Per-restaurant reports:** for each client in get_active_clients():
      - Call build_report_package() — skip if empty
      - Load analytics_narrator.txt, call Claude (claude-sonnet-4-6, max_tokens=3000), parse JSON narrative
      - Fetch owner email from users table (role='owner' or 'manager')
      - Call send_analytics_report()
      - UPDATE weekly_report_snapshots SET report_sent=TRUE
      - log_agent_action(action_type='analytics_report_sent')
      - asyncio.sleep(3) between clients
    - **Phase 2 — Platform intelligence:**
      - get_platform_metrics() + get_client_league_table()
      - Upsert to platform_weekly_summaries
      - Load platform_intelligence.txt, call Claude (max_tokens=2000), parse JSON narrative
      - send_platform_intelligence() to PLATFORM_REPORT_EMAIL env var
      - log_agent_action(action_type='platform_intelligence_sent')
    - **Final:** send_slack_alert() with summary (reports sent, total revenue, anomalies, runtime)
    - log_agent_action(action_type='weekly_run_complete')
  - Schedule: CronTrigger(day_of_week='mon', hour=6, minute=0) in main.py
  - Add `from agents.reporting import run_reporting_agent` to main.py imports

- [x] **6M — Seed Test Data + Test Suite**
  - Seed SQL (spec Part 13 Step 11): DO $$ block creating 5 paid orders/day × 14 days for test restaurant + order_items. Verify with SELECT COUNT/SUM query.
  - Create `test_reporting_modules.py`: runs all 4 metric modules against real DB for first restaurant, prints JSON output. Run: `python test_reporting_modules.py`.
  - Create `test_reporting.py`: calls `asyncio.run(run_reporting_agent())`. Run: `python test_reporting.py`.
  - Expected output: report window logged, N clients processed, revenue + food cost printed per restaurant, Phase 2 platform intelligence built, Reporting Agent done.
  - Verify in Neon: weekly_report_snapshots row exists, analytics_anomalies detected, platform_weekly_summaries saved, agent_logs entry with action_type='weekly_run_complete'.

---

## Phase 7: Multi-Client Foundation

> Build the generic config layer that makes all new agents plug-and-play for any company. Nothing in Phase 8–13 works without this. Full spec: `docs/NewAgents_Spec.md`.

- [x] **7A — Core Config Tables (DB)**
  - Create the following tables in the database (SQL run in Neon SQL Editor):
    - `clients` — one row per company (`id, name, owner_email, owner_whatsapp, timezone, currency, is_active`)
    - `brands` — one or many per client (`id, client_id, name, industry, business_model, primary_channel, tone, language_primary, language_secondary, target_audience, avg_deal_value, avg_customer_ltv, currency, roi_target_multiplier, is_active`)
    - `brand_channels` — platform credentials per brand (`id, brand_id, platform, account_id, access_token, is_active`)
    - `brand_keywords` — SEO/content keywords per brand (`id, brand_id, keyword, intent, cluster_topic, is_priority, status`)
    - `brand_content_config` — post frequency + pillars per brand per platform (`id, brand_id, platform, posts_per_week, content_pillars jsonb, word_limit_step1, word_limit_subsequent`)
    - `brand_care_config` — at-risk keywords + escalation rules + retention offers per brand (`id, brand_id, at_risk_keywords text[], escalation_triggers text[], retention_offer_template`)
    - `industry_roi_benchmarks` — shared benchmarks by industry + channel (`id, industry, channel, typical_roi_min, typical_roi_max`)
  - Seed at least one test client + one test brand before proceeding
  - Verify all tables exist in Neon console

- [x] **7B — Multi-Tenant DB Functions**
  - Add to `tools/database.py`:
    - `get_all_clients()` — returns all active clients
    - `get_brands_for_client(client_id)` — returns all active brands for a client
    - `get_brand_channels(brand_id)` — returns platform credentials
    - `get_brand_config(brand_id)` — returns brand row (tone, language, audience, ROI target, etc.)
    - `get_brand_content_config(brand_id)` — returns content schedule config
    - `get_brand_care_config(brand_id)` — returns at-risk keywords + escalation rules
    - `get_industry_benchmarks(industry)` — returns ROI benchmarks for a given industry
    - `log_client_agent_action(client_id, brand_id, agent_name, action_type, summary, data, status)` — writes to `client_agent_activity`
  - `client_agent_activity` table: `id, client_id, brand_id, agent_name, action_type, summary, data jsonb, status, duration_ms, created_at`

- [x] **7C — Scheduler Multi-Client Loop Pattern**
  - Update `main.py` to support a second loop pattern alongside the existing restaurant loop:
    ```python
    async def _async_client_agent_job(agent_fn):
        clients = await get_all_clients(pool)
        for client in clients:
            brands = await get_brands_for_client(pool, client["id"])
            for brand in brands:
                try:
                    await agent_fn(pool, client, brand)
                except Exception as e:
                    print(f"[Agent] {brand['name']}: {e}")
    ```
  - This wrapper is reused by all 6 new agents — write it once
  - Test by seeding a test client + brand and verifying the loop runs without errors

---

## Phase 8: Orchestrator Agent

> Master governance layer. Must be built first — all other new agents log to it and route approvals through it. Full spec: `docs/NewAgents_Spec.md § Agent 6`.

- [x] **8A — Approval & Activity Tables (DB)**
  - Create in Neon SQL Editor:
    - `client_approval_requests` — `id, client_id, brand_id, agent_name, approval_type, payload jsonb, status (pending|approved|rejected|expired), expires_at, decided_at, created_at`
    - `client_agent_activity` — `id, client_id, brand_id, agent_name, action_type, result, duration_ms, error_message, created_at`
    - `client_roi_snapshots` — `id, client_id, period_start, period_end, total_spend, total_revenue, platform_cost, spend_by_channel jsonb, revenue_by_channel jsonb, channels_below_target jsonb, compounding_channels jsonb, created_at`
    - `client_business_targets` — `id, client_id, period, targets jsonb, actuals jsonb, status, created_at`
    - `client_budget_envelopes` — `id, client_id, channel, allocated_amount, spent_amount, roi_current, consecutive_below_roi_months, status (active|paused), updated_at`
    - `client_spend_entries` — `id, client_id, brand_id, channel, amount, currency, description, recorded_at`
    - `client_revenue_entries` — `id, client_id, brand_id, channel, amount, currency, source, recorded_at`
    - `client_intelligence` — `id, client_id, report_type, content jsonb, urgency, created_at`

- [x] **8B — Orchestrator DB Functions**
  - Add to `tools/database.py`:
    - `get_pending_approvals(client_id)` — returns all `status=pending` approval requests
    - `save_approval_request(client_id, brand_id, agent_name, approval_type, payload, expires_at)` — inserts approval request
    - `update_approval_status(approval_id, status)` — sets approved/rejected/expired
    - `get_roi_by_channel(client_id, days)` — computes rolling ROI per channel from spend + revenue tables
    - `get_budget_envelopes(client_id)` — returns all channel budgets
    - `save_roi_snapshot(client_id, snapshot_data)` — upserts ROI snapshot
    - `save_intelligence(client_id, report_type, content, urgency)` — saves briefing/alert

- [x] **8C — Orchestrator Agent**
  - Build `agents/orchestrator.py`
  - Implement `run_orchestrator(pool, client, brand)`:
    1. Fetch pending approvals — route each to owner via email (WhatsApp integration optional Phase 2)
    2. Check for overdue approvals (>12h) — send reminder; mark expired after deadline
    3. Execute approved actions (update lead stage, mark outreach as sent, publish post, etc.)
    4. Fetch ROI by channel — classify each with color system (green/yellow/red/black)
    5. Flag channels below `brand.roi_target_multiplier` for reallocation proposal
  - Implement `run_daily_briefing(pool, client, brand)`:
    1. Pull pending approvals + recent agent activity + ROI status + urgent intelligence
    2. Call Claude (`prompts/orchestrator_briefing.txt`) — returns briefing JSON
    3. Email briefing to `client.owner_email`
  - Schedule in `main.py`:
    - `orchestrator_job()` — `CronTrigger(hour='*/4')` (every 4 hours)
    - `daily_briefing_job()` — `CronTrigger(hour=7, minute=30)` weekdays

- [x] **8D — Orchestrator Prompts**
  - `prompts/orchestrator_core.txt` — ROI law, approval routing framework, autonomous vs approval-required actions, escalation rules. JSON-only output.
  - `prompts/orchestrator_briefing.txt` — Daily briefing generator. Receives pending items + ROI status + recent activity. Returns: `{headline, pending_count, urgent_items[], roi_status{}, recent_wins[], one_watch_item}`. JSON-only.
  - `prompts/orchestrator_roi.txt` — ROI analysis. Reallocation triggers, compounding signal detection. JSON-only.

- [x] **8E — Tests**
  - `tests/test_orchestrator.py`: test approval routing, ROI classification, briefing generation
  - Seed test approvals in DB and verify Orchestrator picks them up and emails correctly
  - Verify `client_agent_activity` rows are written on each run

---

## Phase 9: Scout Agent

> Lead discovery and qualification. Finds potential customers for a brand, scores them, queues for owner approval. Full spec: `docs/NewAgents_Spec.md § Agent 1`.

- [x] **9A — Scout Tables (DB)**
  - Create in Neon SQL Editor:
    - `client_prospects` — `id, client_id, brand_id, name, website, industry, size_signal, location, qualification_score, fit_signals jsonb, roi_estimate, source, status (researched|qualified|disqualified), created_at`
    - `client_leads` — `id, client_id, brand_id, prospect_id, stage (pending_approval|identified|outreach_started|responded|won|lost), contract_value_estimate, renewal_date, created_at`
    - `client_contracts` — `id, client_id, brand_id, lead_id, value, start_date, renewal_date, status (active|expired|at_risk), created_at`

- [x] **9B — Scout DB Functions**
  - Add to `tools/database.py`:
    - `get_unqualified_prospects(client_id, brand_id, limit)` — returns prospects needing qualification
    - `save_prospect(client_id, brand_id, prospect_data)` — inserts prospect
    - `update_prospect_score(prospect_id, score, fit_signals)` — updates qualification result
    - `save_lead(client_id, brand_id, prospect_id, stage)` — creates lead from qualified prospect
    - `get_contracts_nearing_renewal(client_id, days)` — returns contracts with renewal_date within N days

- [x] **9C — Scout Agent**
  - Build `agents/scout.py`
  - Implement `run_scout(pool, client, brand)`:
    1. Fetch brand config (target_audience, industry, avg_deal_value, roi_target_multiplier)
    2. Fetch up to 3 unqualified prospects from `client_prospects`
    3. For each prospect, call Claude (`prompts/scout_qualify.txt`) — receives brand config + prospect signals, returns score + reasoning + fit_signals + roi_estimate
    4. Save score; if ≥ threshold (default 6), save to `client_leads` with `stage=pending_approval` and create approval request via Orchestrator
    5. Check `client_contracts` for renewals within 90 days — save renewal alert to `client_intelligence`
  - Schedule: `CronTrigger(day_of_week='mon-fri', hour=7, minute=0)`

- [x] **9D — Scout Prompts**
  - `prompts/scout_qualify.txt` — Generic qualification framework. Receives: brand config + prospect data. Returns: `{score, reasoning, fit_signals[], roi_estimate, recommended_action}`. JSON-only. Never hallucinate signals not in input.
  - `prompts/scout_research.txt` — Research brief generator. Given brand target audience, outputs what signals to look for and how to weight them. JSON-only.

- [x] **9E — Tests**
  - `tests/test_scout.py`: test qualification scoring, renewal detection, approval request creation
  - Seed test prospects with known signals and verify correct scores returned

---

## Phase 10: Pipeline Agent

> Generates personalised outreach sequences for approved leads. Never sends anything without owner approval. Full spec: `docs/NewAgents_Spec.md § Agent 2`.

- [x] **10A — Pipeline Tables (DB)**
  - Create in Neon SQL Editor:
    - `client_outreach` — `id, client_id, brand_id, lead_id, sequence_type (new_acquisition|renewal|nurture), step_number, channel, subject, body, word_count, status (draft|pending_approval|approved|sent|failed), scheduled_for, sent_at, created_at`
    - `client_nurture_messages` — `id, client_id, brand_id, subscriber_id, funnel_stage, channel, body, status (pending_approval|approved|sent), created_at`

- [x] **10B — Pipeline DB Functions**
  - Add to `tools/database.py`:
    - `get_approved_leads(client_id, brand_id)` — returns leads with `stage=identified` (approved by Orchestrator)
    - `get_outreach_sequence(lead_id)` — returns all steps for a lead
    - `save_outreach_step(client_id, brand_id, lead_id, step_data)` — inserts one sequence step
    - `get_due_outreach_steps(client_id)` — returns approved steps where `scheduled_for <= now`
    - `mark_outreach_sent(outreach_id)` — updates status to sent + sets sent_at
    - `get_draft_steps_due_for_promotion(client_id)` — returns draft steps whose prev step is sent and due date passed
    - `update_outreach_status(outreach_id, status)` — sets status on any outreach step

- [x] **10C — Pipeline Agent**
  - Built `agents/pipeline.py`
  - `run_pipeline(pool, client, brand)`:
    1. Fetches approved leads (stage=identified) with no existing sequence
    2. Calls Claude (pipeline_sequence.txt) — 5-step sequence JSON
    3. Saves Step 1 as pending_approval, Steps 2–5 as draft with scheduled_for dates
    4. Creates approval request for Step 1 via Orchestrator (48h expiry)
    5. Marks approved+due steps as sent; promotes next draft step to pending_approval
  - Schedule: `CronTrigger(day_of_week='mon-fri', hour=9, minute=0)`

- [x] **10D — Pipeline Prompts**
  - `prompts/pipeline_sequence.txt` — Generic outreach sequence. Receives brand config (tone, channel, language, word limits) + lead signals. Returns: `{sequence_type, channel, steps: [{step, day, subject, body, word_count}]}`. JSON-only. Adapts tone to config — never hardcoded.
  - `prompts/pipeline_nurture.txt` — Stage-based nurture messages. Receives brand config + subscriber funnel stage. Returns: `{channel, body, word_count, cta}`. JSON-only.

- [x] **10E — Tests**
  - `tests/test_pipeline.py`: 12 tests — step day constants, DB functions, sequence creation, step 1 pending_approval gate, Steps 2–5 draft, mark_outreach_sent, due step detection, approval request creation, run_pipeline no-crash

---

## Phase 11: Customer Care Agent

> Feedback triage, response drafting, competitor intelligence, and monthly strategic opportunity analysis. Full spec: `docs/NewAgents_Spec.md § Agent 5`.

- [x] **11A — Customer Care Tables (DB)**
  - Create in Neon SQL Editor:
    - `client_feedback` — `id, client_id, brand_id, channel (email|whatsapp|qr|web), text, sentiment_score, feedback_type (complaint|testimonial|suggestion|neutral), urgency (critical|urgent|normal|low), is_at_risk_flag, response_draft, status (new|classified|pending_approval|responded), created_at`
    - `client_testimonials` — `id, client_id, brand_id, feedback_id, quote_original, quote_edited, permission_granted_at, status (pending_permission|approved|published), created_at`
    - `client_qr_codes` — `id, client_id, brand_id, code, purpose, linked_entity, scan_count, feedback_count, created_at`
    - `client_competitors` — `id, client_id, brand_id, name, website_url, instagram_handle, google_maps_place_id, is_active, created_at`
    - `client_competitor_snapshots` — `id, client_id, competitor_id, snapshot_month, website_summary, google_rating, google_reviews_sample jsonb, instagram_data jsonb, actual_strengths text[], actual_weaknesses text[], positioning_summary, created_at`
    - `client_strategic_reports` — `id, client_id, brand_id, competitors_analysed int, landscape_summary, universal_complaints text[], unserved_needs text[], opportunities jsonb, executive_summary, status (pending_approval|approved), created_at`

- [x] **11B — Customer Care DB Functions**
  - Add to `tools/database.py`:
    - `get_new_feedback(client_id, brand_id)` — returns unprocessed feedback
    - `save_feedback_classification(feedback_id, classification_data)` — updates type, urgency, sentiment, at_risk_flag, response_draft
    - `get_competitors(client_id, brand_id)` — returns active competitor list
    - `save_competitor_snapshot(client_id, competitor_id, snapshot_data)` — upserts monthly snapshot
    - `save_strategic_report(client_id, brand_id, report_data)` — inserts report + approval request

- [x] **11C — Customer Care Agent**
  - Build `agents/customer_care.py`
  - Implement `run_care_feedback(pool, client, brand)` (runs every 30 min):
    1. Fetch new unprocessed feedback
    2. For each: call Claude (`prompts/care_classify.txt`) — returns type, urgency, sentiment, at_risk_flag
    3. If critical urgency: immediately save to `client_intelligence` with urgency=critical (Orchestrator will escalate)
    4. Call Claude (`prompts/care_respond.txt`) — returns response draft in brand tone + language
    5. Save classification + response draft; set `status=pending_approval`; create approval request via Orchestrator
    6. If sentiment ≥ 8/10: add testimonial request to response draft
  - Implement `run_competitive_intel(pool, client, brand)` (runs 1st of month):
    1. Fetch competitor list
    2. For each competitor: pull Google reviews (SerpAPI), scrape website
    3. Call Claude (`prompts/care_competitor.txt`) — returns strengths, weaknesses, positioning
    4. Save monthly snapshot
    5. Call Claude (`prompts/care_strategy.txt`) — ELIMINATE/REDUCE/RAISE/CREATE analysis with ROI filter from `brand.roi_target_multiplier`
    6. Save strategic report as `pending_approval`; create approval request via Orchestrator
  - Schedule in `main.py`:
    - `care_feedback_job()` — `CronTrigger(minute='*/30')`
    - `care_intel_job()` — `CronTrigger(day=1, hour=6, minute=0)`

- [x] **11D — Customer Care Prompts**
  - `prompts/care_classify.txt` — Feedback classifier. Receives brand config (tone, at_risk_keywords, avg_customer_ltv) + feedback text. Returns: `{feedback_type, urgency, sentiment_score, is_at_risk_flag, at_risk_reason}`. JSON-only.
  - `prompts/care_respond.txt` — Response drafter. Receives brand config (tone, language, word_limit, retention_offer) + classified feedback. Returns: `{response_draft, includes_retention_offer, includes_testimonial_request}`. JSON-only.
  - `prompts/care_competitor.txt` — Competitor profiler. Receives reviews + website summary. Returns: `{actual_strengths[], actual_weaknesses[], positioning_summary, key_gaps[]}`. JSON-only. Evidence-based only — 3+ mentions required to call something a weakness.
  - `prompts/care_strategy.txt` — Strategic opportunity analyzer. ELIMINATE/REDUCE/RAISE/CREATE framework. Receives competitive data + brand roi_target. Returns: `{opportunities[{action, framework_category, evidence, projected_roi, implementation_cost_estimate}], executive_summary}`. JSON-only.

- [x] **11E — Tests**
  - `tests/test_customer_care.py`: test feedback classification accuracy, at-risk flag detection, response tone matching brand config, ROI filter on strategic opportunities
  - Seed test feedback with known signals; verify correct urgency + at-risk classification

---

## Phase 12: Broadcast Agent

> Social media content generation, scheduling, publishing, and comment management. Adapts to any brand's tone, channels, and language. Full spec: `docs/NewAgents_Spec.md § Agent 3`.

- [x] **12A — Broadcast Tables (DB)**
  - Create in Neon SQL Editor:
    - `client_social_posts` — `id, client_id, brand_id, platform, post_type, content_pillar, caption, caption_secondary_language, visual_brief, hashtags text[], status (pending_approval|approved|published|failed), scheduled_for, published_at, likes_count, comments_count, reach, impressions, engagement_rate, last_engagement_sync, created_at`
    - `client_social_comments` — `id, client_id, brand_id, post_id, platform_comment_id, text, sentiment (positive|neutral|negative|spam), requires_reply, reply_draft, status (pending_approval|approved|sent|escalated), escalation_reason, created_at`

- [x] **12B — Broadcast DB Functions**
  - Add to `tools/database.py`:
    - `get_approved_posts(client_id)` — returns posts `status=approved` where `scheduled_for <= now`
    - `save_social_post(client_id, brand_id, post_data)` — inserts draft post
    - `update_post_status(post_id, status)` — marks published/failed
    - `update_post_engagement(post_id, metrics)` — updates likes, comments, reach, etc.
    - `get_recent_comments(client_id, brand_id, since)` — returns unprocessed comments
    - `save_comment_classification(comment_id, classification_data)` — saves sentiment + reply draft

- [x] **12C — Broadcast Agent**
  - Build `agents/broadcast.py`
  - Implement `run_content_batch(pool, client, brand)` (runs Monday 6am):
    1. Fetch brand content config (platforms, posts_per_week, pillars, word limits)
    2. Fetch brand channels for credentials
    3. For each active platform: call Claude (`prompts/broadcast_post.txt`) to generate weekly posts
    4. Save each post as `pending_approval`; create approval request via Orchestrator
  - Implement `run_publish_queue(pool, client, brand)` (runs every 30 min):
    1. Fetch approved posts with `scheduled_for <= now`
    2. Publish to platform API (Instagram Graph API / LinkedIn API)
    3. Update `status=published`; log to `client_agent_activity`
  - Implement `run_engagement_sync(pool, client, brand)` (runs every 2 hours):
    1. Fetch published posts from last 30 days
    2. Pull metrics from platform API
    3. Update engagement fields in `client_social_posts`
    4. Fetch new comments; call Claude (`prompts/broadcast_comment.txt`) to classify + draft reply
    5. If escalation needed: save to `client_intelligence`; otherwise save reply as `pending_approval`
  - Schedule in `main.py`:
    - `broadcast_batch_job()` — `CronTrigger(day_of_week='mon', hour=6, minute=0)`
    - `broadcast_publish_job()` — `CronTrigger(minute='*/30')`
    - `broadcast_engagement_job()` — `CronTrigger(hour='*/2')`

- [x] **12D — Broadcast Prompts**
  - `prompts/broadcast_post.txt` — Post generator. Receives: brand config (tone, platform, pillar, language_primary, language_secondary, word_limit, audience) + catalog items. Returns: `{caption, caption_secondary_language, visual_brief, hashtags[], content_pillar}`. JSON-only. Bilingual only when `language_secondary` is set.
  - `prompts/broadcast_comment.txt` — Comment classifier + reply drafter. Receives: brand config (tone, word_limit) + comment text. Returns: `{sentiment, requires_reply, reply_draft, escalate_to_human, escalation_reason}`. JSON-only.

- [x] **12E — Tests**
  - `tests/test_broadcast.py`: test content generation for different platforms/tones, bilingual output when configured, comment classification, escalation logic
  - Verify posts are saved as `pending_approval` and not published until approved

---

## Phase 13: SEO Engine Agent

> Generates SEO keyword clusters and long-form articles for any brand in any industry. Full spec: `docs/NewAgents_Spec.md § Agent 4`.

- [x] **13A — SEO Tables (DB)**
  - Create in Neon SQL Editor:
    - `client_seo_content` — `id, client_id, brand_id, keyword_id, title, slug, content_markdown, meta_title, meta_description, schema_markup jsonb, word_count, seo_score, status (pending_approval|approved|published), published_at, created_at`
  - `brand_keywords` table already created in Phase 7A — verify it exists

- [x] **13B — SEO DB Functions**
  - Add to `tools/database.py`:
    - `get_priority_keywords(brand_id, limit)` — returns keywords with `status=identified`, ordered by `is_priority DESC`
    - `get_published_slugs(client_id, brand_id)` — returns slugs of published articles (to avoid duplication)
    - `save_seo_article(client_id, brand_id, keyword_id, article_data)` — inserts article as `pending_approval`
    - `update_keyword_status(keyword_id, status)` — marks `identified → in_progress → published`
    - `save_keyword_cluster(brand_id, keywords)` — inserts new keyword cluster rows

- [x] **13C — SEO Engine Agent**
  - Build `agents/seo_engine.py`
  - Implement `run_seo_engine(pool, client, brand)`:
    1. Fetch brand config (industry, target_audience, location)
    2. Call Claude (`prompts/seo_keywords.txt`) to generate new keyword clusters based on brand industry + audience — save any new keywords not already in DB
    3. Fetch priority keywords (`status=identified`, up to 4 per brand per week)
    4. Fetch published slugs to pass as context (avoid duplication)
    5. For each keyword: call Claude (`prompts/seo_article.txt`) — returns full article with schema, meta, FAQ
    6. Save article as `pending_approval`; mark keyword `status=in_progress`; create approval request via Orchestrator
  - Schedule: `CronTrigger(day_of_week='mon', hour=6, minute=0)` (runs alongside broadcast batch)

- [x] **13D — SEO Prompts**
  - `prompts/seo_keywords.txt` — Keyword cluster generator. Receives: brand industry + target audience + location. Returns: `{clusters: [{cluster_topic, keywords: [{keyword, intent, search_volume_estimate, difficulty_estimate}]}]}`. JSON-only.
  - `prompts/seo_article.txt` — SEO article generator. Receives: brand config + primary keyword + secondary keywords + existing slugs + word count target. Returns: `{title, slug, content_markdown, meta_title, meta_description, schema_markup, word_count, seo_score, faq_count}`. JSON-only. Primary keyword must appear in H1, first 80 words, one H2, and meta description. 4+ FAQ items required.

- [x] **13E — Tests**
  - `tests/test_seo_engine.py`: test keyword cluster generation, article structure (keyword placement, FAQ count, word count range, seo_score present), duplicate slug prevention
  - Seed test keywords and verify article is saved as `pending_approval` with correct fields

---

## Phase 14: Sales & Marketing Agents (Later — Months 4-6)

> Only build these after you have paying customers and proven value. Do not rush this.

- [x] **14A — Sales Outreach Agent**
  - `agents/sales.py`
  - Apollo.io API integration to pull restaurant leads weekly
  - Claude generates personalised cold emails referencing specific restaurant details
  - Resend sends emails in batches of 20/day
  - Lead scoring based on email opens/clicks (use Resend webhooks)

- [x] **14B — Marketing Content Agent**
  - `agents/marketing.py`
  - Claude generates 3 SEO blog posts per week targeting "AI restaurant management" keywords
  - Posts drafted and saved; manual approval before publishing
  - Buffer API integration for LinkedIn/Instagram scheduling (Phase 2 of this agent)

---

## Phase 15: Hardening & Autonomous Mode

> Only build Phase 15A after 20+ consecutive correct recommendations. This is the trust milestone.

- [ ] **15A — Autonomous Ordering Mode**
  - Add `auto_ordering_enabled` flag to restaurant settings
  - If enabled: agents auto-approve and email suppliers directly (no human in the loop)
  - Add hard guardrails: max order value per supplier, max total spend per week
  - Log every autonomous action clearly to agent_logs
  - Send a "We ordered for you" email to manager with full details and a cancel window

- [ ] **15B — Waste Anomaly Detection (Enhanced)**
  - Improve `detect_waste_anomalies()` to use a rolling 28-day average (currently 4 weeks)
  - Add ingredient category context (produce anomalies in summer are expected)
  - Add photo evidence request: if waste spike detected, send manager a "please log this with a photo" nudge
  - Threshold: flag if current week > 2.5× 28-day average (not just 3×, for earlier detection)

- [ ] **15C — Sentry Error Tracking**
  - Add `sentry_sdk.init(dsn=...)` to main.py
  - Wrap all agent job functions in Sentry transaction spans
  - Add a custom tag for `restaurant_id` so errors are traceable per client
  - Test by intentionally throwing an error and verifying Sentry captures it

- [ ] **15D — UptimeRobot Monitoring**
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
| 2026-03-11 | 3E | Initialized git repo, committed all 22 files (3228 lines), pushed to github.com/jeffrizkallah/POS.Agents on branch master | .env and venv/ correctly excluded by .gitignore |
| 2026-03-11 | 3D | Built tests/conftest.py, tests/test_db.py (18 tests), tests/test_agents.py (10 tests); added pytest.ini (asyncio_mode=auto); all 39 tests pass. Fixed waste_records column name: quantity_wasted (not quantity). Function-scoped pool fixtures required for pytest-asyncio 0.23.0 + Python 3.14 event loop compatibility |
| 2026-03-11 | 3C | Wired agents into main.py: replaced placeholder tick with full _run_restaurant() pipeline (inventory scan → draft orders → approval email → waste anomaly check → alert email); per-restaurant try/except isolation; CronTrigger(minute='*/15'), max_instances=1 |
| 2026-03-11 | 3B | Built agents/ordering.py: draft_purchase_orders() calls calculate_order_quantity, sends payload to Claude Haiku, parses JSON, saves POs with duplicate guard (get_existing_draft_po_today added to DB); send_approval_email() fetches manager email + sends low_stock_alert | Claude call wrapped in asyncio.to_thread; invalid JSON logs failure and skips, never crashes |
| 2026-03-11 | 3A | Built agents/inventory.py: run_inventory_check() fetches low-stock items, calculates 7-day depletion rates, upserts rates, returns enriched list; detect_waste_anomalies() flags 3× anomalies with pending_approval logs. Added get_waste_by_ingredient() to tools/database.py | math.inf used for days_until_stockout when daily_usage=0 (serialised as null in JSON log) |
| 2026-03-11 | 4A | Added 5 pricing DB functions to tools/database.py: get_menu_items_with_costs, save_food_cost_snapshot, get_over_target_menu_items, save_pricing_recommendation, get_existing_pricing_recommendation_today. Built agents/pricing.py part 1: save_food_cost_snapshots() | Real table names: food_cost_snapshots (columns: ingredient_cost, selling_price, snapshot_date), ai_pricing_recommendations. menu_item_id is INTEGER not UUID |
| 2026-03-11 | 4B | Built agents/pricing.py part 2: generate_pricing_recommendations() calls Claude Haiku, enforces 8% max increase guardrail, saves to ai_pricing_recommendations; duplicate guard checks today's pending recs. Created prompts/pricing_system.txt | Claude returns recommendations list; current_food_cost_pct saved alongside projected |
| 2026-03-11 | 4C | Wired food_cost_snapshot_job (02:00) and pricing_recommendation_job (02:30) into main.py. Built tests/test_pricing.py with 10 tests covering DB helpers, snapshots, recommendations, guardrail, bad JSON, and no-over-target cases | All 49 tests pass (11 calc + 18 db + 10 agents + 10 pricing) |
| 2026-03-12 | 4D | Created tools/pricing_calculator.py (4 pure functions: calculate_cm, calculate_avg_cm, classify_menu_item, requires_multi_cycle_flag). Updated agents/pricing.py to classify items before calling Claude. Updated prompts/pricing_system.txt with classification-aware rules. Created docs/PRICING_DECISION_TREE.md. Added 11 unit tests. | All 21 pricing tests pass (60 total) |
| 2026-03-12 | 4E | Added estimate_volume_impact() and get_sales_data_status() to pricing_calculator.py. Added get_sales_volume_by_menu_item() to database.py. Updated agents/pricing.py to fetch 30-day sales volumes, pass to Claude, and compute post-recommendation volume impact via elasticity (-1.5). Volume note appended to reasoning; rec dict now includes projected_volume_change_pct, units_sold_30d, sales_data_status. Updated pricing_system.txt with sales data strategy + no-history fallback rules. Added 6 unit tests. | All 27 pricing tests pass |
| 2026-03-12 | 4F | Fixed: accepted price recommendations now apply to menu_items.price. Added get_approved_pricing_recommendations() + apply_pricing_recommendation() to database.py. Added apply_approved_recommendations() to agents/pricing.py (polls every 15 min alongside inventory job). Fixed: inventory "no low-stock" events no longer written to agent_logs (console-only) — prevents log spam on agents page. | |
| 2026-03-14 | 5A–5C | Built agents/customer_success.py: check_restaurant_health() scores 0–100 across 4 signals (login recency, order stability, food cost trend, recipe coverage); send_checkin_if_needed() emails at_risk/churning restaurants; send_monthly_roi_summary_email() runs 1st of month. Added 6 DB helpers to database.py. Added send_checkin_email() to email_sender.py. Wired customer_success_job (daily 08:00) + monthly_roi_job (1st of month 09:00) into main.py. 21 new tests — all 81 pass. | users.last_login falls back gracefully to None if column absent |
| 2026-03-16 | cost-fix | Moved ordering agent duplicate guard to before Claude call. Previously Claude was called every 15 min even when POs already existed for the day. Now filters out already-covered suppliers first and skips Claude entirely if all suppliers have draft POs today. | |
| 2026-03-19 | 6N (consumption) | Added get_consumption_analysis() to tools/metrics/inventory_metrics.py. Formula: Opening + Purchased = Production + Closing. Splits ingredients into recipe ingredients (consumed via production_batch_inputs) and unitary items (consumed via sale inventory_transactions). Variance per ingredient: positive=over_purchased, negative=production_discrepancy. Waste excluded intentionally. Wired into report_builder.py asyncio.gather(). Added CONSUMPTION ANALYSIS section to Claude narrator in agents/reporting.py. Updated AGENT_REPORTING.md. | production_batches.restaurant_id is NULL in POS — bug in POS app's production batch save endpoint; must be fixed in Next.js before this analysis returns data |
| 2026-03-16 | 6A–6M | Built full Reporting & Analytics Agent. SQL provided for 4 new tables (weekly_report_snapshots, analytics_anomalies, platform_weekly_summaries, metric_benchmarks). Created tools/metrics/ with 6 modules (revenue, food_cost, inventory, menu, ops, platform). Built tools/anomaly_detector.py (7 anomaly types: revenue_drop/spike, new_record_high, food_cost_spike, waste_surge, stock_out_spike, dish_margin_collapse). Built tools/report_builder.py: runs all metrics concurrently with asyncio.gather(), benchmark comparisons, upserts snapshot, detects anomalies. Added 2 Claude prompts (analytics_narrator + platform_intelligence, JSON-only). Added send_analytics_report() + send_platform_intelligence() to email_sender.py. Added 3 DB helpers (get_active_clients, mark_report_sent, upsert_platform_weekly_summary). Built agents/reporting.py with full Phase 1 (per-restaurant) + Phase 2 (platform intelligence) pipeline using claude-sonnet-4-6. Wired CronTrigger(day_of_week='mon', hour=6) into main.py. 16 new tests in test_reporting.py. | subscriptions/client_health_scores tables queried defensively (may not exist yet); revenue computed from order_items×price; PLATFORM_REPORT_EMAIL env var required for platform email |
| 2026-03-23 | 7A–7C | Built Multi-Client Foundation. SQL file at docs/phase7_sql.sql: 8 tables (clients, brands, brand_channels, brand_keywords, brand_content_config, brand_care_config, industry_roi_benchmarks, client_agent_activity) + 12 seeded industry benchmarks + test client/brand. Added 8 DB functions to tools/database.py (get_all_clients, get_brands_for_client, get_brand_channels, get_brand_config, get_brand_content_config, get_brand_care_config, get_industry_benchmarks, log_client_agent_action). Added _async_client_agent_job() reusable loop to main.py. | Run docs/phase7_sql.sql in Neon SQL Editor before deploying. All Phase 8-13 agents use _async_client_agent_job(agent_fn) as their scheduler wrapper. |
| 2026-03-23 | 8A–8E | Built Orchestrator Agent. SQL at docs/phase8_sql.sql: 7 new tables (client_approval_requests, client_roi_snapshots, client_business_targets, client_budget_envelopes, client_spend_entries, client_revenue_entries, client_intelligence). Added 7 DB functions to database.py (get_pending_approvals, save_approval_request, update_approval_status, get_roi_by_channel, get_budget_envelopes, save_roi_snapshot, save_intelligence, get_recent_intelligence). Built agents/orchestrator.py: run_orchestrator() routes approvals, sends 12h reminders, expires overdue, classifies ROI (green/yellow/red/black), saves snapshots; run_daily_briefing() calls Claude Haiku + emails structured briefing to owner. Three prompts: orchestrator_core.txt (ROI law + routing rules), orchestrator_briefing.txt (daily email generator), orchestrator_roi.txt (reallocation analyzer). Wired orchestrator_job (every 4h) + daily_briefing_job (weekdays 07:30) into main.py. 11 tests in tests/test_orchestrator.py. | Run docs/phase8_sql.sql in Neon SQL Editor before deploying. client_agent_activity already exists from Phase 7B — SQL uses CREATE TABLE IF NOT EXISTS throughout. |
| 2026-03-23 | 9A–9E | Built Scout Agent. SQL at docs/phase9_sql.sql: 3 new tables (client_prospects, client_leads, client_contracts) + 3 seeded test prospects. Added 5 DB functions to database.py (get_unqualified_prospects, save_prospect, update_prospect_score, save_lead, get_contracts_nearing_renewal). Built agents/scout.py: run_scout() fetches up to 3 unqualified prospects, calls Claude Haiku (scout_qualify.txt) to score each against brand config, saves score+fit_signals, promotes score≥6 to client_leads with pending_approval stage and creates Orchestrator approval request, checks client_contracts for renewals within 90 days and saves renewal alerts to client_intelligence. Two prompts: scout_qualify.txt (prospect qualification framework), scout_research.txt (ICP research brief generator). Wired scout_job (weekdays 07:00) into main.py using _async_client_agent_job(). 13 tests in tests/test_scout.py — all pass. | Run docs/phase9_sql.sql in Neon SQL Editor before deploying. Scout runs before daily briefing (07:00 vs 07:30) so new leads appear in that day's briefing. |
| 2026-03-23 | 11A–11E | Built Customer Care Agent. SQL at docs/phase11_sql.sql: 6 new tables (client_feedback, client_testimonials, client_qr_codes, client_competitors, client_competitor_snapshots, client_strategic_reports). Added 6 DB functions to database.py (get_new_feedback, save_feedback_classification, save_testimonial, get_competitors, save_competitor_snapshot, save_strategic_report). Built agents/customer_care.py: run_care_feedback() classifies each feedback item with Claude Haiku (care_classify.txt), escalates critical items to client_intelligence, drafts responses (care_respond.txt), saves pending_approval + creates Orchestrator approval request, queues testimonials at sentiment≥8; run_competitive_intel() profiles each competitor (care_competitor.txt), saves monthly snapshots, generates ELIMINATE/REDUCE/RAISE/CREATE strategy (care_strategy.txt), saves strategic report as pending_approval. Four prompts created. Wired care_feedback_job (every 30 min) + care_intel_job (1st of month 06:00) into main.py. 16 tests in tests/test_customer_care.py — all pass. | Run docs/phase11_sql.sql in Neon SQL Editor before deploying. Competitive intel uses Claude's general knowledge as a fallback when no live scrape data is available — wire in SerpAPI/Playwright for real data in production. |
| 2026-03-24 | 13A–13E | Built SEO Engine Agent. SQL at docs/phase13_sql.sql: 1 new table (client_seo_content with unique slug per client+brand). Added 5 DB functions to database.py (get_priority_keywords, get_published_slugs, save_seo_article, update_keyword_status, save_keyword_cluster). Built agents/seo_engine.py: run_seo_engine() calls Claude Haiku (seo_keywords.txt) to generate keyword clusters + saves new keywords; fetches up to 4 priority keywords per run; calls Claude Haiku (seo_article.txt) per keyword to write 1200+ word articles with FAQ + schema_markup; saves as pending_approval + marks keyword in_progress + creates Orchestrator approval request (72h expiry). Two prompts created. Wired seo_engine_job (Monday 06:00, alongside broadcast) into main.py. 14 tests — 13 pass immediately; 14th (integration) verified agent works in test run (generated 24 keywords + 1,247-word article live). | SQL run in Neon. Schedule: CronTrigger(day_of_week='mon', hour=6, minute=0). Slug collision prevention: ON CONFLICT DO NOTHING + runtime dedup. |
| 2026-03-24 | 14A–14B | Built Sales & Marketing Agents. SQL at docs/phase14_sql.sql: 4 new tables (company_leads, company_outreach, company_marketing_keywords, company_blog_posts) + 10 seeded priority marketing keywords. Added 13 DB functions to database.py (8 for sales: get_new_company_leads, save_company_lead, update_company_lead_score, save_outreach_draft, get_approved_outreach_batch, mark_company_outreach_sent, record_email_engagement; 5 for marketing: get_pending_marketing_keywords, get_published_blog_slugs, save_blog_post, update_marketing_keyword_status, save_marketing_keyword_cluster). Built agents/sales.py: weekly Apollo.io People Search pull (_fetch_apollo_people → _parse_apollo_person → upsert); Claude Haiku qualification scoring (0–10, sales_qualify.txt); Claude Haiku cold email generation (sales_cold_email.txt, <120 words, <50 char subject); daily batch of 20 sends via Resend (run_sales_batch); record_email_engagement() stub for Resend webhook tracking. Built agents/marketing.py: weekly keyword cluster generation (marketing_keywords.txt, 3–5 clusters, 4–6 kw each); weekly blog post generation (marketing_article.txt, 1,500 words, SEO score, FAQ schema); Buffer API publish stub (wire BUFFER_ACCESS_TOKEN in production); daily publish job marks posts published. Four prompts created. Wired 4 scheduler jobs: sales_apollo_job (Mon 08:00), sales_batch_job (weekdays 10:00), marketing_content_job (Mon 07:00), marketing_publish_job (weekdays 10:30). Added requests>=2.32.0 to requirements.txt. 27 tests across test_sales.py + test_marketing.py. SQL run in Neon (all 4 tables created). | Note: This is company-level outbound sales for RestaurantOS itself — NOT the multi-client Scout/Pipeline agents. APOLLO_API_KEY + SALES_FROM_NAME + BUFFER_ACCESS_TOKEN + MARKETING_SITE_URL env vars required. |\n| 2026-03-23 | 10A–10E | Built Pipeline Agent. SQL at docs/phase10_sql.sql: 2 new tables (client_outreach with UNIQUE(lead_id, step_number), client_nurture_messages) + 5 indexes. Added 7 DB functions to database.py (get_approved_leads, get_outreach_sequence, save_outreach_step, get_due_outreach_steps, mark_outreach_sent, get_draft_steps_due_for_promotion, update_outreach_status). Built agents/pipeline.py: run_pipeline() fetches approved leads (stage=identified) with no existing sequence, calls Claude Haiku (pipeline_sequence.txt) to generate 5-step sequence, saves Step 1 as pending_approval + Steps 2-5 as draft with STEP_DAYS offsets (0/3/7/14/21), creates approval request for Step 1 (48h expiry); on each run also marks approved+due steps as sent and promotes ready drafts to pending_approval. Two prompts: pipeline_sequence.txt (5-step outreach generator with tone/channel/language adaptation), pipeline_nurture.txt (stage-based nurture message generator). Wired pipeline_job (weekdays 09:00) into main.py. 12 tests in tests/test_pipeline.py. SQL run in Neon. | Pipeline runs after scout (07:00) and briefing (07:30), so new sequences are ready before owner checks their 9am briefing. |
| 2026-03-23 | 12A–12E | Built Broadcast Agent. SQL run in Neon: 2 new tables (client_social_posts, client_social_comments) + 4 indexes. Added 6 DB functions to database.py (save_social_post, get_approved_posts, update_post_status, update_post_engagement, get_recent_comments, save_comment_classification). Built agents/broadcast.py: run_content_batch() calls Claude Haiku (broadcast_post.txt) to generate posts_per_week posts per platform, saves each as pending_approval + creates Orchestrator approval request; run_publish_queue() publishes approved posts via platform stub (wire Instagram/LinkedIn API in production); run_engagement_sync() fetches unprocessed comments, calls Claude Haiku (broadcast_comment.txt) to classify + draft reply, escalates to client_intelligence if escalate_to_human=true. Two prompts: broadcast_post.txt (weekly post generator, bilingual when language_secondary set), broadcast_comment.txt (comment classifier + reply drafter). Wired broadcast_batch_job (Mon 06:00), broadcast_publish_job (every 30 min), broadcast_engagement_job (every 2 hours) into main.py. 14 tests in tests/test_broadcast.py — all pass. | Platform publishing is stubbed — wire real Instagram Graph API / LinkedIn API via brand_channels credentials in production. |
