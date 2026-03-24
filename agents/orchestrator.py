"""
agents/orchestrator.py

Master governance layer for the multi-client platform.

run_orchestrator(pool, client, brand)
  — Routes pending approvals to the client owner via email.
  — Sends reminders for approvals overdue by >12 hours.
  — Expires approvals past their deadline.
  — Classifies ROI per channel (green/yellow/red/black).
  — Flags underperforming channels to client_intelligence.
  — Saves a 30-day rolling ROI snapshot.

run_daily_briefing(pool, client, brand)
  — Assembles pending approvals + ROI status + recent intelligence.
  — Calls Claude (Haiku) to generate a structured briefing JSON.
  — Emails the briefing to the client owner.

Both are called via _async_client_agent_job() in main.py.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone

import anthropic
import resend

from tools.database import (
    get_pending_approvals,
    save_approval_request,          # noqa: F401 — re-exported for other agents
    update_approval_status,
    get_roi_by_channel,
    get_budget_envelopes,           # noqa: F401 — re-exported for other agents
    save_roi_snapshot,
    save_intelligence,
    get_recent_intelligence,
    log_client_agent_action,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_prompt(filename: str) -> str:
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
    with open(os.path.join(prompts_dir, filename), encoding="utf-8") as f:
        return f.read()


def classify_roi(roi: float, target: float) -> str:
    """Return color band for a channel's ROI vs the brand's target multiplier.

    green  — at or above target (≥ target)
    yellow — approaching target (≥ 70% of target)
    red    — below target (≥ 30% of target)
    black  — critically below target (< 30% of target)
    """
    if roi >= target:
        return "green"
    if roi >= target * 0.7:
        return "yellow"
    if roi >= target * 0.3:
        return "red"
    return "black"


def _call_claude(system_prompt: str, user_content: str, max_tokens: int = 1500) -> dict:
    """Synchronous Claude call (wrapped with asyncio.to_thread by callers)."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ---------------------------------------------------------------------------
# run_orchestrator — approval routing + ROI classification
# ---------------------------------------------------------------------------

