"""
agents/sales.py

Phase 14A: Sales Outreach Agent

RestaurantOS's own outbound sales pipeline — NOT the multi-client Scout/
Pipeline agents. This agent sells the RestaurantOS platform to new restaurant
clients.

Workflow:
  Weekly (Monday 08:00) — run_apollo_pull(pool):
    1. Call Apollo.io People Search API to find restaurant owners/managers.
    2. Upsert new leads into company_leads (skip duplicates via apollo_id).
    3. Call Claude (sales_qualify.txt) to score each new lead 0–10.
    4. Call Claude (sales_cold_email.txt) to generate a personalised cold email.
    5. Save email as approved outreach step (scheduled_for = now).

  Daily weekdays (10:00) — run_sales_batch(pool):
    1. Fetch up to BATCH_SIZE approved outreach steps with scheduled_for <= now.
    2. Send each via Resend API.
    3. Mark as sent; record resend_email_id for webhook tracking.

  Lead scoring via engagement:
    - email_opens and email_clicks are incremented by record_email_engagement()
      in tools/database.py, called from a Resend webhook handler (wire in
      production via a lightweight Flask/FastAPI endpoint).

Environment variables required:
  APOLLO_API_KEY       — Apollo.io API key
  RESEND_API_KEY       — Resend API key (already used by email_sender.py)
  FROM_EMAIL           — Sender address (e.g. team@restaurantos.ai)
  SALES_FROM_NAME      — Sender name shown in cold emails (e.g. "Jeff at RestaurantOS")
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone

import anthropic
import requests
import resend

from tools.database import (
    get_new_company_leads,
    save_company_lead,
    update_company_lead_score,
    save_outreach_draft,
    get_approved_outreach_batch,
    mark_company_outreach_sent,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BATCH_SIZE = 20              # Resend free-tier safe daily send limit
QUALIFICATION_THRESHOLD = 5  # Min score (0–10) to draft a cold email
APOLLO_SEARCH_LIMIT = 50     # Leads to pull per Apollo call

APOLLO_TITLES = [
    "restaurant owner",
    "restaurant manager",
    "general manager",
    "food and beverage manager",
    "operations manager",
]
APOLLO_INDUSTRIES = [
    "restaurants",
    "food & beverages",
    "food service",
    "hospitality",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_prompt(filename: str) -> str:
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
    with open(os.path.join(prompts_dir, filename), encoding="utf-8") as f:
        return f.read()


def _call_claude(system_prompt: str, user_content: str, max_tokens: int = 1500) -> dict:
    """Synchronous Claude Haiku call. Wrapped with asyncio.to_thread by callers."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ---------------------------------------------------------------------------
# 14A-1: Apollo.io lead pull
# ---------------------------------------------------------------------------

