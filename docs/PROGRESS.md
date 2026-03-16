# RestaurantOS Agents — Build Progress Tracker

> This file tracks every chunk of work across all build phases for the **Python AI Agents** repository.
> This is a **separate codebase** from the Next.js POS app (`restaurant-os-app`).
> The two projects share the same Neon PostgreSQL database — that is how they communicate.
> **Update this file every time a chunk is started, completed, or modified.**
> Reference docs: `BIBLE.md` (in this repo), `Company Bible.md` (in the POS repo)

---

## Current Status

- **Current Phase:** 6 — Reporting & Analytics Agent (complete)
- **Current Chunk:** Next: Internal Platform (see spec below) or Phase 7
- **Last Updated:** March 16, 2026

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
| 2026-03-16 | 6A–6M | Built full Reporting & Analytics Agent. SQL provided for 4 new tables (weekly_report_snapshots, analytics_anomalies, platform_weekly_summaries, metric_benchmarks). Created tools/metrics/ with 6 modules (revenue, food_cost, inventory, menu, ops, platform). Built tools/anomaly_detector.py (7 anomaly types: revenue_drop/spike, new_record_high, food_cost_spike, waste_surge, stock_out_spike, dish_margin_collapse). Built tools/report_builder.py: runs all metrics concurrently with asyncio.gather(), benchmark comparisons, upserts snapshot, detects anomalies. Added 2 Claude prompts (analytics_narrator + platform_intelligence, JSON-only). Added send_analytics_report() + send_platform_intelligence() to email_sender.py. Added 3 DB helpers (get_active_clients, mark_report_sent, upsert_platform_weekly_summary). Built agents/reporting.py with full Phase 1 (per-restaurant) + Phase 2 (platform intelligence) pipeline using claude-sonnet-4-6. Wired CronTrigger(day_of_week='mon', hour=6) into main.py. 16 new tests in test_reporting.py. | subscriptions/client_health_scores tables queried defensively (may not exist yet); revenue computed from order_items×price; PLATFORM_REPORT_EMAIL env var required for platform email |
