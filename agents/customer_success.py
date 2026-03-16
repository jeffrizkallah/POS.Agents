"""
agents/customer_success.py — Customer Success Agent

Responsibilities:
  1. check_restaurant_health(pool, restaurant_id, restaurant_name)
     - Scores each restaurant 0–100 across 4 engagement signals:
       login recency, order volume stability, food cost trend, recipe coverage
     - Returns { score, flags, risk_level, ... }
     - Logs result to agent_logs with action_type='health_check'
     - Runs daily at 08:00

  2. send_checkin_if_needed(pool, restaurant_id, restaurant_name, health)
     - at_risk  → personalised check-in email with 2–3 specific data points
     - churning → urgent email with a direct offer to help
     - ok       → no email sent
     - Logs email sent to agent_logs with action_type='checkin_email_sent'

  3. send_monthly_roi_summary_email(pool, restaurant_id, restaurant_name)
     - Computes monthly ROI metrics and sends a summary email to the manager
     - Runs on the 1st of each month at 09:00
     - Logs to agent_logs with action_type='roi_summary_sent'
"""

import os

from tools.database import (
    get_days_since_last_login,
    get_food_cost_trend_data,
    get_manager_email,
    get_monthly_roi_data,
    get_orders_count_last_week,
    get_orders_count_this_week,
    get_recipe_coverage_pct,
    log_agent_action,
)
from tools.email_sender import (
    send_checkin_email,
    send_monthly_roi_summary,
    send_urgent_alert,
)

AGENT_NAME = "customer_success_agent"

# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------
# Login recency        → 30 pts max
# Order stability      → 25 pts max
# Food cost trend      → 25 pts max
# Recipe coverage      → 20 pts max
#                         ─────────
#                         100 pts total
#
# Risk levels:
#   score >= 70 → ok
#   score >= 40 → at_risk
#   score <  40 → churning


# ---------------------------------------------------------------------------
# 5A — Engagement Monitor
# ---------------------------------------------------------------------------


async def check_restaurant_health(
    pool,
    restaurant_id: str,
    restaurant_name: str,
) -> dict:
    """Score a restaurant's platform engagement (0–100) across 4 signals.

    Returns:
        {
            score: int,
            flags: list[str],
            risk_level: "ok" | "at_risk" | "churning",
            days_since_login: float | None,
            orders_this_week: int,
            orders_last_week: int,
            order_drop_pct: float,
            food_cost_trend: str,
            current_fc_avg: float | None,
            prior_fc_avg: float | None,
            recipe_coverage_pct: float,
        }
    """
    flags = []
    score = 0

    # --- Signal 1: Login recency (30 pts) ---
    days_since_login = await get_days_since_last_login(pool, restaurant_id)

    if days_since_login is None:
        login_score = 15  # no data → neutral, don't penalise
    elif days_since_login < 3:
        login_score = 30
    elif days_since_login < 7:
        login_score = 20
    elif days_since_login < 14:
        login_score = 10
        flags.append("low_login_frequency")
    else:
        login_score = 0
        flags.append("inactive_logins")
    score += login_score

    # --- Signal 2: Order volume stability (25 pts) ---
    orders_this_week = await get_orders_count_this_week(pool, restaurant_id)
    orders_last_week = await get_orders_count_last_week(pool, restaurant_id)

    if orders_last_week > 0:
        drop_pct = (orders_last_week - orders_this_week) / orders_last_week * 100
        drop_pct = max(drop_pct, 0.0)  # ignore volume increases
    else:
        drop_pct = 0.0

    if drop_pct <= 10:
        order_score = 25
    elif drop_pct <= 20:
        order_score = 15
    else:
        order_score = 0
        flags.append("order_volume_drop")
    score += order_score

    # --- Signal 3: Food cost trend (25 pts) ---
    trend_data = await get_food_cost_trend_data(pool, restaurant_id)
    food_cost_trend = trend_data["trend"]
    current_fc_avg = trend_data["current_avg"]
    prior_fc_avg = trend_data["prior_avg"]

    if food_cost_trend == "improving":
        fc_score = 25
    elif food_cost_trend == "stable":
        fc_score = 20
    else:  # worsening
        fc_score = 5
        flags.append("food_cost_worsening")
    score += fc_score

    # --- Signal 4: Recipe coverage (20 pts) ---
    coverage_pct = await get_recipe_coverage_pct(pool, restaurant_id)

    if coverage_pct >= 50:
        coverage_score = 20
    else:
        coverage_score = 0
        flags.append("onboarding_incomplete")
    score += coverage_score

    # --- Risk level ---
    if score >= 70:
        risk_level = "ok"
    elif score >= 40:
        risk_level = "at_risk"
    else:
        risk_level = "churning"

    health = {
        "score": score,
        "flags": flags,
        "risk_level": risk_level,
        "days_since_login": days_since_login,
        "orders_this_week": orders_this_week,
        "orders_last_week": orders_last_week,
        "order_drop_pct": round(drop_pct, 1),
        "food_cost_trend": food_cost_trend,
        "current_fc_avg": current_fc_avg,
        "prior_fc_avg": prior_fc_avg,
        "recipe_coverage_pct": round(coverage_pct, 1),
    }

    await log_agent_action(
        pool=pool,
        restaurant_id=restaurant_id,
        agent_name=AGENT_NAME,
        action_type="health_check",
        summary=(
            f"{restaurant_name}: health score {score}/100 — {risk_level}. "
            f"Flags: {', '.join(flags) if flags else 'none'}."
        ),
        data=health,
        status="completed",
    )

    print(
        f"[CustomerSuccess] {restaurant_name}: score={score}/100, "
        f"risk={risk_level}, flags={flags or 'none'}"
    )
    return health