def _fetch_apollo_people() -> list[dict]:
    """Synchronous Apollo.io People Search call. Returns list of raw person dicts."""
    api_key = os.environ.get("APOLLO_API_KEY", "")
    if not api_key:
        print("[Sales] APOLLO_API_KEY not set — skipping Apollo pull")
        return []

    payload = {
        "api_key": api_key,
        "person_titles": APOLLO_TITLES,
        "organization_industry_tag_ids": [],
        "q_keywords": "restaurant",
        "per_page": APOLLO_SEARCH_LIMIT,
        "page": 1,
        "prospected_by_current_team": ["no"],
        "contact_email_status": ["verified", "likely to engage"],
    }

    try:
        resp = requests.post(
            "https://api.apollo.io/v1/mixed_people/search",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("people") or []
    except Exception as e:
        print(f"[Sales] Apollo.io API error: {e}")
        return []


def _parse_apollo_person(person: dict) -> dict:
    """Map an Apollo person record to our company_leads schema."""
    org = person.get("organization") or {}
    email = None

    # Apollo may return email directly or nested
    if person.get("email"):
        email = person["email"]
    elif person.get("contact") and person["contact"].get("email"):
        email = person["contact"]["email"]

    return {
        "apollo_id": person.get("id"),
        "company_name": org.get("name") or person.get("organization_name") or "Unknown",
        "owner_name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
        "owner_email": email,
        "phone": person.get("sanitized_phone") or (person.get("contact") or {}).get("sanitized_phone"),
        "website": org.get("website_url"),
        "location": person.get("city") or person.get("state") or "",
        "employee_count": org.get("estimated_num_employees"),
        "industry": (org.get("industry") or "restaurants").lower(),
        "source": "apollo",
    }


async def _pull_and_upsert_leads(pool) -> list[dict]:
    """Fetch Apollo.io leads and upsert into DB. Returns newly inserted lead rows."""
    people = await asyncio.to_thread(_fetch_apollo_people)
    print(f"[Sales] Apollo.io returned {len(people)} people")

    new_lead_ids = []
    for person in people:
        lead_data = _parse_apollo_person(person)
        if not lead_data.get("owner_email"):
            continue  # skip leads without an email address
        lead_id = await save_company_lead(pool, lead_data)
        if lead_id:
            new_lead_ids.append(lead_id)

    print(f"[Sales] Upserted {len(new_lead_ids)} new lead(s) from Apollo")
    return new_lead_ids


# ---------------------------------------------------------------------------
# 14A-2: Claude qualification scoring
# ---------------------------------------------------------------------------

async def _qualify_lead(lead: dict, qualify_prompt: str) -> dict:
    """Ask Claude to score a lead 0–10 and identify pain points.

    Returns: { score, pain_points, fit_signals, reasoning }
    """
    payload = {
        "product": "RestaurantOS — AI-powered restaurant management platform",
        "product_value_props": [
            "Automated inventory ordering (prevents stockouts, saves manager time)",
            "AI food cost analysis and pricing recommendations",
            "Weekly analytics reports with anomaly detection",
            "Customer success monitoring and proactive check-ins",
        ],
        "lead": {
            "company_name": lead.get("company_name"),
            "owner_name": lead.get("owner_name"),
            "industry": lead.get("industry"),
            "location": lead.get("location"),
            "employee_count": lead.get("employee_count"),
            "website": lead.get("website"),
        },
    }

    try:
        result = await asyncio.to_thread(_call_claude, qualify_prompt, json.dumps(payload))
        return result
    except Exception as e:
        print(f"[Sales] Qualification Claude error for '{lead.get('company_name')}': {e}")
        return {}


# ---------------------------------------------------------------------------
# 14A-3: Cold email generation
# ---------------------------------------------------------------------------

async def _generate_cold_email(lead: dict, score_result: dict, email_prompt: str) -> dict:
    """Ask Claude to write a personalised cold email for a qualified lead.

    Returns: { subject, body, reasoning }
    """
    payload = {
        "sender_name": os.environ.get("SALES_FROM_NAME", "The RestaurantOS Team"),
        "lead": {
            "company_name": lead.get("company_name"),
            "owner_name": lead.get("owner_name"),
            "location": lead.get("location"),
            "industry": lead.get("industry"),
            "employee_count": lead.get("employee_count"),
        },
        "qualification": {
            "score": score_result.get("score"),
            "pain_points": score_result.get("pain_points", []),
            "fit_signals": score_result.get("fit_signals", {}),
        },
    }

    try:
        result = await asyncio.to_thread(_call_claude, email_prompt, json.dumps(payload), 1000)
        return result
    except Exception as e:
        print(f"[Sales] Cold email Claude error for '{lead.get('company_name')}': {e}")
        return {}


# ---------------------------------------------------------------------------
# 14A-4: Resend cold email send
# ---------------------------------------------------------------------------

def _send_via_resend(to_email: str, to_name: str, subject: str, html_body: str) -> str | None:
    """Send a cold email via Resend. Returns Resend email ID or None on failure."""
    resend.api_key = os.environ.get("RESEND_API_KEY", "")
    from_email = os.environ.get("FROM_EMAIL", "team@restaurantos.ai")
    from_name = os.environ.get("SALES_FROM_NAME", "The RestaurantOS Team")

    try:
        params = {
            "from": f"{from_name} <{from_email}>",
            "to": [f"{to_name} <{to_email}>"],
            "subject": subject,
            "html": html_body,
        }
        response = resend.Emails.send(params)
        # resend SDK returns dict or object with 'id'
        if isinstance(response, dict):
            return response.get("id")
        return getattr(response, "id", None)
    except Exception as e:
        print(f"[Sales] Resend send error to {to_email}: {e}")
        return None


def _build_email_html(body_text: str, owner_name: str) -> str:
    """Wrap plain-text cold email body in minimal HTML."""
    # Convert line breaks to <br> and basic paragraph breaks
    escaped = body_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html_body = escaped.replace("\n\n", "</p><p>").replace("\n", "<br>")
    return f"""
    <html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                       color: #333; font-size: 15px; line-height: 1.7; max-width: 560px;
                       margin: 0 auto; padding: 24px;">
        <p>{html_body}</p>
        <p style="margin-top: 32px; font-size: 12px; color: #999;">
            You're receiving this because your restaurant may benefit from AI-powered management tools.
            <a href="mailto:unsubscribe@restaurantos.ai?subject=Unsubscribe&body={owner_name}"
               style="color: #999;">Unsubscribe</a>
        </p>
    </body></html>
    """


# ---------------------------------------------------------------------------
# 14A-5: Main entry points
# ---------------------------------------------------------------------------

async def run_apollo_pull(pool) -> None:
    """Weekly job: pull Apollo leads → qualify → draft cold emails.

    Called by sales_apollo_job() in main.py.
    Schedule: CronTrigger(day_of_week='mon', hour=8, minute=0)
    """
    t_start = time.time()

    qualify_prompt = _load_prompt("sales_qualify.txt")
    email_prompt = _load_prompt("sales_cold_email.txt")

    # 1. Pull new leads from Apollo.io
    await _pull_and_upsert_leads(pool)

    # 2. Fetch all unscored new leads (including ones from previous runs)
    new_leads = await get_new_company_leads(pool, limit=APOLLO_SEARCH_LIMIT)
    print(f"[Sales] {len(new_leads)} new lead(s) to qualify and email")

    emails_drafted = 0

    for lead in new_leads:
        lead_id = str(lead["id"])
        company = lead.get("company_name", "Unknown")

        # 3. Qualify with Claude
        score_result = await _qualify_lead(lead, qualify_prompt)
        score = float(score_result.get("score", 0))
        pain_points = score_result.get("pain_points", [])
        fit_signals = score_result.get("fit_signals", {})

        # Save score regardless of threshold (for tracking)
        await update_company_lead_score(pool, lead_id, score, fit_signals, pain_points)
        print(f"[Sales] '{company}': score={score:.1f}/10, pain_points={pain_points}")

        if score < QUALIFICATION_THRESHOLD:
            print(f"[Sales] '{company}': below threshold ({QUALIFICATION_THRESHOLD}) — skipping")
            continue

        # 4. Generate cold email
        email_result = await _generate_cold_email(lead, score_result, email_prompt)
        subject = email_result.get("subject", "")
        body = email_result.get("body", "")

        if not subject or not body:
            print(f"[Sales] '{company}': empty email generated — skipping")
            continue

        # 5. Save as approved draft (scheduled for immediate send)
        draft_id = await save_outreach_draft(
            pool,
            lead_id,
            sequence_step=1,
            subject=subject,
            body=body,
            scheduled_for=datetime.now(timezone.utc),
        )
        if draft_id:
            emails_drafted += 1
            print(f"[Sales] '{company}': cold email drafted — '{subject}'")

    duration_ms = int((time.time() - t_start) * 1000)
    print(
        f"[Sales] apollo_pull complete — {len(new_leads)} qualified, "
        f"{emails_drafted} email(s) drafted ({duration_ms}ms)"
    )


async def run_sales_batch(pool) -> None:
    """Daily job: send up to BATCH_SIZE approved outreach emails via Resend.

    Called by sales_batch_job() in main.py.
    Schedule: CronTrigger(day_of_week='mon-fri', hour=10, minute=0)
    """
    t_start = time.time()

    steps = await get_approved_outreach_batch(pool, limit=BATCH_SIZE)
    print(f"[Sales] sales_batch — {len(steps)} email(s) to send")

    sent = 0
    failed = 0

    for step in steps:
        outreach_id = str(step["id"])
        owner_email = step.get("owner_email", "")
        owner_name = step.get("owner_name") or step.get("company_name") or "there"
        subject = step.get("subject", "")
        body = step.get("body", "")
        company = step.get("company_name", "")

        html_body = _build_email_html(body, owner_name)

        resend_id = await asyncio.to_thread(
            _send_via_resend, owner_email, owner_name, subject, html_body
        )

        if resend_id:
            await mark_company_outreach_sent(pool, outreach_id, resend_id)
            sent += 1
            print(f"[Sales] Sent to '{company}' ({owner_email}) — resend_id={resend_id}")
        else:
            failed += 1
            print(f"[Sales] Failed to send to '{company}' ({owner_email})")

        # Small delay between sends to respect Resend rate limits
        await asyncio.sleep(0.5)

    duration_ms = int((time.time() - t_start) * 1000)
    print(
        f"[Sales] sales_batch complete — {sent} sent, {failed} failed ({duration_ms}ms)"
    )
