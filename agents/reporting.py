"""Reporting & Analytics Agent (Phase 6L).

Runs every Monday at 06:00 UTC. Computes 40+ metrics per restaurant,
generates Claude-narrated analytics reports, sends them to each owner,
then produces an internal platform intelligence briefing.
"""

import asyncio
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import anthropic
import asyncpg

from tools.database import (
    get_active_clients,
    get_manager_email,
    log_agent_action,
    mark_report_sent,
    upsert_platform_weekly_summary,
)
from tools.report_builder import build_report_package
from tools.metrics.platform_metrics import get_platform_metrics, get_client_league_table
from tools.email_sender import send_analytics_report, send_platform_intelligence


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_reporting_agent(pool: asyncpg.Pool) -> None:
    """Run the full Monday reporting pipeline.

    Phase 1: Per-restaurant analytics reports.
    Phase 2: Platform-wide intelligence briefing.
    """
    start_time = time.time()

    # --- Calculate week window ---
    # week_end = yesterday (most recent complete day); week_start = 7 days prior
    today = date.today()
    week_end = today - timedelta(days=1)
    week_start = week_end - timedelta(days=6)

    print(
        f"[Reporting] Starting weekly run for {week_start} → {week_end}"
    )

    dashboard_url = os.environ.get("APP_URL", "https://app.restaurantos.com")
    analytics_prompt = _load_prompt("analytics_narrator.txt")
    platform_prompt = _load_prompt("platform_intelligence.txt")

    clients = await get_active_clients(pool)
    print(f"[Reporting] Phase 1 — processing {len(clients)} restaurant(s)")

    reports_sent = 0
    total_anomalies = 0
    total_revenue = 0.0

    # -----------------------------------------------------------------------
    # Phase 1: Per-restaurant reports
    # -----------------------------------------------------------------------
    for restaurant in clients:
        restaurant_id = str(restaurant["id"])
        restaurant_name = restaurant["name"]

        try:
            # Build full metrics package
            package = await build_report_package(
                pool, restaurant_id, restaurant_name, week_start, week_end
            )
            if not package:
                print(f"[Reporting] Skipping {restaurant_name} — empty package")
                continue

            total_revenue += package.get("revenue", {}).get("gross_revenue", 0)
            total_anomalies += len(package.get("anomalies", []))

            # Call Claude to narrate the report
            narrative = await _call_claude_narrator(analytics_prompt, package)
            if not narrative:
                print(f"[Reporting] Skipping {restaurant_name} — Claude narrative failed")
                continue

            # Fetch owner email
            manager_email = await get_manager_email(pool, restaurant_id)
            if not manager_email:
                print(f"[Reporting] No email found for {restaurant_name} — skipping send")
            else:
                await send_analytics_report(
                    to_email=manager_email,
                    restaurant_name=restaurant_name,
                    report_package=package,
                    narrative=narrative,
                    dashboard_url=dashboard_url,
                )
                reports_sent += 1

            # Mark snapshot as report_sent
            await mark_report_sent(pool, restaurant_id, week_start)

            # Log to agent_logs
            await log_agent_action(
                pool=pool,
                restaurant_id=restaurant_id,
                agent_name="reporting_agent",
                action_type="analytics_report_sent",
                summary=(
                    f"Weekly analytics report for {restaurant_name}: "
                    f"AED {package['revenue']['gross_revenue']:,.0f} revenue, "
                    f"{len(package['anomalies'])} anomaly(ies)"
                ),
                data={
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat(),
                    "gross_revenue": package["revenue"]["gross_revenue"],
                    "food_cost_pct": package["food_cost"]["food_cost_pct"],
                    "anomaly_count": len(package["anomalies"]),
                    "email_sent": manager_email is not None,
                },
                status="completed",
            )

            print(
                f"[Reporting] {restaurant_name}: "
                f"AED {package['revenue']['gross_revenue']:,.0f} revenue, "
                f"{len(package['anomalies'])} anomaly(ies)"
            )

            # Rate-limit between clients to avoid thundering herd
            await asyncio.sleep(3)

        except Exception as e:
            print(f"[Reporting] Failed for {restaurant_name}: {e}")
            try:
                await log_agent_action(
                    pool=pool,
                    restaurant_id=restaurant_id,
                    agent_name="reporting_agent",
                    action_type="analytics_report_failed",
                    summary=f"Report generation failed for {restaurant_name}: {e}",
                    data={"error": str(e), "week_start": week_start.isoformat()},
                    status="failed",
                )
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # Phase 2: Platform intelligence
    # -----------------------------------------------------------------------
    print("[Reporting] Phase 2 — building platform intelligence")
    try:
        platform_metrics = await get_platform_metrics(pool, week_start, week_end)
        league_table = await get_client_league_table(pool, week_start, week_end)

        # Upsert to platform_weekly_summaries
        await upsert_platform_weekly_summary(pool, week_start, week_end, platform_metrics)

        # Call Claude for platform narrative
        platform_narrative = await _call_claude_platform(
            platform_prompt, platform_metrics, league_table, week_start, week_end
        )

        # Send to platform report email
        platform_email = os.environ.get("PLATFORM_REPORT_EMAIL")
        if platform_email and platform_narrative:
            await send_platform_intelligence(
                to_email=platform_email,
                platform_narrative=platform_narrative,
                platform_metrics=platform_metrics,
                league_table=league_table,
                week_start=week_start.isoformat(),
                week_end=week_end.isoformat(),
            )
            print(f"[Reporting] Platform intelligence sent to {platform_email}")
        else:
            if not platform_email:
                print("[Reporting] PLATFORM_REPORT_EMAIL not set — skipping platform email")

        await log_agent_action(
            pool=pool,
            restaurant_id=None,
            agent_name="reporting_agent",
            action_type="platform_intelligence_sent",
            summary=(
                f"Platform intelligence for {week_start}: "
                f"{platform_metrics.get('total_active_clients', 0)} clients, "
                f"AED {platform_metrics.get('total_platform_revenue', 0):,.0f} platform revenue"
            ),
            data={
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                **{k: v for k, v in platform_metrics.items() if not isinstance(v, dict)},
            },
            status="completed",
        )

    except Exception as e:
        print(f"[Reporting] Phase 2 platform intelligence failed: {e}")

    # -----------------------------------------------------------------------
    # Final summary log
    # -----------------------------------------------------------------------
    runtime_secs = round(time.time() - start_time, 1)
    summary = (
        f"Weekly run complete: {reports_sent}/{len(clients)} reports sent, "
        f"AED {total_revenue:,.0f} total revenue, "
        f"{total_anomalies} anomalies detected, "
        f"{runtime_secs}s runtime"
    )
    print(f"[Reporting] {summary}")

    await log_agent_action(
        pool=pool,
        restaurant_id=None,
        agent_name="reporting_agent",
        action_type="weekly_run_complete",
        summary=summary,
        data={
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "reports_sent": reports_sent,
            "total_clients": len(clients),
            "total_revenue": total_revenue,
            "total_anomalies": total_anomalies,
            "runtime_secs": runtime_secs,
        },
        status="completed",
    )


