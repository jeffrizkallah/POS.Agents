# Agent Builder Guide

## What This Project Is

This is a **Python background worker system** deployed on Railway.app that provides AI-powered business operations automation. It runs 24/7 and communicates with a client-facing application (Next.js POS) exclusively through a shared **Neon PostgreSQL database** — agents never call the frontend directly, and the frontend never calls agents directly.

### The Core Business Model

We build autonomous AI agents and deploy them as a managed service. When onboarding a new company:
1. Their database schema is connected to the Neon PostgreSQL instance (or a separate pool pointing to their DB)
2. The agents pick up their data automatically via `restaurant_id` (or equivalent tenant identifier)
3. Agents run on a schedule, analyze their data, and take actions (drafting orders, sending emails, generating reports)
4. Staff interact with agent outputs through their own POS/dashboard — they approve or reject recommendations

**The agents are the product.** The goal is that a business owner wakes up each morning to automated decisions already made, reports already sent, and risks already flagged — without touching a dashboard.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Scheduling | APScheduler (BackgroundScheduler + CronTrigger) |
| Database | asyncpg (Neon PostgreSQL) |
| AI | Anthropic SDK (Claude Haiku 4.5 for high-frequency tasks, Sonnet for quality tasks) |
| Email | Resend API |
| Hosting | Railway.app (24/7 worker process) |
| Testing | pytest + pytest-asyncio (real DB, no mocks) |

---

## Project Structure

```
agents/           # One file per agent — the "brain"
tools/            # Shared utilities (DB queries, email, math, metrics)
  metrics/        # One file per metric domain (revenue, food_cost, etc.)
prompts/          # Claude system prompts (.txt files, loaded at runtime)
tests/            # Integration tests (hit real database)
docs/             # Specs, guides, progress tracker
main.py           # Entry point: scheduler + health check + job registration
requirements.txt  # 8 dependencies
Procfile          # Railway start command: "worker: python main.py"
.env.example      # All required environment variables
```

---

## How the System Works

### Startup (`main.py`)

1. HTTP health server starts on port 8080 (Railway ping endpoint)
2. `asyncpg` connection pool is created (min=2, max=10)
3. All restaurants are fetched from DB (logged for visibility)
4. APScheduler registers all jobs with their cron schedules
5. A `while True: time.sleep(60)` loop keeps the process alive

### The Event Loop Pattern

**Critical:** A single event loop is created at module level and reused for all jobs:

```python
_loop = asyncio.new_event_loop()

def _run(coro):
    return _loop.run_until_complete(coro)
```

This prevents asyncpg pool loop mismatch errors. `asyncio.run()` creates a new loop each call — do not use it.

### Job Pattern

Every agent follows this two-function pattern:

```python
# Synchronous wrapper — called by APScheduler
def my_agent_job():
    try:
        _run(_async_my_agent_job())
    except Exception as e:
        print(f"[Scheduler Error] my_agent_job: {e}")

# Async implementation — does the real work
async def _async_my_agent_job():
    restaurants = await get_all_restaurants(pool)
    for r in restaurants:
        restaurant_id = r["id"]
        restaurant_name = r["name"]
        try:
            await run_my_agent(pool, restaurant_id, restaurant_name)
        except Exception as e:
            print(f"[MyAgent] {restaurant_name}: {e}")
            # Per-restaurant isolation: one failure never stops others
```

---

## Existing Agents

| Agent | File | Schedule | Claude Model | Purpose |
|-------|------|----------|-------------|---------|
| Inventory Scanner | `agents/inventory.py` | Every 15 min | None | Detects low-stock items, calculates depletion rates |
| Ordering | `agents/ordering.py` | Every 15 min (after inventory) | Haiku 4.5 | Drafts purchase orders for low-stock items |
| Pricing | `agents/pricing.py` | 02:00 + 02:30 daily | Haiku 4.5 | Food cost snapshots + price recommendations |
| Customer Success | `agents/customer_success.py` | 08:00 daily + 1st of month | None | Health scoring + proactive outreach emails |
| Reporting | `agents/reporting.py` | Monday 06:00 UTC | Sonnet | 40+ metrics, anomaly detection, weekly reports |

---

## How to Build a New Agent

### Step 1 — Define the Agent Spec

Before writing code, answer these questions:

