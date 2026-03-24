# Internal Platform — Build Spec

> The Internal Platform is a **separate Next.js project** (new repo). It is your control hub: the single place where you manage every company you work with, configure which agents run for them, and monitor everything those agents are doing.
>
> It does **not** run agents. It manages the config that agents read, and reads the data that agents write.

---

## What It Is (Plain English)

Right now, if you want to onboard a new company to your agents, you'd have to manually edit code, add environment variables, and redeploy. That does not scale. The Internal Platform solves this: you open a dashboard, add a new company, paste their database URL, choose which agents to enable, and hit Save. The agents pick that company up on their next scheduled run — no code changes, no redeployment.

It also gives you visibility. Instead of connecting to Neon manually to check if an agent ran successfully, you open the platform and see a live view of every agent, every company, last run time, errors, and health scores.

---

## The Two Things It Manages

### 1. The Platform DB (Source of Truth)
A dedicated Neon PostgreSQL database that belongs to the Internal Platform — completely separate from any client's database. It stores:

- **The clients table** — every company you serve, with their DB connection string, enabled agents, and settings
- **Subscriptions** — billing status, MRR, plan type per client
- **Team members** — who can log into the platform

The agents repo reads from this Platform DB at startup to get the full client list. This is the bridge.

### 2. Each Client's DB (Read-Only for the Platform)
Every client (RestaurantOS, Boxed and Go, etc.) has their own database. The agents write to it. The Internal Platform connects to it read-only, purely for monitoring — to read `agent_logs`, `client_health_scores`, `weekly_report_snapshots`, etc.

---

## How the Agents Connect to It

This is the critical section. Here is exactly how the two systems communicate.

### The Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Internal Platform (Vercel)                                 │
│                                                             │
│  You add a client here. Writes to Platform DB.             │
│  You monitor agents here. Reads from each client's DB.     │
└───────────────────────────┬─────────────────────────────────┘
                            │ reads/writes
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Platform DB (Neon — new, separate DB)                      │
│                                                             │
│  clients table:                                             │
│  ├── id                                                     │
│  ├── name          "Boxed and Go"                          │
│  ├── db_url        "postgresql://neon.tech/boxedandgo"     │
│  ├── enabled_agents  ["inventory","ordering","pricing"]    │
│  ├── settings      { target_food_cost_pct: 32, ... }      │
│  └── is_active     true                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │ reads at startup
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  POS.Agents repo (Railway)                                  │
│                                                             │
│  main.py:                                                   │
│  1. Connect to Platform DB                                  │
│  2. SELECT * FROM clients WHERE is_active = true           │
│  3. For each client:                                        │
│     a. Connect to client.db_url                            │
│     b. Run client.enabled_agents                           │
│     c. Write agent_logs → client's own DB                  │
│     d. Write health scores → client's own DB               │
└───────────────────────────┬─────────────────────────────────┘
                            │ agents write logs here
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Each Client's DB (Neon — one per client)                   │
│                                                             │
│  agent_logs, client_health_scores,                          │
│  weekly_report_snapshots, purchase_orders, etc.            │
│                                                             │
│  ← Internal Platform reads these for monitoring (read-only)│
└─────────────────────────────────────────────────────────────┘
```

### What Changes in the Agents Repo (Phase 3 below)

One new environment variable is added to the agents repo:

```
PLATFORM_DB_URL=postgresql://... (the new Platform DB)
```

One function replaces `get_all_restaurants()` in `tools/database.py`:

```python
async def get_all_clients(platform_pool):
    # Connects to Platform DB, returns all active clients
    # Each client row includes: id, name, db_url, enabled_agents, settings
    rows = await platform_pool.fetch("SELECT * FROM clients WHERE is_active = true")
    return rows
```

`main.py` changes from:

```python
restaurants = await get_all_restaurants()  # one hardcoded DB
for r in restaurants:
    await run_inventory_check(r.id)
```

To:

```python
clients = await get_all_clients(platform_pool)  # dynamic, from Platform DB
for client in clients:
    client_pool = await create_pool(client.db_url)
    if "inventory" in client.enabled_agents:
        await run_inventory_check(client, client_pool)
    if "ordering" in client.enabled_agents:
        await run_ordering_agent(client, client_pool)
    # etc.