# ---------------------------------------------------------------------------
# Claude helpers
# ---------------------------------------------------------------------------

def _load_prompt(filename: str) -> str:
    """Load a prompt file from the prompts/ directory."""
    path = Path(__file__).parent.parent / "prompts" / filename
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[Reporting] Failed to load prompt {filename}: {e}")
        return ""


async def _call_claude_narrator(system_prompt: str, package: dict) -> dict:
    """Call Claude with the analytics narrator prompt. Returns parsed JSON dict or {}."""
    if not system_prompt:
        return {}

    # Build a concise user message with the key metrics
    revenue = package.get("revenue", {})
    food_cost = package.get("food_cost", {})
    inventory = package.get("inventory", {})
    menu = package.get("menu", {})
    ops = package.get("ops", {})
    anomalies = package.get("anomalies", [])
    benchmarks = package.get("benchmark_comparisons", {})
    prev = package.get("previous_week") or {}

    user_message = f"""Restaurant: {package.get('restaurant_name')}
Week: {package.get('week_start')} to {package.get('week_end')}

REVENUE:
- Gross revenue: AED {revenue.get('gross_revenue', 0):,.2f}
- Total covers: {revenue.get('total_covers', 0)}
- Avg spend/cover: AED {revenue.get('avg_spend_per_cover', 0):.2f}
- Revenue WoW: {revenue.get('revenue_wow_pct', 0):+.1f}%
- Revenue MoM: {revenue.get('revenue_mom_pct', 0):+.1f}%
- Peak hour: {revenue.get('peak_hour', 'N/A')}:00 (AED {revenue.get('peak_hour_revenue', 0):,.0f})
- Void rate: {revenue.get('void_rate_pct', 0):.1f}%

FOOD COST:
- Avg food cost %: {food_cost.get('food_cost_pct', 0):.1f}%
- Trend: {food_cost.get('food_cost_trend', 'stable')}
- Top margin killer: {food_cost.get('top_margin_killer_name', 'N/A')} ({food_cost.get('top_margin_killer_pct', 0):.1f}%)
- Top star dish: {food_cost.get('top_star_dish_name', 'N/A')} ({food_cost.get('top_star_dish_pct', 0):.1f}%)
- Estimated margin loss: AED {food_cost.get('estimated_margin_loss', 0):,.2f}
- Pricing agent recovery: AED {food_cost.get('pricing_agent_recovery', 0):,.2f}

INVENTORY:
- Waste rate: {inventory.get('waste_rate_pct', 0):.1f}%
- Waste qty: {inventory.get('waste_qty', 0):.1f} units ({inventory.get('waste_event_count', 0)} events)
- Stock-outs: {inventory.get('stock_out_count', 0)} ingredients at zero
- Avg days stock cover: {inventory.get('avg_days_stock_cover') or 'N/A'}
- PO cycle time: {inventory.get('po_cycle_time_days') or 'N/A'} days

MENU:
- Top dish: {menu.get('top_dish_name', 'N/A')} ({menu.get('top_dish_count', 0)} orders)
- Star-to-dog ratio: {menu.get('star_to_dog_ratio', 0):.2f} (target: 0.70)
- Attachment rate: {menu.get('attachment_rate', 0):.2f} (target: 0.60)

OPS:
- Table turn rate: {ops.get('table_turn_rate', 0):.2f}x/day (target: 2.5x)
- Recommendation action rate: {ops.get('recommendation_action_rate', 0):.1f}%
- Agent runs this week: {ops.get('agent_run_count', 0)}

BENCHMARK COMPARISONS:
- Food cost: {food_cost.get('food_cost_pct', 0):.1f}% vs {benchmarks.get('food_cost_pct', {}).get('benchmark', 30):.0f}% benchmark
- Waste rate: {inventory.get('waste_rate_pct', 0):.1f}% vs {benchmarks.get('waste_rate_pct', {}).get('benchmark', 5):.0f}% benchmark
- Avg spend/cover: AED {revenue.get('avg_spend_per_cover', 0):.2f} vs AED {benchmarks.get('avg_spend_per_cover', {}).get('benchmark', 28):.0f} benchmark
- Table turn: {ops.get('table_turn_rate', 0):.2f}x vs {benchmarks.get('table_turn_rate', {}).get('benchmark', 2.5):.1f}x benchmark

ANOMALIES DETECTED ({len(anomalies)}):
{_format_anomalies(anomalies)}

PREVIOUS WEEK COMPARISON:
- Prev revenue: AED {prev.get('gross_revenue', 0):,.0f}
- Prev food cost %: {prev.get('food_cost_pct', 0):.1f}%
- Prev waste rate: {prev.get('waste_rate_pct', 0):.1f}%

Generate the weekly analytics report narrative now."""

    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        return _parse_json_response(raw, "analytics_narrator")
    except Exception as e:
        print(f"[Reporting] Claude narrator call failed: {e}")
        return {}