- **What trigger causes this agent to act?** (schedule, event, approval)
- **What data does it read?** (which DB tables)
- **What decision does it make?** (draft, flag, send, update)
- **Does it call Claude?** If yes, which model and why
- **What does it write back?** (which DB tables, which emails)
- **What guardrails prevent runaway actions?** (duplicate guards, caps, approval gates)

Save your spec in `docs/AGENTS/AGENT_YOURNAME.md` before building.

---

### Step 2 — Create the Agent File

Create `agents/your_agent.py`. The standard structure:

```python
import json
import asyncio
import anthropic
import asyncpg

# Import shared tools
from tools.database import (
    get_all_restaurants,
    log_agent_action,
    # ... whatever DB functions you need
)
from tools.email_sender import send_your_email_type

# Claude model constants
MODEL = "claude-haiku-4-5-20251001"   # use for high-frequency agents
# MODEL = "claude-sonnet-4-6"         # use for weekly/quality agents

# ─── Claude call (sync + async wrapper) ───────────────────────────────────────

def _call_claude_sync(payload: dict) -> dict:
    """Sync Claude call — runs in thread so it doesn't block the event loop."""
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    with open("prompts/your_agent_system.txt") as f:
        system_prompt = f.read()

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(payload)}]
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences (Claude sometimes wraps in ```json ... ``` despite instructions)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)

async def _call_claude(payload: dict) -> dict:
    """Async wrapper — bridges sync Anthropic SDK to async event loop."""
    return await asyncio.to_thread(_call_claude_sync, payload)

# ─── Core agent logic ─────────────────────────────────────────────────────────

async def run_your_agent(pool: asyncpg.Pool, restaurant_id: int, restaurant_name: str):
    """Main entry point for this agent. Called once per restaurant per job run."""
    try:
        # 1. Fetch data
        data = await get_your_data(pool, restaurant_id)

        if not data:
            print(f"[YourAgent] {restaurant_name}: nothing to process")
            return

        # 2. Duplicate guard (if applicable)
        # existing = await check_if_already_ran_today(pool, restaurant_id)
        # if existing:
        #     return

        # 3. Decision logic (pure math or Claude)
        result = await _call_claude({"restaurant": restaurant_name, "data": data})

        # 4. Write results back to DB
        await save_your_result(pool, restaurant_id, result)

        # 5. Email notification (if applicable)
        manager_email = await get_manager_email(pool, restaurant_id)
        if manager_email:
            await send_your_email_type(manager_email, restaurant_name, result)

        # 6. Log the action (always)
        await log_agent_action(
            pool, restaurant_id,
            agent_name="your_agent",
            action_type="your_action",
            summary=f"Processed {len(data)} items",
            data={"count": len(data)},
            status="completed"
        )

    except Exception as e:
        print(f"[YourAgent] {restaurant_name}: {e}")
        await log_agent_action(
            pool, restaurant_id,
            agent_name="your_agent",
            action_type="your_action",
            summary=str(e),
            data={},
            status="failed"
        )
```

---

### Step 3 — Write the Claude Prompt

If your agent calls Claude, create `prompts/your_agent_system.txt`.

**Mandatory rules for all Claude prompts:**
- First line defines the role: `You are a [role] for [context].`
- Explicitly state: `Respond with JSON only. No markdown. No explanation outside the JSON.`
- Define the exact input schema Claude will receive
- Define the exact output schema Claude must return (with field names and types)
- Include guardrails in the prompt (max %, no decreases, etc.)
- State what to do with missing/uncertain data

**Example prompt structure:**
```
You are a [professional role] for a restaurant management platform.

Your job: [one sentence]

Input format:
{
  "restaurant_name": "string",
  "items": [{ "id": int, "field": value, ... }]
}

Output format (JSON only, no markdown):
{
  "results": [
    {
      "item_id": int,
      "recommendation": "string",
      "reasoning": "string (1-2 sentences, cite specific numbers)"
    }
  ]
}

Rules:
- [guardrail 1]
- [guardrail 2]
- Never hallucinate data. Only use what is provided.
- If data is insufficient, use conservative defaults.
```

---

### Step 4 — Add Database Functions

Add new query functions to `tools/database.py`. Follow the existing pattern:

