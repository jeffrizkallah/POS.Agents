# RestaurantOS Agents — Project Bible

> **This is the reference document for the `restaurant-os-agents` Python repository.**
> Read this before starting any task. It tells you what this project is, how it works, what files do what, and how to avoid breaking things.
> The companion document for the Next.js web app lives in `docs/Company Bible.md` inside the `restaurant-os-app` repo.

---

## Table of Contents

1. [What This Project Is](#1-what-this-project-is)
2. [How the Two Projects Communicate](#2-how-the-two-projects-communicate)
3. [The Six AI Agents — Overview](#3-the-six-ai-agents--overview)
4. [Agent 1: Inventory & Ordering (Build First)](#4-agent-1-inventory--ordering-build-first)
5. [Agent 2: Pricing Strategy](#5-agent-2-pricing-strategy)
6. [Agent 3: Customer Success](#6-agent-3-customer-success)
7. [Agent 4: Reporting & Analytics](#7-agent-4-reporting--analytics)
8. [Agent 5: Sales Outreach (Later)](#8-agent-5-sales-outreach-later)
9. [Agent 6: Marketing & Content (Later)](#9-agent-6-marketing--content-later)
10. [Database Tables — What Agents Read and Write](#10-database-tables--what-agents-read-and-write)
11. [File Structure](#11-file-structure)
12. [Tech Stack & Dependencies](#12-tech-stack--dependencies)
13. [Environment Variables](#13-environment-variables)
14. [Tools Reference (tools/)](#14-tools-reference-tools)
15. [How Claude API Is Used](#15-how-claude-api-is-used)
16. [Scheduling — How Jobs Run](#16-scheduling--how-jobs-run)
17. [Health Check Endpoint](#17-health-check-endpoint)
18. [Deploying to Railway](#18-deploying-to-railway)
19. [Testing Locally](#19-testing-locally)
20. [Rules & Guardrails](#20-rules--guardrails)

---

## 1. What This Project Is

This is a **Python background worker** that runs 24/7 on Railway.app. It is the AI brain behind RestaurantOS. It has no website, no API, no user interface. It is invisible — it runs behind the scenes while restaurant owners use the Next.js dashboard.

**What it does in plain English:**
Every 15 minutes, it wakes up, checks the database to see if any restaurant is running low on stock. If something is low, it figures out how much to order, asks Claude AI to draft a purchase order with clear reasoning, saves that draft to the database, and sends an email to the restaurant manager saying "You have orders to approve." The manager opens the dashboard, clicks Approve, and goes back to work.

**Why it exists separately from the Next.js app:**
The web app runs on Vercel, which is designed for HTTP requests — things that happen when a user clicks a button. Vercel functions time out after 10-30 seconds. The agents need to run continuously, on a timer, forever. Railway is designed exactly for this — persistent background processes that never stop.

**The key rule:** These two systems (Next.js + Python) **never talk to each other directly**. They both read and write to the same Neon PostgreSQL database. That database is the shared brain. The agents write draft orders → the dashboard reads them → manager approves → agents see the approval on next scan.

---

## 2. How the Two Projects Communicate

```
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│  Next.js Web App (Vercel)       │         │  Python Agents (Railway)        │
│                                 │         │                                 │
│  Restaurant managers log in.    │ READS   │  Wakes up every 15 minutes.     │
│  They approve orders, view      │◄───────►│  Checks stock, calls Claude,    │
│  reports, and use the POS.      │ WRITES  │  drafts orders, sends emails.   │
│                                 │         │                                 │
└────────────────┬────────────────┘         └────────────────┬────────────────┘
                 │                                           │
                 └──────────────────┬────────────────────────┘
                                    │
                        ┌───────────▼───────────┐
                        │  Neon PostgreSQL DB   │
                        │  (shared brain)       │
                        └───────────────────────┘
```

**Agents WRITE to:**
- `purchase_orders` — draft orders they generate
- `purchase_order_lines` — line items in each order
- `agent_logs` — a record of every action taken
- `ingredient_depletion_rates` — calculated daily usage per ingredient
- `food_cost_snapshots` — nightly food cost % per menu item
- `pricing_recommendations` — AI-generated price suggestions

**Agents READ from:**
- `restaurants` — to know which restaurants to monitor
- `ingredients` — current stock levels, par levels, reorder points, cost
- `suppliers` — email addresses for notifications
- `inventory_transactions` — to calculate how fast stock is being used
- `purchase_orders` — to check if an order was already approved/dismissed
- `recipes` / `recipe_items` — to calculate food cost per menu item
- `menu_items` — current selling prices
- `waste_records` — to detect waste spikes
- `users` — manager email addresses for notifications

**Agents must NEVER:**
- Modify `orders`, `order_items`, or any POS data (that's the POS's job)
- Delete any rows (agents only insert and update)
- Change authentication data (users, sessions)
- Drop or alter database tables (schema is managed by Drizzle ORM in the Next.js repo)

---

## 3. The Six AI Agents — Overview

| # | Agent Name | When It Runs | What It Does | Build Phase |
|---|-----------|-------------|-------------|-------------|
| 1 | **Inventory & Ordering** | Every 15 min | Checks stock → drafts purchase orders | Phase 3 (first) |
| 2 | **Pricing Strategy** | Nightly at 02:00 | Calculates food costs → generates price recommendations | Phase 4 |
| 3 | **Customer Success** | Daily at 08:00 | Monitors engagement → sends at-risk check-in emails | Phase 5 |
| 4 | **Reporting & Analytics** | Weekly (Mon 07:00) | Generates performance summaries for each restaurant | Phase 6 |
| 5 | **Sales Outreach** | Weekly | Pulls leads from Apollo.io → sends cold emails | Phase 7 (later) |
| 6 | **Marketing & Content** | 3× per week | Generates blog + social media content via Claude | Phase 7 (later) |

**Build order rule:** Build 1 first, verify it works in production, then build 2, and so on. Never build all six at once.

---

## 4. Agent 1: Inventory & Ordering (Build First)

### What It Does
This is the core product. It is the reason restaurants pay for RestaurantOS.

Every 15 minutes:
1. Connects to the database and fetches all active restaurants
2. For each restaurant, checks: which ingredients are below their `reorder_point`?
3. For each low-stock ingredient, calculates the daily usage rate from the last 7 days of `inventory_transactions` (type = 'sale')
4. Saves the daily usage rate to `ingredient_depletion_rates`
5. Calculates how many days of stock remain: `days_remaining = stock_qty / daily_usage`
6. Calls Claude API with all low-stock items and asks it to draft purchase orders grouped by supplier
7. Saves draft purchase orders to `purchase_orders` and `purchase_order_lines`
8. Logs the action to `agent_logs`
9. Emails the restaurant manager: "You have X orders to approve"

Also runs a waste anomaly check:
- Compares this week's waste for each ingredient vs the 28-day rolling average
- If any ingredient is 3× above average, logs a warning to `agent_logs` with `status = 'pending_approval'`
- Emails the manager with an alert

### Files Involved
- `agents/inventory.py` — the scanner (detects low stock, calculates depletion)
- `agents/ordering.py` — the drafter (calls Claude, saves orders, sends email)
- `tools/database.py` — all DB queries
- `tools/order_calculator.py` — the math for quantity calculation
- `tools/email_sender.py` — sends email via Resend
- `prompts/ordering_system.txt` — Claude's instructions

### The Quantity Formula
```
days_of_stock_needed = lead_time_days + 3   # 3-day safety buffer
smart_order_qty = max(
    par_level - current_stock,
    daily_usage × days_of_stock_needed
)
# Round up to whole supplier units (e.g. 1kg bags, full cases)
```

### Example Flow
```
Demo Bistro | 08:00 check
→ Chicken Breast: stock=1.2kg, reorder_point=2kg ← LOW
→ Daily usage (last 7 days): avg 0.8kg/day
→ Days remaining: 1.2 / 0.8 = 1.5 days
→ Supplier lead time: 2 days → ORDER URGENTLY
→ Claude drafts: order 5kg from Metro Foods (lead_time + buffer + low stock)
→ Draft PO saved to DB (status='draft')
→ Agent log saved (action_type='draft_purchase_order')
→ Email sent to sarah@demobistro.ae: "1 order needs approval"
→ Sarah opens dashboard, clicks Approve. Done.
```

---

## 5. Agent 2: Pricing Strategy

### What It Does
Runs nightly. Calculates real food cost for every active menu item. Compares against the restaurant's target food cost % (default: 30%). If any item is above target, asks Claude to suggest a better price. Saves recommendations to `pricing_recommendations` table. The manager sees them in the Pricing page and can Accept, Edit, or Dismiss each one.

### Schedule
- 02:00 — Save food cost snapshots for all restaurants
- 02:30 — Generate pricing recommendations

### Key Calculation
```
food_cost_pct = SUM(ingredient.cost_per_unit × recipe_item.quantity_needed) / menu_item.price × 100
```

### Claude's Job
Given a list of over-target items, Claude must return:
- A specific recommended price for each item
- Reasoning (e.g. "Salmon costs $8.20 to make. At $19.99, food cost is 41%. Raising to $24.99 brings it to 33%.")
- Guardrail: never suggest a price increase of more than 8% in one step

### Output Tables
- `food_cost_snapshots` — one row per menu item per night (powers the Reports trend chart)
- `pricing_recommendations` — one row per recommendation (powers the Pricing page)

---

## 6. Agent 3: Customer Success

### What It Does
Protects revenue by detecting restaurants that are disengaging from the platform before they cancel.

Daily at 08:00:
1. For each restaurant, calculates a "health score" (0-100)
2. Flags at-risk restaurants (score < 50)
3. Sends a personalised check-in email to at-risk managers with 2-3 specific data points
4. On the 1st of each month: sends a Monthly ROI Summary showing what value the platform delivered

### Health Score Factors
- Days since last order processed (proxy for POS usage)
- Week-over-week order count change (big drops = warning)
- Food cost % trend direction (worsening = warning)
- % of menu items with recipes linked (low = onboarding incomplete)

### Risk Levels
- `ok` (score ≥ 70) — no action
- `at_risk` (score 40-69) — send a helpful check-in email
- `churning` (score < 40) — send urgent email with offer to help via call

---

## 7. Agent 4: Reporting & Analytics

### What It Does
Generates automated reports so restaurant managers get value without having to log into the dashboard.

### Reports It Sends
| Report | Schedule | Recipient | Content |
|--------|---------|-----------|---------|
| Weekly Performance Summary | Monday 07:00 | Each restaurant manager | Sales, food cost %, top items, waste |
| Daily Operations Digest | Daily 07:30 | Each restaurant manager | Yesterday's sales, pending approvals, stock warnings |
| Internal Business Report | Monday 06:00 | You (the SaaS owner) | Active restaurants, agent activity, failures |

---

## 8. Agent 5: Sales Outreach (Later)

**Build this in Phase 7 — only after you have paying customers and case studies.**

Uses Apollo.io API to pull restaurant leads weekly. Claude writes personalised cold emails for each lead referencing specific details (cuisine type, location, reviews). Sends in batches of 20/day via Resend. Tracks engagement to score hot leads.

---

## 9. Agent 6: Marketing & Content (Later)

**Build this in Phase 7 — only after you have paying customers.**

Claude generates 3 SEO blog posts per week targeting keywords like "AI inventory management for restaurants". Posts are saved as drafts for your manual approval before publishing. Later: Buffer API integration for social media scheduling.

---

## 10. Database Tables — What Agents Read and Write

> The schema is defined in `src/lib/db/schema.ts` in the Next.js repo using Drizzle ORM.
> Never create or alter tables from the Python repo. All schema changes go through Drizzle.

### Tables Agents WRITE TO

| Table | Agent | What It Writes |
|-------|-------|----------------|
| `purchase_orders` | Ordering | Draft purchase orders (status='draft') |
| `purchase_order_lines` | Ordering | Line items: ingredient, qty, cost |
| `agent_logs` | All agents | Every action, with status and JSON data |
| `ingredient_depletion_rates` | Inventory | Daily usage rate per ingredient |
| `food_cost_snapshots` | Pricing | Nightly food cost % per menu item |
| `pricing_recommendations` | Pricing | Price suggestions with reasoning |

### Tables Agents READ FROM

| Table | Purpose |
|-------|---------|
| `restaurants` | Get all active restaurants to loop over |
| `ingredients` | Current stock, reorder_point, par_level, cost, supplier_id |
| `suppliers` | Supplier name, email, lead_time_days |
| `inventory_transactions` | Calculate daily usage from type='sale' entries |
| `waste_records` | Detect anomalies; check this week vs historical average |
| `menu_items` | Current selling prices for food cost calculation |
| `recipes` + `recipe_items` | Map menu items to ingredients (for food cost calc) |
| `users` | Manager emails for notifications |
| `restaurant_settings` | Target food cost %, tax rate, email preferences |
| `purchase_orders` | Check if a draft for this supplier already exists today |

### Key Table: agent_logs

Every agent action MUST write a row here. This is what the manager sees in the Agents dashboard.

```
agent_logs columns:
  id                UUID
  restaurant_id     UUID
  agent_name        TEXT  -- e.g. "inventory_agent", "pricing_agent"
  action_type       TEXT  -- e.g. "draft_purchase_order", "price_recommendation", "waste_alert"
  summary           TEXT  -- human-readable: "Drafted 2 orders totalling $340 for Demo Bistro"
  data              JSONB -- full structured data (the drafted orders, the recommendations, etc.)
  status            TEXT  -- "completed" | "pending_approval" | "failed" | "dismissed"
  requires_approval BOOLEAN -- true if manager needs to act on this
  approved_by       UUID  -- set by the dashboard when manager approves
  approved_at       TIMESTAMPTZ
  created_at        TIMESTAMPTZ
```

---

## 11. File Structure

```
restaurant-os-agents/
│
├── main.py                         ← Entry point. Railway runs: python main.py
│                                     Contains: health check server + APScheduler setup
│
├── requirements.txt                ← All Python dependencies
├── Procfile                        ← Railway command: worker: python main.py
├── .env                            ← API keys — NEVER commit this file
├── .env.example                    ← Template showing which vars are needed
├── .gitignore                      ← Ignores .env, __pycache__, .pytest_cache
│
├── agents/
│   ├── __init__.py
│   ├── inventory.py                ← Checks stock levels; detects waste anomalies
│   ├── ordering.py                 ← Calls Claude; drafts + saves purchase orders
│   ├── pricing.py                  ← Saves food cost snapshots; generates price recs
│   ├── customer_success.py         ← Monitors engagement; sends check-in emails
│   ├── reporting.py                ← Generates weekly/daily summaries
│   ├── sales.py                    ← (Phase 7) Apollo.io leads + cold email
│   └── marketing.py                ← (Phase 7) Claude blog generation
│
├── tools/
│   ├── __init__.py
│   ├── database.py                 ← All async DB query functions (asyncpg)
│   ├── order_calculator.py         ← Smart quantity formula (pure Python, no DB)
│   └── email_sender.py             ← HTML email templates + Resend API calls
│
├── prompts/
│   ├── ordering_system.txt         ← Claude's system prompt for drafting purchase orders
│   └── pricing_system.txt          ← Claude's system prompt for pricing recommendations
│
└── tests/
    ├── test_db.py                  ← Tests for each database.py function
    ├── test_calc.py                ← Unit tests for order_calculator.py
    └── test_agents.py              ← Integration test: full inventory check → draft cycle
```

---

## 12. Tech Stack & Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `asyncpg` | latest | Fast async PostgreSQL driver for Neon DB |
| `anthropic` | latest | Claude API client (Anthropic SDK) |
| `apscheduler` | 3.x | Job scheduler — runs agents on a timer |
| `resend` | latest | Email sending API |
| `python-dotenv` | latest | Loads variables from `.env` file |
| `sentry-sdk` | latest | Error tracking and crash alerts |

**Python version:** 3.11+ (Railway supports this by default)

**requirements.txt example:**
```
asyncpg==0.29.0
anthropic>=0.40.0
apscheduler==3.10.4
resend==2.0.0
python-dotenv==1.0.0
sentry-sdk==2.0.0
pytest==8.0.0
pytest-asyncio==0.23.0
```

---

## 13. Environment Variables

Create a `.env` file locally (never commit it). Add these same variables in the Railway dashboard under "Variables".

| Variable | Example Value | Purpose |
|----------|--------------|---------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Claude API — the AI brain |
| `DATABASE_URL` | `postgresql://...` | Neon connection string (same as POS app) |
| `RESEND_API_KEY` | `re_...` | Email sending via Resend |
| `FROM_EMAIL` | `alerts@restaurantos.ai` | The "from" address for all agent emails |
| `APP_URL` | `https://app.restaurantos.com` | Dashboard URL (used in email links) |
| `SENTRY_DSN` | `https://...@sentry.io/...` | Error tracking (get from sentry.io) |
| `ENVIRONMENT` | `production` or `development` | Controls log verbosity |

**Getting the DATABASE_URL:** It is the same Neon connection string used in the Next.js `.env.local`. Use the **pooled** connection URL (ends with `-pooler.neon.tech`) for Railway.

---

## 14. Tools Reference (tools/)

### tools/database.py — All Async DB Functions

```python
# Returns a list of ingredients below their reorder_point for a given restaurant
async def get_low_stock_ingredients(pool, restaurant_id: str) -> list[dict]

# Returns all active restaurant rows (id, name, contact email, settings)
async def get_all_restaurants(pool) -> list[dict]

# Returns the saved daily usage rate for an ingredient (or None if never calculated)
async def get_depletion_rate(pool, ingredient_id: str) -> float | None

# Saves a depletion rate (upsert — update if exists, insert if not)
async def update_depletion_rate(pool, ingredient_id: str, daily_usage: float, days_analysed: int)

# Calculates the real daily usage from inventory_transactions (type='sale')
async def calculate_depletion_from_sales(pool, ingredient_id: str, days: int) -> float

# Creates a draft purchase_order with all its lines in one transaction
async def save_purchase_order(pool, restaurant_id: str, supplier_id: str, lines: list[dict]) -> str  # returns PO id

# Writes a row to agent_logs
async def log_agent_action(pool, restaurant_id: str, agent_name: str, action_type: str,
                            summary: str, data: dict, status: str = 'completed') -> str

# Returns a full ingredient row by ID
async def get_ingredient_by_id(pool, ingredient_id: str) -> dict

# Returns the manager's email for a restaurant (from users table, role='manager' or 'owner')
async def get_manager_email(pool, restaurant_id: str) -> str | None
```

### tools/order_calculator.py — Quantity Formula

```python
def calculate_order_quantity(
    current_stock: float,       # how much is in stock right now
    reorder_point: float,       # the trigger threshold
    par_level: float,           # the "full" level to aim for
    daily_usage: float,         # average units used per day
    lead_time_days: int         # how many days until delivery arrives
) -> dict:
    # Returns: { recommended_qty, days_of_coverage, reasoning }
```

### tools/email_sender.py — Email Templates

```python
# Sends an email listing low stock items with an "Approve Orders" button link
async def send_low_stock_alert(to_email: str, restaurant_name: str,
                                items: list[dict], dashboard_url: str)

# Sends a weekly performance summary email
async def send_weekly_report(to_email: str, restaurant_name: str,
                              report_data: dict, dashboard_url: str)

# Sends an urgent alert for critical issues (stockout imminent, waste spike)
async def send_urgent_alert(to_email: str, restaurant_name: str,
                             subject: str, message: str, dashboard_url: str)

# Sends the monthly ROI summary (1st of each month)
async def send_monthly_roi_summary(to_email: str, restaurant_name: str,
                                    roi_data: dict, dashboard_url: str)
```

---

## 15. How Claude API Is Used

### Model Choice
- **Start with:** `claude-haiku-4-5-20251001` (cheapest, fast, handles structured data well)
- **Upgrade to:** `claude-sonnet-4-6` if output quality is insufficient
- Never use Opus for routine agent tasks — too expensive for this use case

### API Call Pattern
```python
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    system=open("prompts/ordering_system.txt").read(),
    messages=[
        {
            "role": "user",
            "content": f"Here is the low stock data for {restaurant_name}: {json.dumps(low_stock_data)}"
        }
    ]
)

raw_text = response.content[0].text
parsed = json.loads(raw_text)  # prompts instruct Claude to return JSON only
```

### Cost Reference (per Claude call)
| Model | Input 1K tokens | Output 1K tokens | Est. per call |
|-------|----------------|-----------------|--------------|
| Haiku 4.5 | $0.001 | $0.005 | ~$0.004 |
| Sonnet 4.6 | $0.003 | $0.015 | ~$0.012 |

A restaurant with 5 low-stock items triggers ~90 Claude calls/month = **~$0.36/month at Haiku pricing**.

### Prompt Rules
- Always instruct Claude to return **valid JSON only** — no markdown, no explanation, no code fences
- Always define the exact JSON schema in the prompt
- Keep prompts under 1,000 tokens to stay cost-efficient
- Include "If you are unsure, return an empty array — never guess" in every prompt

---

## 16. Scheduling — How Jobs Run

APScheduler runs all jobs. It is started in `main.py` on app startup.

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()

# Every 15 minutes — inventory check
scheduler.add_job(inventory_and_ordering_job, CronTrigger(minute='*/15'))

# Nightly 02:00 — food cost snapshots
scheduler.add_job(pricing_snapshot_job, CronTrigger(hour=2, minute=0))

# Nightly 02:30 — pricing recommendations
scheduler.add_job(pricing_recommendations_job, CronTrigger(hour=2, minute=30))

# Daily 07:30 — daily digest
scheduler.add_job(daily_digest_job, CronTrigger(hour=7, minute=30))

# Daily 08:00 — customer success checks
scheduler.add_job(customer_success_job, CronTrigger(hour=8, minute=0))

# Monday 06:00 — internal business report
scheduler.add_job(internal_report_job, CronTrigger(day_of_week='mon', hour=6, minute=0))

# Monday 07:00 — weekly client summaries
scheduler.add_job(weekly_summary_job, CronTrigger(day_of_week='mon', hour=7, minute=0))

scheduler.start()
```

**Important:** Railway uses UTC time. Add the correct UTC offset if your restaurants are in a different timezone (UAE = UTC+4, so "07:30 UAE time" = "03:30 UTC").

---

## 17. Health Check Endpoint

Railway needs a way to verify the process is alive. This simple HTTP server answers pings:

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'RestaurantOS Agents running OK')

    def log_message(self, *args):
        pass  # silence access logs

def start_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    print("Health check server started on port 8080")
```

Call `start_health_server()` at the top of `main.py` before starting the scheduler.

UptimeRobot (free) will ping this endpoint every 5 minutes. If it goes down, it emails you.

---

## 18. Deploying to Railway

### First Deployment
1. Push your code to a new GitHub repo: `restaurant-os-agents`
2. Log in to railway.app
3. Click "New Project" → "Deploy from GitHub repo"
4. Select `restaurant-os-agents`
5. Railway auto-detects Python and runs `pip install -r requirements.txt`
6. The `Procfile` tells Railway how to start: `worker: python main.py`
7. Go to the "Variables" tab in Railway and add all environment variables from section 13
8. Railway will auto-deploy. Check the logs for "Agents started" and "Scheduler running"

### Procfile
```
worker: python main.py
```
Note: `worker` (not `web`) tells Railway this is a background process, not a web server.

### Redeploy After Changes
Just push to GitHub main branch. Railway auto-detects the push and redeploys within 30 seconds.

### Checking Logs
Railway dashboard → your project → "Deployments" tab → click latest deployment → "Logs".
You will see each scheduler tick and agent run in real time.

---

## 19. Testing Locally

### Setup
```bash
# Clone the repo
git clone https://github.com/your-username/restaurant-os-agents
cd restaurant-os-agents

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Fill in your real values in .env
```

### Running the Test Suite
```bash
pytest tests/ -v
```

### Testing a Single Agent Run
```python
# In a test script or Python REPL:
import asyncio
from tools.database import create_pool
from agents.inventory import run_inventory_check

async def test():
    pool = await create_pool()
    # Use the Demo Bistro restaurant_id from the seed data
    result = await run_inventory_check(pool, "your-demo-bistro-uuid")
    print(result)

asyncio.run(test())
```

### Testing Email Sending
Always test email with your own address first:
```python
import asyncio
from tools.email_sender import send_urgent_alert

async def test():
    await send_urgent_alert(
        to_email="your@email.com",
        restaurant_name="Demo Bistro",
        subject="Test Alert",
        message="This is a test from the agents system.",
        dashboard_url="http://localhost:3000/dashboard"
    )

asyncio.run(test())
```

---

## 20. Rules & Guardrails

These rules are non-negotiable. Breaking them can harm real restaurant businesses.

### Always
- Log every action to `agent_logs` — if it's not logged, it didn't happen
- Handle exceptions per restaurant (wrap each restaurant's work in try/except so one failing restaurant never stops the others)
- Return clean JSON from Claude prompts — if parsing fails, log the failure and skip (never crash)
- Use `GREATEST(stock - deducted, 0)` when updating stock to avoid negative numbers
- Check if a draft PO for this supplier already exists today before creating a new one (avoid duplicates)

### Never
- Modify the database schema (no CREATE TABLE, ALTER TABLE, DROP TABLE)
- Delete rows from any table
- Access or modify authentication data (users table passwords, sessions)
- Send emails to users who have email notifications disabled in their settings
- Call Claude API more than necessary — cache results within a run
- Hard-code restaurant IDs, emails, or credentials anywhere in the code
- Commit the `.env` file to GitHub

### Agent Mode Guardrails
- Default mode: **recommend only** — agents suggest, humans approve
- Autonomous mode (Phase 8): only after 20+ consecutive correct recommendations for a given restaurant
- Even in autonomous mode: max order value caps apply (defined in restaurant settings)
- Even in autonomous mode: every autonomous action must be logged and an email sent to the manager

---

*This document is the source of truth for the agents project. Update it whenever the architecture changes.*
