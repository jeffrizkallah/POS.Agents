# Reporting & Analytics Agent

**File:** `agents/reporting.py`
**Runs:** Every Monday at 06:00 UTC

---

## What it does in plain English

The Reporting Agent is the most complex agent in the system. Every Monday morning, it computes over 40 metrics for each restaurant, has Claude write a plain-English narrative explaining what happened that week, and emails a full analytics report to each restaurant owner. It then produces a separate internal briefing for the company's own team, summarising performance across all clients.

Think of it as an automated weekly business review — the kind a consultant would charge thousands for, delivered automatically every Monday.

---

## How it works — Step by step

The agent runs in two phases every Monday.

---

### Phase 1: Per-Restaurant Analytics Reports

For every active restaurant (client), the agent:

#### Step 1: Gather all the metrics

Five metric modules run in parallel (at the same time, not one after another) using `asyncio.gather()`. This makes the whole process much faster. The five areas measured are:

**Revenue metrics**
- Total gross revenue for the week
- Number of covers (guests) served
- Average spend per cover
- Revenue change vs last week (week-over-week %)
- Revenue change vs a month ago (month-over-month %)
- Which hour of the day generated the most revenue (peak hour)
- Void rate — how often orders were cancelled or voided

**Food cost metrics**
- Average food cost % across all dishes for the week
- Whether the food cost trend is improving, stable, or deteriorating vs the prior 2 weeks
- The "top margin killer" — the dish with the highest food cost % (most expensive relative to what it sells for)
- The "top star dish" — the dish with the lowest food cost % (best margin)
- Estimated money being lost on over-priced-to-make dishes
- How much revenue the Pricing Agent has helped recover through accepted recommendations

**Inventory metrics**
- Total waste recorded (quantity and number of waste events)
- Waste rate — waste as a percentage of total ingredients used
- How many ingredients hit zero stock (stock-outs) during the week
- Average days of stock cover across all ingredients
- Average time from creating a purchase order to receiving it (PO cycle time)

**Consumption analysis** (`Opening + Purchased = Production + Closing`)
- Checks whether the inventory books balance for each ingredient
- Splits ingredients into two categories:
  - **Recipe ingredients** — consumed via kitchen production batches (`production_batch_inputs`). The formula checks that what was bought plus opening stock equals what production batches consumed plus what's left in stock.
  - **Unitary items** — sold directly without a production batch (e.g. bottled water). The formula checks that purchases plus opening stock equals units sold plus closing stock.
- Variance per ingredient: positive = over-purchased, negative = production discrepancy (recipe wrong, over-portioning, or unrecorded consumption)
- Waste is intentionally excluded so it cannot be used to explain away discrepancies
- Results sorted by absolute variance — biggest discrepancies surface first

**Menu metrics**
- The single most-ordered dish of the week
- Star-to-dog ratio — what fraction of menu items are high performers vs poor performers
- Attachment rate — how often customers add sides or drinks alongside a main

**Operations metrics**
- Table turn rate — how many times tables are filled per day on average
- How many AI recommendations the manager actually acted on (recommendation action rate)
- Total number of agent runs logged this week
- Login frequency data

#### Step 2: Compare against industry benchmarks

The agent fetches pre-loaded industry benchmarks from the database (e.g. 30% food cost, 5% waste rate, $28 average spend per cover) and compares each restaurant's actual numbers against these. This tells the owner whether they're doing better or worse than the industry average.

#### Step 3: Save a weekly snapshot to the database

All the computed metrics are saved to the `weekly_report_snapshots` table. This creates a historical record that can be trended over time and used for comparison the following week.

#### Step 4: Detect anomalies

The agent compares this week's metrics to last week's and looks for statistically significant changes worth flagging:

| Anomaly Type | Trigger |
|-------------|---------|
| Revenue drop | This week's revenue < last week's × 80% |
| Revenue spike | This week's revenue > last week's × 125% |
| Food cost spike | Food cost % up by more than 3 percentage points |
| Waste surge | Waste rate up by more than 2 percentage points |
| Stock-out spike | 3+ more ingredients hit zero stock than last week |
| New record high | Highest revenue ever recorded for this restaurant |
| Dish margin collapse | A dish's food cost % exceeds 45% |

Each anomaly is saved to the `analytics_anomalies` table and rated by severity: `info`, `warning`, or `critical`.

#### Step 5: Ask Claude to write the narrative

The agent sends the full metrics package to Claude (Sonnet model — more capable than Haiku for this task) and asks it to write a plain-English weekly report. Claude produces:

- A headline summarising the week in one sentence
- An executive summary (2–3 sentences for busy owners)
- Individual narrative sections for Revenue, Food Cost, Inventory, Menu, and Operations
- Plain-language descriptions of each anomaly with suggested actions
- A benchmark commentary comparing the restaurant to industry standards
- A single top recommendation for what to focus on next week

Claude is instructed to write in a style appropriate for a busy restaurant owner — specific, direct, using real numbers, no buzzwords.

#### Step 6: Email the report to the owner

The formatted report is emailed to the restaurant manager/owner. The email includes:
- A colour-coded header with the week dates
- The headline and executive summary
- Anomaly alert cards (red for critical, amber for warning, blue for info)
- Four metric cards (Revenue, Food Cost, Inventory, Menu) with key numbers and narrative
- A benchmark comparison section
- The top recommendation highlighted in a box

#### Step 7: Mark as sent and log

The weekly snapshot is marked as `report_sent = true` in the database. The action is logged to `agent_logs`. A 3-second pause is added between clients to avoid sending too many requests at once.

---

### Phase 2: Platform Intelligence Briefing

After all restaurant reports are sent, the agent produces an internal briefing for the company's own team.

#### What gets measured (platform-wide)

- Total active clients (restaurants on paying or trial subscriptions)
- Total MRR (monthly recurring revenue) and how much of it is "at risk" from low-health clients
- Average health score across all clients
- How clients are distributed across health bands (healthy, at-risk, critical)
- New clients signed up this week
- Clients who churned this week
- Total revenue processed across the entire platform
- Average food cost % across all restaurants
- Total number of agent runs across all clients
- Feature adoption — what % of restaurants are actively using all three key features (pricing, purchase orders, waste tracking)

#### Client league table

A ranked list of all clients by revenue for the week, including their food cost %, health score, and how often they act on AI recommendations.

#### Claude writes the internal briefing

The same data is sent to Claude with a different prompt — this one is written as a briefing for a co-founder or head of customer success. Claude produces:
- A week headline
- Commentary on MRR and at-risk revenue
- Notes on client health distribution
- Who the top performer was this week
- Who is most at risk
- Three actionable priorities for the team

This briefing is emailed to the internal `PLATFORM_REPORT_EMAIL` address (set in environment variables).

---

## Key facts

| Setting | Value |
|---------|-------|
| Schedule | Every Monday at 06:00 UTC |
| AI model (restaurant reports) | Claude Sonnet 4.6 (best quality) |
| AI model (platform briefing) | Claude Sonnet 4.6 |
| Metrics computed per restaurant | 40+ |
| Anomaly types detected | 7 |
| Failure isolation | One failing restaurant never stops others |
| Rate limiting | 3-second pause between client reports |

---

## What it does NOT do

- It does not make any decisions on behalf of the restaurant.
- It does not send reports to suppliers or external parties.
- It does not run on any day other than Monday.
- It does not crash if one restaurant's data is missing — it logs the error and moves to the next.
