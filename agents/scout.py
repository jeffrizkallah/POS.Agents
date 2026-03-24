"""
agents/scout.py

Phase 9: Scout Agent

run_scout(pool, client, brand)
  — Fetches up to 3 unqualified prospects for the brand.
  — Calls Claude (scout_qualify.txt) to score each prospect against brand config.
  — Saves qualification score + fit_signals to client_prospects.
  — If score >= threshold (default 6): creates client_lead with stage=pending_approval
    and routes an approval request through the Orchestrator.
  — Checks client_contracts for renewals within 90 days and saves renewal alerts
    to client_intelligence.

Called via _async_client_agent_job() in main.py.
Schedule: CronTrigger(day_of_week='mon-fri', hour=7, minute=0)
"""

import asyncio
import json
import os
import time

import anthropic

from tools.database import (
    get_brand_config,
    get_unqualified_prospects,
    update_prospect_score,
    save_lead,
    get_contracts_nearing_renewal,
    save_approval_request,
    save_intelligence,
    log_client_agent_action,
)

# Minimum score (out of 10) to promote a prospect to a lead
QUALIFICATION_THRESHOLD = 6.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_prompt(filename: str) -> str:
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
    with open(os.path.join(prompts_dir, filename), encoding="utf-8") as f:
        return f.read()


def _call_claude(system_prompt: str, user_content: str, max_tokens: int = 1000) -> dict:
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
# Prospect qualification
# ---------------------------------------------------------------------------

async def _qualify_prospect(
    pool,
    client_id: str,
    brand_id: str,
    brand: dict,
    prospect: dict,
    system_prompt: str,
) -> dict:
    """Score a single prospect with Claude and save results. Returns enriched prospect dict."""
    prospect_id = str(prospect["id"])

    user_payload = {
        "brand": {
            "name": brand.get("name"),
            "industry": brand.get("industry"),
            "business_model": brand.get("business_model"),
            "target_audience": brand.get("target_audience"),
            "avg_deal_value": float(brand.get("avg_deal_value") or 0),
            "avg_customer_ltv": float(brand.get("avg_customer_ltv") or 0),
            "roi_target_multiplier": float(brand.get("roi_target_multiplier") or 3.0),
            "primary_channel": brand.get("primary_channel"),
        },
        "prospect": {
            "name": prospect.get("name"),
            "website": prospect.get("website"),
            "industry": prospect.get("industry"),
            "size_signal": prospect.get("size_signal"),
            "location": prospect.get("location"),
            "source": prospect.get("source"),
        },
    }

    try:
        result = await asyncio.to_thread(
            _call_claude, system_prompt, json.dumps(user_payload)
        )
    except (json.JSONDecodeError, Exception) as e:
        print(f"[Scout] Claude qualification failed for prospect {prospect.get('name')}: {e}")
        return {}

    score = float(result.get("score", 0))
    fit_signals = result.get("fit_signals", [])
    roi_estimate = result.get("roi_estimate")
    recommended_action = result.get("recommended_action", "")

    # Determine new status
    new_status = "qualified" if score >= QUALIFICATION_THRESHOLD else "disqualified"

    await update_prospect_score(
        pool,
        prospect_id,
        score,
        fit_signals,
        roi_estimate=float(roi_estimate) if roi_estimate is not None else None,
        status=new_status,
    )

    print(
        f"[Scout] Prospect '{prospect['name']}': score={score:.1f} "
        f"→ {new_status} ({recommended_action})"
    )

    return {
        "prospect_id": prospect_id,
        "prospect_name": prospect.get("name", ""),
        "score": score,
        "status": new_status,
        "roi_estimate": roi_estimate,
        "fit_signals": fit_signals,
        "recommended_action": recommended_action,
    }


# ---------------------------------------------------------------------------
# run_scout — main entry point
# ---------------------------------------------------------------------------