async def run_orchestrator(pool, client: dict, brand: dict) -> None:
    """Route pending approvals and classify ROI channels for one client/brand."""
    start = time.time()
    client_id = str(client["id"])
    brand_id = str(brand["id"])
    client_name = client["name"]
    brand_name = brand["name"]
    owner_email = client.get("owner_email")
    roi_target = float(brand.get("roi_target_multiplier") or 3.0)
    dashboard_url = os.environ.get("APP_URL", "https://app.restaurantos.com")

    # ------------------------------------------------------------------
    # 1. Fetch pending approvals
    # ------------------------------------------------------------------
    try:
        pending = await get_pending_approvals(pool, client_id)
    except Exception as e:
        print(f"[Orchestrator] get_pending_approvals failed for {client_name}: {e}")
        pending = []

    now = datetime.now(timezone.utc)
    reminder_sent = 0
    expired_count = 0

    for approval in pending:
        approval_id = str(approval["id"])
        created_at = approval["created_at"]
        expires_at = approval.get("expires_at")
        agent_name = approval["agent_name"]
        approval_type = approval["approval_type"]
        payload = approval.get("payload") or {}

        # Expire if past deadline
        if expires_at and now > expires_at:
            try:
                await update_approval_status(pool, approval_id, "expired")
                expired_count += 1
                print(f"[Orchestrator] Expired approval {approval_id} for {client_name}")
            except Exception as e:
                print(f"[Orchestrator] expire failed ({approval_id}): {e}")
            continue

        # Send reminder if >12 hours old and owner email exists
        hours_pending = (now - created_at).total_seconds() / 3600
        if hours_pending > 12 and owner_email:
            try:
                payload_preview = json.dumps(payload, indent=2)[:400]
                resend.api_key = os.environ.get("RESEND_API_KEY", "")
                await asyncio.to_thread(
                    resend.Emails.send,
                    {
                        "from": os.environ.get("FROM_EMAIL", "alerts@restaurantos.ai"),
                        "to": [owner_email],
                        "subject": f"Reminder: {approval_type} awaiting approval — {client_name}",
                        "html": f"""
                        <div style="font-family:sans-serif;max-width:580px;margin:0 auto">
                          <div style="background:#7c3aed;color:white;padding:20px 28px;border-radius:8px 8px 0 0">
                            <h1 style="margin:0;font-size:18px">Action Required — {client_name}</h1>
                            <p style="margin:6px 0 0;opacity:.8;font-size:13px">Waiting {hours_pending:.0f} hours for your decision</p>
                          </div>
                          <div style="padding:24px 28px;background:#f9fafb;border:1px solid #e5e7eb">
                            <p><strong>Agent:</strong> {agent_name}<br>
                               <strong>Type:</strong> {approval_type}<br>
                               <strong>Brand:</strong> {brand_name}</p>
                            <pre style="background:#f3f4f6;padding:12px;border-radius:6px;font-size:12px;white-space:pre-wrap">{payload_preview}</pre>
                            <a href="{dashboard_url}" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#7c3aed;color:white;border-radius:6px;text-decoration:none;font-weight:600">
                              Review in Dashboard
                            </a>
                          </div>
                        </div>
                        """,
                    },
                )
                reminder_sent += 1
            except Exception as e:
                print(f"[Orchestrator] Reminder email failed ({approval_id}): {e}")

    # ------------------------------------------------------------------
    # 2. ROI classification
    # ------------------------------------------------------------------
    try:
        roi_channels = await get_roi_by_channel(pool, client_id, 30)
    except Exception as e:
        print(f"[Orchestrator] get_roi_by_channel failed for {client_name}: {e}")
        roi_channels = []

    below_target = []
    roi_status = {}

    for ch in roi_channels:
        channel = ch["channel"]
        roi = float(ch.get("roi") or 0)
        color = classify_roi(roi, roi_target)
        roi_status[channel] = {
            "roi": roi,
            "color": color,
            "spend": float(ch.get("total_spend") or 0),
            "revenue": float(ch.get("total_revenue") or 0),
        }
        if color in ("red", "black"):
            below_target.append({"channel": channel, "roi": roi, "color": color})

    if below_target:
        urgency = "urgent" if any(c["color"] == "black" for c in below_target) else "normal"
        try:
            await save_intelligence(
                pool,
                client_id,
                "roi_alert",
                {
                    "below_target_channels": below_target,
                    "roi_target": roi_target,
                    "brand": brand_name,
                },
                urgency=urgency,
            )
        except Exception as e:
            print(f"[Orchestrator] save_intelligence failed for {client_name}: {e}")

    # ------------------------------------------------------------------
    # 3. Save ROI snapshot (only if spend data exists)
    # ------------------------------------------------------------------
    if roi_channels:
        try:
            total_spend = sum(float(ch.get("total_spend") or 0) for ch in roi_channels)
            total_revenue = sum(float(ch.get("total_revenue") or 0) for ch in roi_channels)
            await save_roi_snapshot(
                pool,
                client_id,
                {
                    "total_spend": total_spend,
                    "total_revenue": total_revenue,
                    "platform_cost": 0.0,
                    "spend_by_channel": {ch["channel"]: float(ch.get("total_spend") or 0) for ch in roi_channels},
                    "revenue_by_channel": {ch["channel"]: float(ch.get("total_revenue") or 0) for ch in roi_channels},
                    "channels_below_target": {c["channel"]: c["roi"] for c in below_target},
                    "compounding_channels": {
                        ch["channel"]: float(ch.get("roi") or 0)
                        for ch in roi_channels
                        if classify_roi(float(ch.get("roi") or 0), roi_target) == "green"
                    },
                },
            )
        except Exception as e:
            print(f"[Orchestrator] save_roi_snapshot failed for {client_name}: {e}")

    # ------------------------------------------------------------------
    # 4. Log
    # ------------------------------------------------------------------
    duration_ms = int((time.time() - start) * 1000)
    summary = (
        f"Processed {len(pending)} approvals "
        f"({reminder_sent} reminders, {expired_count} expired). "
        f"{len(below_target)} channel(s) below ROI target."
    )
    print(f"[Orchestrator] {client_name}/{brand_name}: {summary}")
    try:
        await log_client_agent_action(
            pool,
            client_id,
            brand_id,
            "orchestrator",
            "approval_routing",
            summary,
            {
                "pending_count": len(pending),
                "reminder_sent": reminder_sent,
                "expired_count": expired_count,
                "below_target": below_target,
                "roi_status": roi_status,
            },
            status="completed",
            duration_ms=duration_ms,
        )
    except Exception as e:
        print(f"[Orchestrator] log failed for {client_name}: {e}")


