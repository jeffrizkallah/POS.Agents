# Customer Success Agent

**File:** `agents/customer_success.py`
**Runs:** Daily at 08:00 (health check + check-in emails), 1st of each month at 09:00 (ROI summary)

---

## What it does in plain English

The Customer Success Agent is not about the restaurant's operations — it's about whether the restaurant is actually *using* the platform. Its job is to spot restaurants that are drifting away (not logging in, not processing orders, not engaging with recommendations) and send them a proactive, personalised check-in email before they churn.

Think of it as a silent account manager that watches for warning signs and reaches out automatically.

---

## How it works — Step by step

### Part 1: Health Check — Scoring each restaurant (daily at 08:00)

Every morning, the agent scores each restaurant on a scale of **0 to 100** across four signals. The score determines how worried we should be about that restaurant.

---

#### Signal 1: Login Recency (up to 30 points)

How recently did anyone from the restaurant log into the POS dashboard?

| Last login | Score | Flag |
|------------|-------|------|
| Within 3 days | 30 pts | None |
| 3–7 days ago | 20 pts | None |
| 7–14 days ago | 10 pts | `low_login_frequency` |
| 14+ days ago | 0 pts | `inactive_logins` |
| No data | 15 pts | None (neutral — don't penalise missing data) |

---

#### Signal 2: Order Volume Stability (up to 25 points)

Is the restaurant processing roughly as many orders as last week? A big drop in orders might mean they're struggling or stopped using the system.

| Order volume drop | Score | Flag |
|-------------------|-------|------|
| Drop ≤ 10% | 25 pts | None |
| Drop 10–20% | 15 pts | None |
| Drop > 20% | 0 pts | `order_volume_drop` |

---

#### Signal 3: Food Cost Trend (up to 25 points)

Is the restaurant's food cost percentage getting better or worse over the last two weeks? Worsening food costs might mean the pricing recommendations aren't being used.

| Trend | Score | Flag |
|-------|-------|------|
| Improving | 25 pts | None |
| Stable | 20 pts | None |
| Worsening | 5 pts | `food_cost_worsening` |

---

#### Signal 4: Recipe Coverage (up to 20 points)

Have they linked recipes to at least 50% of their menu items? Without recipes, the agent can't calculate food costs accurately. Low coverage usually means onboarding wasn't completed.

| Coverage | Score | Flag |
|----------|-------|------|
| ≥ 50% of items have recipes | 20 pts | None |
| < 50% | 0 pts | `onboarding_incomplete` |

---

#### Risk Level

The final score determines the restaurant's risk level:

| Score | Risk Level |
|-------|-----------|
| 70–100 | `ok` — no action needed |
| 40–69 | `at_risk` — send a friendly check-in |
| 0–39 | `churning` — send an urgent "we're here to help" email |

The health score and all flags are written to `agent_logs` for every restaurant, every day.

---

### Part 2: Proactive Check-in Emails

After scoring, the agent decides whether to send an email based on the risk level.

**If `ok`:** No email sent. Everything is fine.

**If `at_risk`:** A personalised check-in email is sent to the restaurant manager. The email includes 2–3 specific data points pulled from the health check — things like:
- "No logins detected in the last 9 days — your team may not be checking the dashboard regularly."
- "Order volume dropped 34% this week (42 orders vs 64 last week)."
- "Food cost % has been worsening — currently 38.2% vs 33.1% two weeks ago. Check your pricing recommendations in the dashboard."

The email is specific, not generic. It uses real numbers from that restaurant's actual data.

**If `churning`:** An urgent email is sent with the subject line "Your restaurant needs attention — we're here to help." It includes the same specific data points and a direct invitation to reply or book a call with the team.

---

### Part 3: Monthly ROI Summary (1st of each month at 09:00)

On the first of every month, every restaurant gets a summary email showing the value the platform delivered last month:

- Total orders processed through the system
- Total waste cost recorded
- Purchase orders that were approved
- Estimated staff time saved

This email is designed to remind managers of the concrete value they're getting, making it harder to justify cancelling.

---

## What it does NOT do

- It does not take any action on the restaurant's behalf — only emails.
- It does not score restaurants more than once per day.
- It does not send emails if the manager's email address is missing from the database.
- It does not trigger for restaurants with an `ok` health score.