# ---------------------------------------------------------------------------
# 5B — Proactive Check-in Emails
# ---------------------------------------------------------------------------


async def send_checkin_if_needed(
    pool,
    restaurant_id: str,
    restaurant_name: str,
    health: dict,
) -> bool:
    """Send a proactive check-in email if risk_level is at_risk or churning.

    Returns True if an email was sent, False otherwise.
    """
    risk_level = health.get("risk_level", "ok")
    if risk_level == "ok":
        return False

    manager_email = await get_manager_email(pool, restaurant_id)
    if not manager_email:
        print(
            f"[CustomerSuccess] No manager email for {restaurant_name} — skipping check-in."
        )
        return False

    dashboard_url = os.environ.get("APP_URL", "https://app.restaurantos.com")
    insights = _build_insights(health)

    try:
        if risk_level == "at_risk":
            await send_checkin_email(
                to_email=manager_email,
                restaurant_name=restaurant_name,
                health=health,
                insights=insights,
                dashboard_url=dashboard_url,
            )
        else:  # churning
            message = (
                f"We noticed {restaurant_name} may need some attention. "
                f"Here's what we're seeing:\n\n"
                + "\n".join(f"• {i}" for i in insights)
                + "\n\nWe'd love to help you get the most out of RestaurantOS. "
                "Reply to this email or book a call with our team."
            )
            await send_urgent_alert(
                to_email=manager_email,
                restaurant_name=restaurant_name,
                subject="Your restaurant needs attention — we're here to help",
                message=message,
                dashboard_url=dashboard_url,
            )
    except Exception as e:
        print(f"[CustomerSuccess] Check-in email failed for {restaurant_name}: {e}")
        return False

    await log_agent_action(
        pool=pool,
        restaurant_id=restaurant_id,
        agent_name=AGENT_NAME,
        action_type="checkin_email_sent",
        summary=f"Proactive check-in email sent to {manager_email} ({risk_level}).",
        data={"risk_level": risk_level, "insights": insights, "email": manager_email},
        status="completed",
    )

    print(
        f"[CustomerSuccess] Check-in email sent for {restaurant_name} ({risk_level})."
    )
    return True


# ---------------------------------------------------------------------------
# 5C — Monthly ROI Summary Email
# ---------------------------------------------------------------------------


async def send_monthly_roi_summary_email(
    pool,
    restaurant_id: str,
    restaurant_name: str,
) -> bool:
    """Compute monthly ROI data and send summary email to the restaurant manager.

    Returns True if sent successfully, False otherwise.
    """
    manager_email = await get_manager_email(pool, restaurant_id)
    if not manager_email:
        print(
            f"[CustomerSuccess] No manager email for {restaurant_name} — skipping ROI summary."
        )
        return False

    roi_data = await get_monthly_roi_data(pool, restaurant_id)
    dashboard_url = os.environ.get("APP_URL", "https://app.restaurantos.com")

    try:
        await send_monthly_roi_summary(
            to_email=manager_email,
            restaurant_name=restaurant_name,
            roi_data=roi_data,
            dashboard_url=dashboard_url,
        )
    except Exception as e:
        print(f"[CustomerSuccess] ROI summary email failed for {restaurant_name}: {e}")
        return False

    await log_agent_action(
        pool=pool,
        restaurant_id=restaurant_id,
        agent_name=AGENT_NAME,
        action_type="roi_summary_sent",
        summary=(
            f"Monthly ROI summary sent to {manager_email} for "
            f"{roi_data.get('month_name', 'this month')}."
        ),
        data=roi_data,
        status="completed",
    )

    print(f"[CustomerSuccess] Monthly ROI summary sent for {restaurant_name}.")
    return True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_insights(health: dict) -> list[str]:
    """Build up to 3 human-readable insight bullets from health data."""
    insights = []

    # Login insight
    days = health.get("days_since_login")
    if days is not None and days >= 7:
        insights.append(
            f"No logins detected in the last {int(days)} day(s) — "
            f"your team may not be checking the dashboard regularly."
        )

    # Order volume insight
    drop_pct = health.get("order_drop_pct", 0)
    orders_last = health.get("orders_last_week", 0)
    orders_this = health.get("orders_this_week", 0)
    if drop_pct > 20:
        insights.append(
            f"Order volume dropped {drop_pct:.0f}% this week "
            f"({orders_this} orders vs {orders_last} last week)."
        )

    # Food cost insight
    fc_trend = health.get("food_cost_trend", "stable")
    current_fc = health.get("current_fc_avg")
    prior_fc = health.get("prior_fc_avg")
    if fc_trend == "worsening" and current_fc is not None and prior_fc is not None:
        insights.append(
            f"Food cost % has been worsening — currently {current_fc:.1f}% "
            f"vs {prior_fc:.1f}% two weeks ago. "
            f"Check your pricing recommendations in the dashboard."
        )

    # Recipe coverage insight
    coverage = health.get("recipe_coverage_pct", 100)
    if coverage < 50:
        insights.append(
            f"Only {coverage:.0f}% of your menu items have recipes linked — "
            f"food cost tracking is incomplete. Add recipes in the dashboard."
        )

    # Fallback if nothing specific triggered
    if not insights:
        score = health.get("score", 0)
        insights.append(
            f"Your platform engagement score is {score}/100. "
            f"We'd love to help you get more value from RestaurantOS."
        )

    return insights[:3]