```python
async def get_your_data(pool: asyncpg.Pool, restaurant_id: int) -> list[dict]:
    """Fetch [description] for a restaurant."""
    try:
        rows = await pool.fetch("""
            SELECT column1, column2
            FROM your_table
            WHERE restaurant_id = $1
              AND some_condition = true
        """, restaurant_id)
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB] get_your_data: {e}")
        raise

async def save_your_result(pool: asyncpg.Pool, restaurant_id: int, data: dict) -> None:
    """Save [description] for a restaurant."""
    try:
        await pool.execute("""
            INSERT INTO your_table (restaurant_id, field1, field2, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (restaurant_id, unique_key) DO UPDATE
              SET field1 = EXCLUDED.field1,
                  updated_at = NOW()
        """, restaurant_id, data["field1"], data["field2"])
    except Exception as e:
        print(f"[DB] save_your_result: {e}")
        raise
```

**Rules for DB functions:**
- Always use parameterized queries (`$1`, `$2` — never f-strings in SQL)
- Always wrap in try/except; print the error; re-raise so callers can catch
- Use `COALESCE` for nullable columns
- Use `ON CONFLICT DO NOTHING` or `DO UPDATE` for idempotent writes
- Return `list[dict]` (from `fetchrow`→`dict(row)` or `fetch`→`[dict(r) for r in rows]`)

---

### Step 5 — Add Email Templates (if needed)

If your agent sends emails, add a function to `tools/email_sender.py`:

```python
async def send_your_email(
    to_email: str,
    restaurant_name: str,
    data: dict
) -> None:
    """Send [description] email."""
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #4f46e5; color: white; padding: 24px; border-radius: 8px 8px 0 0;">
        <h1 style="margin: 0; font-size: 20px;">{restaurant_name} — Your Subject</h1>
      </div>
      <div style="padding: 24px; background: #f9fafb; border-radius: 0 0 8px 8px;">
        <!-- content -->
      </div>
    </div>
    """
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": os.getenv("FROM_EMAIL"),
            "to": [to_email],
            "subject": f"{restaurant_name} — Your Subject",
            "html": html
        })
    except Exception as e:
        print(f"[Email] send_your_email: {e}")
        # Don't raise — email failure should never crash an agent
```

**Rules for emails:**
- Always use `asyncio.to_thread()` (Resend SDK is synchronous)
- Catch exceptions silently — email failure must not crash the agent
- Use inline CSS only (email clients strip `<style>` tags)
- Keep the indigo (`#4f46e5`) header color for brand consistency

---

### Step 6 — Register the Job in `main.py`

```python
# Import your agent
from agents.your_agent import run_your_agent

# Add sync wrapper function
def your_agent_job():
    try:
        _run(_async_your_agent_job())
    except Exception as e:
        print(f"[Scheduler Error] your_agent_job: {e}")

async def _async_your_agent_job():
    restaurants = await get_all_restaurants(pool)
    for r in restaurants:
        try:
            await run_your_agent(pool, r["id"], r["name"])
        except Exception as e:
            print(f"[YourAgent] {r['name']}: {e}")

# Register in the scheduler block
scheduler.add_job(
    your_agent_job,
    CronTrigger(hour=3, minute=0),   # adjust schedule
    id="your_agent_job",
    name="Your Agent Job"
)
```

---

### Step 7 — Write Tests

Create `tests/test_your_agent.py`. All tests hit the real database — no mocks.

```python
import pytest
import pytest_asyncio
import asyncpg
import asyncio
from agents.your_agent import run_your_agent
from tools.database import get_your_data

TEST_RESTAURANT_ID = 1   # seed a test restaurant in your DB

@pytest.mark.asyncio
async def test_get_your_data(pool):
    result = await get_your_data(pool, TEST_RESTAURANT_ID)
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_run_your_agent_no_crash(pool):
    # Should not raise even if there's nothing to process
    await run_your_agent(pool, TEST_RESTAURANT_ID, "Test Restaurant")

@pytest.mark.asyncio
async def test_your_agent_result_shape(pool):
    result = await get_your_data(pool, TEST_RESTAURANT_ID)
    if result:
        assert "expected_field" in result[0]
```

Run with: `pytest tests/test_your_agent.py -v`

---

## Patterns & Rules Reference

### Model Selection

| Use Case | Model | Why |
|----------|-------|-----|
| Runs every 15 min or daily | `claude-haiku-4-5-20251001` | Cost: ~10× cheaper than Sonnet |
| Weekly reports, quality narratives | `claude-sonnet-4-6` | Quality: better reasoning, prose |
| Real-time / sub-second | Don't use Claude | Latency too high for sync tasks |