async def run_scout(pool, client: dict, brand: dict) -> None:
    """Scout agent: qualify prospects and flag renewals for one client/brand."""
    start = time.time()
    client_id = str(client["id"])
    brand_id = str(brand["id"])
    client_name = client["name"]
    brand_name = brand["name"]

    # ------------------------------------------------------------------
    # 1. Fetch brand config (tone, audience, deal value, ROI target, etc.)
    # ------------------------------------------------------------------
    try:
        brand_config = await get_brand_config(pool, brand_id)
    except Exception as e:
        print(f"[Scout] get_brand_config failed for {brand_name}: {e}")
        brand_config = brand  # fall back to the brand dict passed in

    # Merge brand_config fields into brand dict (brand_config may be richer)
    merged_brand = {**brand, **(brand_config or {})}

    # ------------------------------------------------------------------
    # 2. Load qualify prompt
    # ------------------------------------------------------------------
    try:
        qualify_prompt = _load_prompt("scout_qualify.txt")
    except FileNotFoundError:
        print("[Scout] scout_qualify.txt not found — aborting")
        return

    # ------------------------------------------------------------------
    # 3. Fetch up to 3 unqualified prospects
    # ------------------------------------------------------------------
    try:
        prospects = await get_unqualified_prospects(pool, client_id, brand_id, limit=3)
    except Exception as e:
        print(f"[Scout] get_unqualified_prospects failed for {client_name}: {e}")
        prospects = []

    print(f"[Scout] {client_name}/{brand_name}: {len(prospects)} unqualified prospect(s)")

    leads_created = 0
    qualified_results = []

    for prospect in prospects:
        result = await _qualify_prospect(
            pool, client_id, brand_id, merged_brand, prospect, qualify_prompt
        )
        if not result:
            continue

        qualified_results.append(result)

        # ------------------------------------------------------------------
        # 4. If score >= threshold → create lead + approval request
        # ------------------------------------------------------------------
        if result["score"] >= QUALIFICATION_THRESHOLD:
            try:
                from datetime import datetime, timedelta, timezone
                lead_id = await save_lead(
                    pool,
                    client_id,
                    brand_id,
                    result["prospect_id"],
                    stage="pending_approval",
                    contract_value_estimate=result.get("roi_estimate"),
                )

                if lead_id:
                    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
                    await save_approval_request(
                        pool,
                        client_id,
                        brand_id,
                        agent_name="scout",
                        approval_type="new_lead",
                        payload={
                            "lead_id": lead_id,
                            "prospect_name": result["prospect_name"],
                            "score": result["score"],
                            "fit_signals": result["fit_signals"],
                            "roi_estimate": result.get("roi_estimate"),
                            "recommended_action": result.get("recommended_action"),
                        },
                        expires_at=expires_at,
                    )
                    leads_created += 1
                    print(
                        f"[Scout] Lead created for '{result['prospect_name']}' "
                        f"(score={result['score']:.1f}) — approval request sent"
                    )
            except Exception as e:
                print(f"[Scout] save_lead/approval failed for '{result['prospect_name']}': {e}")

    # ------------------------------------------------------------------
    # 5. Check for contracts nearing renewal (within 90 days)
    # ------------------------------------------------------------------
    renewals = []
    try:
        renewals = await get_contracts_nearing_renewal(pool, client_id, days=90)
    except Exception as e:
        print(f"[Scout] get_contracts_nearing_renewal failed for {client_name}: {e}")

    for contract in renewals:
        renewal_date = contract.get("renewal_date")
        prospect_name = contract.get("prospect_name", "Unknown")
        value = float(contract.get("value") or 0)
        try:
            await save_intelligence(
                pool,
                client_id,
                "renewal_alert",
                {
                    "contract_id": str(contract["id"]),
                    "prospect_name": prospect_name,
                    "renewal_date": str(renewal_date),
                    "contract_value": value,
                    "brand": brand_name,
                },
                urgency="urgent" if renewal_date and (renewal_date - __import__("datetime").date.today()).days <= 30 else "normal",
            )
            print(f"[Scout] Renewal alert saved for '{prospect_name}' (due {renewal_date})")
        except Exception as e:
            print(f"[Scout] save_intelligence (renewal) failed for contract {contract['id']}: {e}")

    # ------------------------------------------------------------------
    # 6. Log
    # ------------------------------------------------------------------
    duration_ms = int((time.time() - start) * 1000)
    summary = (
        f"Qualified {len(qualified_results)} prospect(s), "
        f"created {leads_created} lead(s), "
        f"{len(renewals)} renewal alert(s)."
    )
    print(f"[Scout] {client_name}/{brand_name}: {summary}")

    try:
        await log_client_agent_action(
            pool,
            client_id,
            brand_id,
            "scout",
            "prospect_qualification",
            summary,
            {
                "prospects_evaluated": len(qualified_results),
                "leads_created": leads_created,
                "renewals_flagged": len(renewals),
                "results": qualified_results,
            },
            status="completed",
            duration_ms=duration_ms,
        )
    except Exception as e:
        print(f"[Scout] log failed for {client_name}: {e}")
