"""
agents/pipeline.py

Phase 10: Pipeline Agent

run_pipeline(pool, client, brand)
  — For each approved lead (stage='identified') with no existing sequence:
      1. Calls Claude (pipeline_sequence.txt) to generate a 5-step outreach sequence.
      2. Saves Step 1 as pending_approval, Steps 2-5 as draft with scheduled_for dates.
      3. Creates an approval request via the Orchestrator for Step 1.
  — Marks approved+due steps as sent and promotes the next draft step to pending_approval.

Called via _async_client_agent_job() in main.py.
Schedule: CronTrigger(day_of_week='mon-fri', hour=9, minute=0)
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone

import anthropic

from tools.database import (
    get_brand_config,
    get_approved_leads,
    get_outreach_sequence,
    save_outreach_step,
    get_due_outreach_steps,
    mark_outreach_sent,
    get_draft_steps_due_for_promotion,
    update_outreach_status,
    save_approval_request,
    log_client_agent_action,
)

# Days after sequence start for each step
STEP_DAYS = {1: 0, 2: 3, 3: 7, 4: 14, 5: 21}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_prompt(filename: str) -> str:
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
    with open(os.path.join(prompts_dir, filename), encoding="utf-8") as f:
        return f.read()


def _call_claude(system_prompt: str, user_content: str, max_tokens: int = 2000) -> dict:
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
# Sequence generation
# ---------------------------------------------------------------------------

async def _generate_sequence(
    pool,
    client_id: str,
    brand_id: str,
    lead: dict,
    brand: dict,
    system_prompt: str,
) -> int:
    """Generate and save a 5-step outreach sequence for one lead.

    Returns the number of steps saved (0 on failure).
    """
    lead_id = str(lead["id"])
    prospect_name = lead.get("prospect_name", "Unknown")

    user_payload = {
        "brand": {
            "name": brand.get("name"),
            "industry": brand.get("industry"),
            "business_model": brand.get("business_model"),
            "primary_channel": brand.get("primary_channel"),
            "tone": brand.get("tone"),
            "language_primary": brand.get("language_primary", "English"),
            "language_secondary": brand.get("language_secondary"),
            "target_audience": brand.get("target_audience"),
            "avg_deal_value": float(brand.get("avg_deal_value") or 0),
        },
        "lead": {
            "prospect_name": prospect_name,
            "website": lead.get("website"),
            "industry": lead.get("industry"),
            "size_signal": lead.get("size_signal"),
            "location": lead.get("location"),
            "qualification_score": float(lead.get("qualification_score") or 0),
            "fit_signals": lead.get("fit_signals") or [],
            "roi_estimate": float(lead.get("roi_estimate") or 0),
            "contract_value_estimate": float(lead.get("contract_value_estimate") or 0),
        },
    }

    try:
        result = await asyncio.to_thread(
            _call_claude, system_prompt, json.dumps(user_payload), 2000
        )
    except (json.JSONDecodeError, Exception) as e:
        print(f"[Pipeline] Claude sequence generation failed for '{prospect_name}': {e}")
        return 0

    steps = result.get("steps", [])
    if not steps:
        print(f"[Pipeline] No steps returned for '{prospect_name}'")
        return 0

    sequence_type = result.get("sequence_type", "new_acquisition")
    channel = result.get("channel", brand.get("primary_channel", "email"))
    now = datetime.now(timezone.utc)
    steps_saved = 0

    for step_raw in steps:
        step_num = int(step_raw.get("step", 1))
        day_offset = step_raw.get("day", STEP_DAYS.get(step_num, (step_num - 1) * 7))
        scheduled_for = now + timedelta(days=day_offset)
        status = "pending_approval" if step_num == 1 else "draft"

        step_data = {
            "step_number": step_num,
            "sequence_type": sequence_type,
            "channel": channel,
            "subject": step_raw.get("subject"),
            "body": step_raw.get("body", ""),
            "word_count": step_raw.get("word_count"),
            "status": status,
            "scheduled_for": scheduled_for,
        }

        step_id = await save_outreach_step(pool, client_id, brand_id, lead_id, step_data)
        if step_id:
            steps_saved += 1

    # Create approval request for Step 1
    if steps_saved > 0:
        try:
            step1 = next(
                (s for s in steps if int(s.get("step", 0)) == 1), steps[0] if steps else {}
            )
            expires_at = now + timedelta(hours=48)
            await save_approval_request(
                pool,
                client_id,
                brand_id,
                agent_name="pipeline",
                approval_type="outreach_step_1",
                payload={
                    "lead_id": lead_id,
                    "prospect_name": prospect_name,
                    "sequence_type": sequence_type,
                    "channel": channel,
                    "subject": step1.get("subject", ""),
                    "body_preview": (step1.get("body", "")[:200] + "…")
                    if len(step1.get("body", "")) > 200
                    else step1.get("body", ""),
                    "total_steps": len(steps),
                },
                expires_at=expires_at,
            )
            print(
                f"[Pipeline] Sequence created for '{prospect_name}': "
                f"{steps_saved} steps, approval request sent"
            )
        except Exception as e:
            print(f"[Pipeline] save_approval_request failed for '{prospect_name}': {e}")

    return steps_saved


# ---------------------------------------------------------------------------
# Step execution — send due approved steps
# ---------------------------------------------------------------------------

async def _execute_due_steps(pool, client_id: str) -> int:
    """Mark approved+due steps as sent. Returns count of steps sent."""
    due_steps = await get_due_outreach_steps(pool, client_id)
    sent_count = 0

    for step in due_steps:
        outreach_id = str(step["id"])
        prospect_name = step.get("prospect_name", "Unknown")
        step_num = step.get("step_number", "?")
        channel = step.get("channel", "email")

        try:
            await mark_outreach_sent(pool, outreach_id)
            sent_count += 1
            print(
                f"[Pipeline] Step {step_num} sent to '{prospect_name}' "
                f"via {channel} (outreach_id={outreach_id})"
            )
        except Exception as e:
            print(f"[Pipeline] mark_outreach_sent failed for '{prospect_name}' step {step_num}: {e}")

    return sent_count


# ---------------------------------------------------------------------------
# Draft promotion — move next step to pending_approval when previous step sent
# ---------------------------------------------------------------------------

async def _promote_due_drafts(pool, client_id: str, brand_id: str) -> int:
    """Promote draft steps that are due (prev step sent) to pending_approval.

    Creates an approval request for each promoted step.
    Returns count of steps promoted.
    """
    due_drafts = await get_draft_steps_due_for_promotion(pool, client_id)
    promoted = 0

    for step in due_drafts:
        outreach_id = str(step["id"])
        prospect_name = step.get("prospect_name", "Unknown")
        step_num = step.get("step_number", "?")
        lead_id = str(step["lead_id"])

        try:
            await update_outreach_status(pool, outreach_id, "pending_approval")

            await save_approval_request(
                pool,
                client_id,
                brand_id,
                agent_name="pipeline",
                approval_type=f"outreach_step_{step_num}",
                payload={
                    "outreach_id": outreach_id,
                    "lead_id": lead_id,
                    "prospect_name": prospect_name,
                    "step_number": step_num,
                    "channel": step.get("channel", "email"),
                    "subject": step.get("subject", ""),
                    "body_preview": (step.get("body", "")[:200] + "…")
                    if len(step.get("body", "")) > 200
                    else step.get("body", ""),
                },
                expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
            promoted += 1
            print(
                f"[Pipeline] Step {step_num} for '{prospect_name}' promoted to pending_approval"
            )
        except Exception as e:
            print(
                f"[Pipeline] promote_draft failed for '{prospect_name}' step {step_num}: {e}"
            )

    return promoted


# ---------------------------------------------------------------------------
# run_pipeline — main entry point
# ---------------------------------------------------------------------------

async def run_pipeline(pool, client: dict, brand: dict) -> None:
    """Pipeline agent: generate outreach sequences and execute approved steps."""
    start = time.time()
    client_id = str(client["id"])
    brand_id = str(brand["id"])
    client_name = client["name"]
    brand_name = brand["name"]

    # 1. Fetch brand config
    try:
        brand_config = await get_brand_config(pool, brand_id)
    except Exception as e:
        print(f"[Pipeline] get_brand_config failed for {brand_name}: {e}")
        brand_config = brand
    merged_brand = {**brand, **(brand_config or {})}

    # 2. Load sequence prompt
    try:
        sequence_prompt = _load_prompt("pipeline_sequence.txt")
    except FileNotFoundError:
        print("[Pipeline] pipeline_sequence.txt not found — aborting")
        return

    # 3. Fetch approved leads with no existing sequence
    try:
        new_leads = await get_approved_leads(pool, client_id, brand_id)
    except Exception as e:
        print(f"[Pipeline] get_approved_leads failed for {client_name}: {e}")
        new_leads = []

    print(
        f"[Pipeline] {client_name}/{brand_name}: "
        f"{len(new_leads)} new approved lead(s) to sequence"
    )

    sequences_created = 0
    for lead in new_leads:
        steps_saved = await _generate_sequence(
            pool, client_id, brand_id, lead, merged_brand, sequence_prompt
        )
        if steps_saved > 0:
            sequences_created += 1

    # 4. Execute approved steps that are due
    try:
        sent_count = await _execute_due_steps(pool, client_id)
    except Exception as e:
        print(f"[Pipeline] _execute_due_steps failed for {client_name}: {e}")
        sent_count = 0

    # 5. Promote draft steps whose previous step was sent
    try:
        promoted_count = await _promote_due_drafts(pool, client_id, brand_id)
    except Exception as e:
        print(f"[Pipeline] _promote_due_drafts failed for {client_name}: {e}")
        promoted_count = 0

    # 6. Log
    duration_ms = int((time.time() - start) * 1000)
    summary = (
        f"Created {sequences_created} new sequence(s), "
        f"sent {sent_count} step(s), "
        f"promoted {promoted_count} draft(s) to pending_approval."
    )
    print(f"[Pipeline] {client_name}/{brand_name}: {summary}")

    try:
        await log_client_agent_action(
            pool,
            client_id,
            brand_id,
            "pipeline",
            "outreach_sequencing",
            summary,
            {
                "new_leads_sequenced": sequences_created,
                "steps_sent": sent_count,
                "drafts_promoted": promoted_count,
            },
            status="completed",
            duration_ms=duration_ms,
        )
    except Exception as e:
        print(f"[Pipeline] log failed for {client_name}: {e}")