### Duplicate Guards

Every agent that creates records must check for existing records first:

```python
existing = await pool.fetchrow("""
    SELECT id FROM your_table
    WHERE restaurant_id = $1
      AND DATE(created_at) = CURRENT_DATE
""", restaurant_id)

if existing:
    print(f"[YourAgent] {restaurant_name}: already ran today, skipping")
    return
```

This prevents wasted Claude API calls and duplicate records.

### Per-Restaurant Isolation

Always wrap each restaurant in its own try/except inside the job loop. One restaurant's error must never stop processing for others.

### Token Budget

| Agent type | max_tokens guideline |
|------------|---------------------|
| Simple JSON output (orders, recommendations) | 1000–2000 |
| Structured analysis (pricing classification) | 2000–3000 |
| Long narrative reports | 3000–4000 |
| Never exceed | 4096 (Haiku) / 8000 (Sonnet) without justification |

### Approval Gate Pattern

When agents should not auto-execute but instead draft for human approval:

1. Agent writes a record with `status = 'draft'`
2. Human reviews in POS/dashboard and sets `status = 'approved'`
3. A polling job (every 15 min) scans for `status = 'approved'` and executes

Used by: Ordering agent (purchase orders), Pricing agent (price changes)

### Concurrent Execution Pattern

When an agent needs multiple independent data fetches, run them in parallel:

```python
results = await asyncio.gather(
    get_revenue_metrics(pool, restaurant_id, week_start, week_end),
    get_food_cost_metrics(pool, restaurant_id, week_start, week_end),
    get_inventory_metrics(pool, restaurant_id, week_start, week_end),
)
revenue, food_cost, inventory = results
```

### Agent Logging

Every agent run must write to `agent_logs` on both success and failure:

```python
await log_agent_action(
    pool,
    restaurant_id=restaurant_id,
    agent_name="your_agent",       # snake_case, matches file name
    action_type="your_action",     # verb_noun describing what happened
    summary="Human-readable result",
    data={"key": "value"},         # any JSON-serializable dict
    status="completed"             # or "failed"
)
```

---

## Connecting a New Client (Company)

When onboarding a company to use these agents:

1. **Database:** Point the agent pool at their DB (or add their schema to the shared Neon instance). Ensure their tables match the expected schema (`menu_items`, `orders`, `ingredients`, etc.)
2. **Tenant ID:** Add their entry to the `restaurants` table (or equivalent). The `get_all_restaurants()` function is the only place that needs to change — all agent loops are already multi-tenant.
3. **Email:** Add their manager's email to `users` or equivalent. Agents pull this at runtime via `get_manager_email(pool, restaurant_id)`.
4. **Environment:** No code changes needed. Agents are data-driven — they pick up new tenants automatically on next job run.
5. **Schema differences:** If their DB has different column names, add a mapping layer in `tools/database.py` specific to their queries. Never break existing restaurant queries.

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | Yes | Neon PostgreSQL connection string (pooler endpoint) |
| `ANTHROPIC_API_KEY` | Yes | Claude API access |
| `RESEND_API_KEY` | Yes | Email sending |
| `FROM_EMAIL` | Yes | Sender address for all outbound emails |
| `APP_URL` | Yes | Dashboard URL embedded in email CTAs |
| `PLATFORM_REPORT_EMAIL` | Yes | Recipient of internal weekly platform briefing |
| `ENVIRONMENT` | No | `development` or `production` — used in log labels |
| `SENTRY_DSN` | No | Error tracking (optional, dependency installed) |

---

## Deployment Checklist for a New Agent

- [ ] Spec written in `docs/AGENTS/AGENT_YOURNAME.md`
- [ ] `agents/your_agent.py` created with standard pattern
- [ ] `prompts/your_agent_system.txt` written (if Claude is used)
- [ ] DB functions added to `tools/database.py`
- [ ] Email function added to `tools/email_sender.py` (if emails sent)
- [ ] Job registered in `main.py` (sync wrapper + async impl + `scheduler.add_job`)
- [ ] Tests written in `tests/test_your_agent.py`
- [ ] All tests pass: `pytest -v`
- [ ] `docs/PROGRESS.md` updated with new phase/chunk
- [ ] Pushed to `main` → Railway auto-deploys