```

That is the entire connection. One extra DB connection at startup, one loop change. Every other agent file stays exactly the same — they just receive a `client` object and a `client_pool` instead of a raw `restaurant_id`.

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Framework | Next.js (App Router) | Same stack as RestaurantOS — you already know it |
| Database | Neon PostgreSQL (new DB) | Consistent with the rest of the stack |
| ORM | Prisma | Type-safe, great with Next.js |
| Auth | NextAuth.js | Internal only — simple credentials or Google OAuth |
| Hosting | Vercel | Free tier, instant deploys, same as RestaurantOS |
| Styling | Tailwind + shadcn/ui | Fast to build clean internal tooling |

---

## Phase 1: Foundation

> New repo, Platform DB, auth, skeleton layout. Nothing functional yet — just the shell.

- [ ] **1A — New Repo + Project Setup**
  - Create new GitHub repo: `pos-internal-platform` (or similar)
  - `npx create-next-app@latest` with TypeScript + Tailwind + App Router
  - Install: `prisma`, `@prisma/client`, `next-auth`, `@auth/prisma-adapter`, `shadcn/ui`
  - Create `.env.example` with: `DATABASE_URL`, `NEXTAUTH_SECRET`, `NEXTAUTH_URL`
  - Deploy skeleton to Vercel immediately — verify it runs

- [ ] **1B — Platform DB Schema**
  - Create a new Neon database called `platform-db` (separate from any client DB)
  - Write Prisma schema with 3 tables:
    - `Client`: id, name, db_url (encrypted), product_type, enabled_agents (String[]), settings (Json), is_active, created_at
    - `Subscription`: id, client_id (FK), plan, status (active/trialing/cancelled), mrr, billing_cycle_start
    - `TeamMember`: id, email, name, role (admin/viewer), created_at
  - Run `prisma migrate dev` to apply
  - Seed one row: your own RestaurantOS as the first client

- [ ] **1C — Auth**
  - Set up NextAuth.js with credentials provider (email + password)
  - Only team members in the `TeamMember` table can log in
  - Add middleware to protect all `/dashboard/*` routes
  - Test: verify login works, verify unauthenticated users get redirected

- [ ] **1D — Sidebar Layout**
  - Create the main layout: collapsible left sidebar + top bar
  - Sidebar links: Companies, Agents, Health, Billing, Settings
  - All pages placeholder ("Coming soon") for now
  - This is the shell every future phase builds inside

---

## Phase 2: Client Management

> The core feature. Add, configure, and manage every company the agents serve.

- [ ] **2A — Companies List Page** (`/dashboard/companies`)
  - Table: company name, product type, active agents count, status (active/inactive), date added
  - "Add Company" button opens a slide-over form
  - Data comes from Prisma query on the `Client` table

- [ ] **2B — Add / Edit Company Form**
  - Fields: Name, DB URL (masked after save), Enabled Agents (multi-select checkboxes), Settings (JSON editor for things like target_food_cost_pct, manager_email)
  - "Test Connection" button: server action that tries `asyncpg.connect(db_url)` via a small Python microservice OR a Neon connection test — confirms the DB URL is valid before saving
  - Save writes to `Client` table in Platform DB
  - This is the moment a new company becomes visible to the agents

- [ ] **2C — Company Detail Page** (`/dashboard/companies/[id]`)
  - All config for that company
  - Toggle active/inactive (agents stop running for inactive clients immediately on next cycle)
  - Edit settings inline
  - Delete company (with confirmation — removes from clients table, agents stop immediately)

---

## Phase 3: Connect Agents to Platform DB

> This is where the POS.Agents repo gets updated to read from the Platform DB instead of a single hardcoded DB. This phase happens in the **agents repo**, not the platform.

- [ ] **3A — Platform DB Connection in Agents Repo**
  - Add `PLATFORM_DB_URL` to `.env` and Railway environment variables
  - Add `create_platform_pool()` to `tools/database.py` — separate connection pool for Platform DB
  - Add `get_all_clients(platform_pool)` function: `SELECT * FROM clients WHERE is_active = true`
  - Test: print all clients at startup, confirm RestaurantOS appears

- [ ] **3B — Refactor main.py Scheduler Loop**
  - Replace `get_all_restaurants()` with `get_all_clients(platform_pool)`
  - Update `_run_restaurant()` → `_run_client(client)`:
    - Opens a per-client connection pool using `client.db_url`
    - Checks `client.enabled_agents` before calling each agent
    - Passes `client` object (with settings) down to each agent function
    - Closes per-client pool when done
  - Per-client try/except isolation stays exactly as is

- [ ] **3C — Update Agent Function Signatures**
  - Every agent function currently takes `restaurant_id`
  - Update to take `client` (the full config row) and `pool` (the per-client connection)
  - Inside agents, replace hardcoded column names with `client.settings.get("items_table", "ingredients")` — this is how schema differences between companies are handled without restructuring
  - All 49 existing tests must still pass after this refactor

---

## Phase 4: Agent Monitoring

> The reason the platform exists. Live visibility into every agent run across every company.

- [ ] **4A — Agents Overview Page** (`/dashboard/agents`)
  - Table: for each client × each agent combination:
    - Last run time
    - Status of last run (completed / error / skipped)
    - Run count this week
    - Last error message (if any)
  - Data source: Platform queries `agent_logs` from each client's DB using the stored `db_url`
  - This is a fan-out read — platform connects to each client's DB and pulls the latest logs

- [ ] **4B — Per-Client Agent Log Page** (`/dashboard/companies/[id]/logs`)
  - Full scrollable log of every `agent_logs` entry for this company
  - Filter by agent name, status, date range
  - Shows: timestamp, agent name, action type, summary, status

- [ ] **4C — Error Alerting**
  - If any agent logs an error status, platform sends an email to the team within 15 minutes
  - Platform polls `agent_logs` across all client DBs every 15 minutes (a cron job on Vercel)
  - Uses Resend (same as agents) to send the alert

---

## Phase 5: Health & Analytics

> Surface the intelligence the agents are already generating.

- [ ] **5A — Health Scores Page** (`/dashboard/health`)
  - For each active client: health score (0–100), risk band (ok/at_risk/churning), last checked
  - Data source: reads `client_health_scores` table from each client's DB
  - Red/amber/green colour coding
  - Clicking a client shows which health signals triggered the score

- [ ] **5B — Platform Intelligence Page** (`/dashboard/intelligence`)
  - Weekly narrative generated by the Reporting Agent (Phase 6 of agents repo)
  - Reads `platform_weekly_summaries` from the RestaurantOS DB (and eventually merged across all client DBs)
  - Shows: MRR, avg health score, total revenue across all clients, anomalies detected, top performer, most at risk

- [ ] **5C — Per-Client Analytics Snapshot**
  - On the company detail page: embed the latest `weekly_report_snapshots` row for that client
  - Revenue, food cost %, waste rate, agent run count for the last 7 days
  - Read directly from client's DB

---

## Phase 6: Billing & MRR

> Track the business side of every client relationship.

- [ ] **6A — Subscriptions Page** (`/dashboard/billing`)
  - Table: client name, plan, MRR, status, billing cycle start, months active
  - Total MRR card at top
  - MRR at risk (clients where health_score < 40) highlighted in amber
  - Data source: `Subscription` table in Platform DB

- [ ] **6B — Add / Edit Subscription**
  - Form to set plan, MRR, status per client
  - Status changes (active → cancelled) automatically flags the client as at-risk in the Health page

- [ ] **6C — MRR Chart**
  - Line chart: MRR over the last 12 months (built from subscription history)
  - Breakdown: new MRR, churned MRR, net change per month

---

## What Gets Built Where — Summary

| What | Where | Why |
|---|---|---|
| Client list (CRUD) | Internal Platform | Humans manage this through a UI |
| Agent logic | POS.Agents repo | Background worker, stays on Railway |
| Agent logs | Each client's DB | Written by agents, read by platform |
| Health scores | Each client's DB | Written by agents, read by platform |
| Billing / MRR | Platform DB | Business data, not agent data |
| Platform intelligence | Platform DB | Aggregated, not per-client |

---

## Build Order

Do not skip ahead. Each phase unlocks the next.

1. **Phase 1** — get the platform running and deployed (empty shell is fine)
2. **Phase 2** — add company management (the platform has something real in it)
3. **Phase 3** — update agents repo to read from Platform DB (agents now serve multiple clients)
4. **Phase 4** — monitoring (now you can see what agents are doing per client)
5. **Phase 5** — health and analytics (surface the intelligence already being generated)
6. **Phase 6** — billing (once you have paying clients to track)

Phases 1–3 are the critical path. Everything after that adds visibility and polish.