# ---------------------------------------------------------------------------
# run_daily_briefing — Claude-generated daily email to client owner
# ---------------------------------------------------------------------------

async def run_daily_briefing(pool, client: dict, brand: dict) -> None:
    """Generate and email a daily briefing to the client owner (weekdays 07:30)."""
    start = time.time()
    client_id = str(client["id"])
    brand_id = str(brand["id"])
    client_name = client["name"]
    brand_name = brand["name"]
    owner_email = client.get("owner_email")
    roi_target = float(brand.get("roi_target_multiplier") or 3.0)
    dashboard_url = os.environ.get("APP_URL", "https://app.restaurantos.com")

    if not owner_email:
        print(f"[Orchestrator Briefing] No owner email for {client_name} — skipping")
        return

    # Gather inputs concurrently
    pending, roi_channels, intel_items = await asyncio.gather(
        get_pending_approvals(pool, client_id),
        get_roi_by_channel(pool, client_id, 30),
        get_recent_intelligence(pool, client_id, 5),
        return_exceptions=True,
    )
    if isinstance(pending, Exception):
        pending = []
    if isinstance(roi_channels, Exception):
        roi_channels = []
    if isinstance(intel_items, Exception):
        intel_items = []

    # Build ROI status dict
    roi_status = {}
    for ch in roi_channels:
        roi = float(ch.get("roi") or 0)
        roi_status[ch["channel"]] = {
            "roi": roi,
            "color": classify_roi(roi, roi_target),
            "spend": float(ch.get("total_spend") or 0),
            "revenue": float(ch.get("total_revenue") or 0),
        }

    # Build Claude input payload
    briefing_input = {
        "client_name": client_name,
        "brand_name": brand_name,
        "roi_target_multiplier": roi_target,
        "pending_approvals": [
            {
                "agent": a["agent_name"],
                "type": a["approval_type"],
                "hours_waiting": round(
                    (datetime.now(timezone.utc) - a["created_at"]).total_seconds() / 3600, 1
                ),
            }
            for a in pending
        ],
        "roi_status": roi_status,
        "recent_intelligence": [
            {"type": i["report_type"], "urgency": i["urgency"]}
            for i in intel_items
        ],
    }

    # Call Claude
    try:
        system_prompt = _load_prompt("orchestrator_briefing.txt")
        narrative = await asyncio.to_thread(
            _call_claude, system_prompt, json.dumps(briefing_input), 1500
        )
    except (json.JSONDecodeError, Exception) as e:
        print(f"[Orchestrator Briefing] Claude failed for {client_name}: {e}")
        # Fallback narrative
        narrative = {
            "headline": f"Your daily briefing — {client_name}",
            "pending_count": len(pending),
            "urgent_items": [],
            "recent_wins": [],
            "one_watch_item": "Check your dashboard for the latest updates.",
        }

    # Build email HTML
    pending_html = ""
    if narrative.get("pending_count", 0) > 0:
        pending_html = (
            f"<div style='background:#fef3c7;border-left:4px solid #f59e0b;"
            f"padding:12px 16px;margin-bottom:20px;border-radius:4px'>"
            f"<strong>{narrative['pending_count']} item(s) awaiting your approval.</strong>"
            f"</div>"
        )

    urgent_html = ""
    for item in narrative.get("urgent_items", []):
        urgent_html += f"<li style='color:#dc2626;margin-bottom:6px'>{item}</li>"
    if urgent_html:
        urgent_html = (
            f"<h3 style='color:#dc2626;margin-top:0'>Urgent</h3>"
            f"<ul style='padding-left:20px;margin:0 0 20px'>{urgent_html}</ul>"
        )

    wins_html = ""
    for win in narrative.get("recent_wins", []):
        wins_html += f"<li style='color:#16a34a;margin-bottom:6px'>{win}</li>"
    if wins_html:
        wins_html = (
            f"<h3 style='color:#16a34a;margin-top:0'>Recent Wins</h3>"
            f"<ul style='padding-left:20px;margin:0 0 20px'>{wins_html}</ul>"
        )

    watch_html = ""
    if narrative.get("one_watch_item"):
        watch_html = (
            f"<div style='background:#fff7ed;border-left:4px solid #f97316;"
            f"padding:12px 16px;margin-bottom:20px;border-radius:4px'>"
            f"<strong>Watch:</strong> {narrative['one_watch_item']}"
            f"</div>"
        )

    color_map = {"green": "#16a34a", "yellow": "#ca8a04", "red": "#dc2626", "black": "#111827"}
    roi_rows = ""
    for channel, data in roi_status.items():
        col = color_map.get(data["color"], "#6b7280")
        roi_rows += (
            f"<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb'>{channel}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;color:{col};font-weight:600'>{data['roi']:.2f}x</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb'>"
            f"<span style='background:{col}22;color:{col};padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600'>"
            f"{data['color'].upper()}</span></td>"
            f"</tr>"
        )
    roi_table_html = ""
    if roi_rows:
        roi_table_html = (
            f"<h3 style='margin-top:0'>ROI by Channel (Last 30 Days)</h3>"
            f"<table style='width:100%;border-collapse:collapse;margin-bottom:20px'>"
            f"<thead><tr>"
            f"<th style='text-align:left;padding:8px 12px;background:#f3f4f6;font-size:12px;color:#6b7280;text-transform:uppercase'>Channel</th>"
            f"<th style='text-align:left;padding:8px 12px;background:#f3f4f6;font-size:12px;color:#6b7280;text-transform:uppercase'>ROI</th>"
            f"<th style='text-align:left;padding:8px 12px;background:#f3f4f6;font-size:12px;color:#6b7280;text-transform:uppercase'>Status</th>"
            f"</tr></thead><tbody>{roi_rows}</tbody></table>"
        )

    html_body = f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
      <div style="max-width:600px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">
        <div style="background:#1e1b4b;color:white;padding:24px 32px">
          <h1 style="margin:0;font-size:20px;font-weight:600">Daily Briefing — {client_name}</h1>
          <p style="margin:6px 0 0;opacity:.7;font-size:13px">{brand_name}</p>
        </div>
        <div style="padding:28px 32px">
          <h2 style="margin:0 0 20px;color:#1e1b4b;font-size:17px">{narrative.get('headline', 'Your daily briefing')}</h2>
          {pending_html}
          {urgent_html}
          {wins_html}
          {roi_table_html}
          {watch_html}
          <a href="{dashboard_url}" style="display:inline-block;padding:12px 28px;background:#4f46e5;color:white;border-radius:6px;text-decoration:none;font-size:14px;font-weight:600">
            Open Dashboard
          </a>
        </div>
        <div style="padding:16px 32px;background:#f9fafb;border-top:1px solid #eeeeee;font-size:12px;color:#999;text-align:center">
          RestaurantOS Agents · Daily Briefing
        </div>
      </div>
    </body></html>
    """

    try:
        resend.api_key = os.environ.get("RESEND_API_KEY", "")
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": os.environ.get("FROM_EMAIL", "alerts@restaurantos.ai"),
                "to": [owner_email],
                "subject": f"Daily Briefing — {client_name} ({narrative.get('pending_count', 0)} pending)",
                "html": html_body,
            },
        )
        print(f"[Orchestrator Briefing] Sent to {owner_email} for {client_name}")
    except Exception as e:
        print(f"[Orchestrator Briefing] Email send failed for {client_name}: {e}")
        return

    duration_ms = int((time.time() - start) * 1000)
    try:
        await log_client_agent_action(
            pool,
            client_id,
            brand_id,
            "orchestrator",
            "daily_briefing_sent",
            f"Briefing sent to {owner_email}: {narrative.get('headline', '')}",
            {"pending_count": len(pending), "roi_channels": len(roi_channels)},
            status="completed",
            duration_ms=duration_ms,
        )
    except Exception as e:
        print(f"[Orchestrator Briefing] log failed for {client_name}: {e}")