async def _call_claude_platform(
    system_prompt: str,
    platform_metrics: dict,
    league_table: list,
    week_start: date,
    week_end: date,
) -> dict:
    """Call Claude with the platform intelligence prompt. Returns parsed JSON dict or {}."""
    if not system_prompt:
        return {}

    league_text = "\n".join(
        f"  {i+1}. {c.get('restaurant_name')}: AED {c.get('gross_revenue', 0):,.0f} revenue, "
        f"{c.get('food_cost_pct', 0):.1f}% FC, {c.get('recommendation_action_rate', 0):.0f}% action rate"
        for i, c in enumerate(league_table[:5])
    ) or "  No revenue data this week."

    clients_by_band = platform_metrics.get("clients_by_band", {})
    band_text = ", ".join(f"{k}: {v}" for k, v in clients_by_band.items()) or "No health data"

    user_message = f"""Week: {week_start} to {week_end}

PLATFORM METRICS:
- Active clients: {platform_metrics.get('total_active_clients', 0)}
- Total MRR: AED {platform_metrics.get('total_mrr', 0):,.0f}
- MRR at risk: AED {platform_metrics.get('mrr_at_risk', 0):,.0f}
- Avg client health score: {platform_metrics.get('avg_client_health', 0):.1f}/100
- Clients by health band: {band_text}
- New clients this week: {platform_metrics.get('new_clients_this_week', 0)}
- Churned this week: {platform_metrics.get('churned_this_week', 0)}
- Total platform revenue: AED {platform_metrics.get('total_platform_revenue', 0):,.0f}
- Total covers processed: {platform_metrics.get('total_platform_covers', 0):,}
- Avg food cost %: {platform_metrics.get('avg_food_cost_pct', 0):.1f}%
- Total agent runs: {platform_metrics.get('agent_total_runs', 0)}
- Feature adoption: {platform_metrics.get('feature_adoption_pct', 0):.1f}%

CLIENT LEAGUE TABLE (top 5 by revenue):
{league_text}

Generate the platform intelligence briefing now."""

    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        return _parse_json_response(raw, "platform_intelligence")
    except Exception as e:
        print(f"[Reporting] Claude platform call failed: {e}")
        return {}


def _format_anomalies(anomalies: list) -> str:
    if not anomalies:
        return "  None detected."
    return "\n".join(
        f"  - [{a.get('severity', 'info').upper()}] {a.get('anomaly_type', '?')}: {a.get('description', '')[:120]}"
        for a in anomalies
    )


def _parse_json_response(raw: str, context: str) -> dict:
    """Strip optional markdown fences and parse JSON from Claude response."""
    text = raw
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[Reporting] JSON parse failed ({context}): {e} — raw: {raw[:200]}")
        return {}
