"""
agents/customer_care.py

Phase 11: Customer Care Agent

run_care_feedback(pool, client, brand)  — runs every 30 minutes
  1. Fetches new unprocessed feedback for the brand.
  2. Calls Claude (care_classify.txt) to classify each item:
     type, urgency, sentiment, at_risk_flag.
  3. If critical: saves to client_intelligence immediately (Orchestrator escalates).
  4. Calls Claude (care_respond.txt) to draft a response in brand tone + language.
  5. Saves classification + draft; sets status=pending_approval.
  6. Creates Orchestrator approval request for the response.
  7. If sentiment >= 8: saves testimonial row + adds permission request to draft.

run_competitive_intel(pool, client, brand)  — runs 1st of each month
  1. Fetches active competitor list.
  2. For each competitor: simulates research (website + Google reviews summary).
  3. Calls Claude (care_competitor.txt) — strengths, weaknesses, positioning.
  4. Saves monthly snapshot to client_competitor_snapshots.
  5. Calls Claude (care_strategy.txt) — ELIMINATE/REDUCE/RAISE/CREATE analysis.
  6. Saves strategic report as pending_approval + creates Orchestrator approval.

Called via _async_client_agent_job() in main.py.
Schedules:
  care_feedback_job()  — CronTrigger(minute='*/30')
  care_intel_job()     — CronTrigger(day=1, hour=6, minute=0)
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone

import anthropic

from tools.database import (
    get_brand_config,
    get_brand_care_config,
    get_new_feedback,
    save_feedback_classification,
    save_testimonial,
    get_competitors,
    save_competitor_snapshot,
    save_strategic_report,
    save_approval_request,
    save_intelligence,
    log_client_agent_action,
)

# Sentiment score threshold to promote feedback to a testimonial
TESTIMONIAL_THRESHOLD = 8.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_prompt(filename: str) -> str:
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
    with open(os.path.join(prompts_dir, filename), encoding="utf-8") as f:
        return f.read()


def _call_claude(
    system_prompt: str, user_content: str, max_tokens: int = 1500
) -> dict:
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


def _build_brand_context(brand: dict, care_config: dict | None) -> dict:
    """Merge brand + care config into a flat dict for Claude payloads."""
    ctx = {
        "name": brand.get("name"),
        "industry": brand.get("industry"),
        "tone": brand.get("tone", "professional"),
        "language_primary": brand.get("language_primary", "English"),
        "language_secondary": brand.get("language_secondary"),
        "target_audience": brand.get("target_audience"),
        "avg_customer_ltv": float(brand.get("avg_customer_ltv") or 0),
        "roi_target_multiplier": float(brand.get("roi_target_multiplier") or 3.0),
    }
    if care_config:
        ctx["at_risk_keywords"] = care_config.get("at_risk_keywords") or []
        ctx["escalation_triggers"] = care_config.get("escalation_triggers") or []
        ctx["retention_offer_template"] = care_config.get("retention_offer_template", "")
    else:
        ctx["at_risk_keywords"] = []
        ctx["escalation_triggers"] = []
        ctx["retention_offer_template"] = ""
    return ctx


# ---------------------------------------------------------------------------
# Feedback triage helpers
# ---------------------------------------------------------------------------

async def _classify_feedback(
    feedback: dict, brand_ctx: dict, classify_prompt: str
) -> dict:
    """Call Claude to classify one feedback item. Returns classification dict."""
    payload = {
        "brand": brand_ctx,
        "feedback": {
            "id": str(feedback["id"]),
            "channel": feedback.get("channel", "web"),
            "text": feedback.get("text", ""),
        },
    }
    try:
        return await asyncio.to_thread(
            _call_claude, classify_prompt, json.dumps(payload), 800
        )
    except Exception as e:
        print(f"[Care] classify_feedback failed for feedback {feedback['id']}: {e}")
        return {}


async def _draft_response(
    feedback: dict, classification: dict, brand_ctx: dict, respond_prompt: str
) -> dict:
    """Call Claude to draft a response. Returns response dict."""
    payload = {
        "brand": brand_ctx,
        "feedback": {
            "channel": feedback.get("channel", "web"),
            "text": feedback.get("text", ""),
        },
        "classification": {
            "feedback_type": classification.get("feedback_type", "neutral"),
            "urgency": classification.get("urgency", "normal"),
            "sentiment_score": classification.get("sentiment_score", 5.0),
            "is_at_risk_flag": classification.get("is_at_risk_flag", False),
        },
    }
    try:
        return await asyncio.to_thread(
            _call_claude, respond_prompt, json.dumps(payload), 1000
        )
    except Exception as e:
        print(f"[Care] draft_response failed for feedback {feedback['id']}: {e}")
        return {}


# ---------------------------------------------------------------------------
# run_care_feedback — main feedback triage loop
# ---------------------------------------------------------------------------

async def run_care_feedback(pool, client: dict, brand: dict) -> None:
    """Triage all new feedback for one client/brand."""
    start = time.time()
    client_id = str(client["id"])
    brand_id = str(brand["id"])
    client_name = client["name"]
    brand_name = brand["name"]

    # 1. Fetch brand config + care config
    try:
        brand_config = await get_brand_config(pool, brand_id)
    except Exception as e:
        print(f"[Care] get_brand_config failed for {brand_name}: {e}")
        brand_config = brand

    try:
        care_config = await get_brand_care_config(pool, brand_id)
    except Exception as e:
        print(f"[Care] get_brand_care_config failed for {brand_name}: {e}")
        care_config = None

    merged_brand = {**brand, **(brand_config or {})}
    brand_ctx = _build_brand_context(merged_brand, care_config)

    # 2. Load prompts
    try:
        classify_prompt = _load_prompt("care_classify.txt")
        respond_prompt = _load_prompt("care_respond.txt")
    except FileNotFoundError as e:
        print(f"[Care] Prompt file missing — {e}. Aborting feedback run.")
        return

    # 3. Fetch new feedback
    try:
        feedback_items = await get_new_feedback(pool, client_id, brand_id)
    except Exception as e:
        print(f"[Care] get_new_feedback failed for {client_name}: {e}")
        feedback_items = []

    print(f"[Care] {client_name}/{brand_name}: {len(feedback_items)} new feedback item(s)")

    classified_count = 0
    critical_count = 0
    testimonial_count = 0

    for item in feedback_items:
        feedback_id = str(item["id"])

        # --- Classify ---
        classification = await _classify_feedback(item, brand_ctx, classify_prompt)
        if not classification:
            continue

        urgency = classification.get("urgency", "normal")
        sentiment = float(classification.get("sentiment_score") or 5.0)
        is_at_risk = bool(classification.get("is_at_risk_flag", False))

        # --- Escalate critical items immediately ---
        if urgency == "critical":
            try:
                await save_intelligence(
                    pool,
                    client_id,
                    "critical_feedback",
                    {
                        "feedback_id": feedback_id,
                        "brand": brand_name,
                        "channel": item.get("channel"),
                        "text_preview": (item.get("text", "")[:300] + "…")
                        if len(item.get("text", "")) > 300
                        else item.get("text", ""),
                        "urgency": urgency,
                        "is_at_risk_flag": is_at_risk,
                        "at_risk_reason": classification.get("at_risk_reason", ""),
                    },
                    urgency="critical",
                )
                critical_count += 1
                print(f"[Care] Critical feedback {feedback_id} escalated to intelligence")
            except Exception as e:
                print(f"[Care] save_intelligence (critical) failed: {e}")

        # --- Draft response ---
        response_result = await _draft_response(
            item, classification, brand_ctx, respond_prompt
        )
        response_draft = response_result.get("response_draft", "")
        includes_testimonial_request = response_result.get(
            "includes_testimonial_request", False
        )

        # --- Save classification + draft ---
        try:
            await save_feedback_classification(
                pool,
                feedback_id,
                {
                    "feedback_type": classification.get("feedback_type", "neutral"),
                    "urgency": urgency,
                    "sentiment_score": sentiment,
                    "is_at_risk_flag": is_at_risk,
                    "response_draft": response_draft,
                    "status": "pending_approval",
                },
            )
            classified_count += 1
        except Exception as e:
            print(f"[Care] save_feedback_classification failed for {feedback_id}: {e}")
            continue

        # --- Create approval request for the response ---
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
            await save_approval_request(
                pool,
                client_id,
                brand_id,
                agent_name="customer_care",
                approval_type="feedback_response",
                payload={
                    "feedback_id": feedback_id,
                    "channel": item.get("channel"),
                    "feedback_type": classification.get("feedback_type"),
                    "urgency": urgency,
                    "sentiment_score": sentiment,
                    "is_at_risk_flag": is_at_risk,
                    "response_preview": (response_draft[:200] + "…")
                    if len(response_draft) > 200
                    else response_draft,
                    "includes_testimonial_request": includes_testimonial_request,
                },
                expires_at=expires_at,
            )
        except Exception as e:
            print(f"[Care] save_approval_request failed for feedback {feedback_id}: {e}")

        # --- High sentiment → save testimonial row ---
        if sentiment >= TESTIMONIAL_THRESHOLD:
            try:
                testimonial_id = await save_testimonial(
                    pool, client_id, brand_id, feedback_id, item.get("text", "")
                )
                if testimonial_id:
                    testimonial_count += 1
                    print(
                        f"[Care] Testimonial queued for feedback {feedback_id} "
                        f"(sentiment={sentiment:.1f})"
                    )
            except Exception as e:
                print(f"[Care] save_testimonial failed for {feedback_id}: {e}")

    # --- Log ---
    duration_ms = int((time.time() - start) * 1000)
    summary = (
        f"Classified {classified_count}/{len(feedback_items)} feedback items, "
        f"{critical_count} critical escalation(s), "
        f"{testimonial_count} testimonial(s) queued."
    )
    print(f"[Care] {client_name}/{brand_name}: {summary}")

    try:
        await log_client_agent_action(
            pool,
            client_id,
            brand_id,
            "customer_care",
            "feedback_triage",
            summary,
            {
                "total_feedback": len(feedback_items),
                "classified": classified_count,
                "critical_escalations": critical_count,
                "testimonials_queued": testimonial_count,
            },
            status="completed",
            duration_ms=duration_ms,
        )
    except Exception as e:
        print(f"[Care] log failed for {client_name}: {e}")


# ---------------------------------------------------------------------------
# Competitive intelligence helpers
# ---------------------------------------------------------------------------

async def _profile_competitor(
    competitor: dict, brand_ctx: dict, competitor_prompt: str
) -> dict:
    """Call Claude to profile one competitor from available signals."""
    # Build a simulated research payload.
    # In production this would include real Google/scraping data injected externally.
    payload = {
        "brand": {
            "name": brand_ctx.get("name"),
            "industry": brand_ctx.get("industry"),
        },
        "competitor": {
            "name": competitor.get("name"),
            "website_url": competitor.get("website_url"),
            "instagram_handle": competitor.get("instagram_handle"),
        },
        "website_summary": (
            f"Website: {competitor.get('website_url', 'N/A')}. "
            "No live scrape data available — use general industry knowledge."
        ),
        "google_reviews_sample": [],
        "note": (
            "Use your general knowledge of this type of business to infer "
            "likely strengths and weaknesses. Evidence-based only — "
            "require 3+ signals to assert a strength or weakness."
        ),
    }
    try:
        return await asyncio.to_thread(
            _call_claude, competitor_prompt, json.dumps(payload), 1500
        )
    except Exception as e:
        print(f"[Care] competitor profile failed for '{competitor['name']}': {e}")
        return {}


async def _generate_strategy(
    brand_ctx: dict, snapshots: list[dict], strategy_prompt: str
) -> dict:
    """Call Claude to generate ELIMINATE/REDUCE/RAISE/CREATE strategic analysis."""
    payload = {
        "brand": {
            "name": brand_ctx.get("name"),
            "industry": brand_ctx.get("industry"),
            "target_audience": brand_ctx.get("target_audience"),
            "roi_target_multiplier": brand_ctx.get("roi_target_multiplier", 3.0),
        },
        "competitive_landscape": [
            {
                "competitor_name": s.get("competitor_name"),
                "actual_strengths": s.get("actual_strengths", []),
                "actual_weaknesses": s.get("actual_weaknesses", []),
                "positioning_summary": s.get("positioning_summary"),
            }
            for s in snapshots
        ],
    }
    try:
        return await asyncio.to_thread(
            _call_claude, strategy_prompt, json.dumps(payload), 2000
        )
    except Exception as e:
        print(f"[Care] strategy generation failed: {e}")
        return {}


# ---------------------------------------------------------------------------
# run_competitive_intel — monthly competitive analysis
# ---------------------------------------------------------------------------

async def run_competitive_intel(pool, client: dict, brand: dict) -> None:
    """Run monthly competitive intelligence for one client/brand."""
    start = time.time()
    client_id = str(client["id"])
    brand_id = str(brand["id"])
    client_name = client["name"]
    brand_name = brand["name"]

    # 1. Fetch brand config
    try:
        brand_config = await get_brand_config(pool, brand_id)
    except Exception as e:
        print(f"[Care-Intel] get_brand_config failed for {brand_name}: {e}")
        brand_config = brand

    try:
        care_config = await get_brand_care_config(pool, brand_id)
    except Exception:
        care_config = None

    merged_brand = {**brand, **(brand_config or {})}
    brand_ctx = _build_brand_context(merged_brand, care_config)

    # 2. Load prompts
    try:
        competitor_prompt = _load_prompt("care_competitor.txt")
        strategy_prompt = _load_prompt("care_strategy.txt")
    except FileNotFoundError as e:
        print(f"[Care-Intel] Prompt file missing — {e}. Aborting intel run.")
        return

    # 3. Fetch competitors
    try:
        competitors = await get_competitors(pool, client_id, brand_id)
    except Exception as e:
        print(f"[Care-Intel] get_competitors failed for {client_name}: {e}")
        competitors = []

    print(
        f"[Care-Intel] {client_name}/{brand_name}: "
        f"{len(competitors)} competitor(s) to profile"
    )

    if not competitors:
        print(f"[Care-Intel] No competitors configured for {brand_name} — skipping")
        return

    snapshot_month = datetime.now(timezone.utc).date().replace(day=1)
    enriched_snapshots = []

    # 4. Profile each competitor
    for comp in competitors:
        competitor_id = str(comp["id"])
        profile = await _profile_competitor(comp, brand_ctx, competitor_prompt)
        if not profile:
            continue

        snapshot_data = {
            "snapshot_month": snapshot_month,
            "website_summary": profile.get("positioning_summary", ""),
            "google_rating": None,
            "google_reviews_sample": [],
            "instagram_data": {},
            "actual_strengths": profile.get("actual_strengths", []),
            "actual_weaknesses": profile.get("actual_weaknesses", []),
            "positioning_summary": profile.get("positioning_summary", ""),
        }

        try:
            await save_competitor_snapshot(
                pool, client_id, competitor_id, snapshot_data
            )
            print(
                f"[Care-Intel] Snapshot saved for competitor '{comp['name']}' "
                f"({len(snapshot_data['actual_strengths'])} strengths, "
                f"{len(snapshot_data['actual_weaknesses'])} weaknesses)"
            )
        except Exception as e:
            print(f"[Care-Intel] save_competitor_snapshot failed for '{comp['name']}': {e}")

        enriched_snapshots.append({
            **snapshot_data,
            "competitor_name": comp["name"],
        })

    if not enriched_snapshots:
        print(f"[Care-Intel] No snapshots produced for {brand_name} — skipping strategy")
        return

    # 5. Generate strategic analysis
    strategy = await _generate_strategy(brand_ctx, enriched_snapshots, strategy_prompt)
    if not strategy:
        print(f"[Care-Intel] Strategy generation failed for {brand_name}")
        return

    # 6. Save strategic report
    report_data = {
        "competitors_analysed": len(enriched_snapshots),
        "landscape_summary": strategy.get("executive_summary", ""),
        "universal_complaints": strategy.get("universal_complaints", []),
        "unserved_needs": strategy.get("unserved_needs", []),
        "opportunities": strategy.get("opportunities", []),
        "executive_summary": strategy.get("executive_summary", ""),
    }

    try:
        report_id = await save_strategic_report(pool, client_id, brand_id, report_data)
        print(
            f"[Care-Intel] Strategic report saved (id={report_id}, "
            f"{len(report_data['opportunities'])} opportunity(s))"
        )
    except Exception as e:
        print(f"[Care-Intel] save_strategic_report failed for {brand_name}: {e}")
        report_id = None

    # 7. Create approval request for the strategic report
    if report_id:
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            opportunities = strategy.get("opportunities", [])
            await save_approval_request(
                pool,
                client_id,
                brand_id,
                agent_name="customer_care",
                approval_type="strategic_report",
                payload={
                    "report_id": report_id,
                    "competitors_analysed": len(enriched_snapshots),
                    "opportunities_count": len(opportunities),
                    "top_opportunity": opportunities[0] if opportunities else None,
                    "executive_summary": (
                        strategy.get("executive_summary", "")[:300] + "…"
                    )
                    if len(strategy.get("executive_summary", "")) > 300
                    else strategy.get("executive_summary", ""),
                },
                expires_at=expires_at,
            )
        except Exception as e:
            print(f"[Care-Intel] save_approval_request (strategy) failed: {e}")

    # 8. Log
    duration_ms = int((time.time() - start) * 1000)
    summary = (
        f"Profiled {len(enriched_snapshots)} competitor(s), "
        f"saved strategic report with "
        f"{len(strategy.get('opportunities', []))} opportunity(s)."
    )
    print(f"[Care-Intel] {client_name}/{brand_name}: {summary}")

    try:
        await log_client_agent_action(
            pool,
            client_id,
            brand_id,
            "customer_care",
            "competitive_intel",
            summary,
            {
                "competitors_profiled": len(enriched_snapshots),
                "opportunities": len(strategy.get("opportunities", [])),
                "report_id": report_id,
            },
            status="completed",
            duration_ms=duration_ms,
        )
    except Exception as e:
        print(f"[Care-Intel] log failed for {client_name}: {e}")
