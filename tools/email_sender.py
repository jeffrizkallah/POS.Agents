"""
tools/email_sender.py

Sends HTML emails via the Resend API.
All functions are async (use asyncio.to_thread to wrap the sync Resend SDK).
"""

import asyncio
import os
from typing import Optional
import resend


def _get_from_email() -> str:
    return os.environ.get("FROM_EMAIL", "alerts@restaurantos.ai")


def _base_styles() -> str:
    return """
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: #f5f5f5; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 32px auto; background: #ffffff;
                     border-radius: 8px; overflow: hidden;
                     box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .header { background: #1a1a2e; color: #ffffff; padding: 24px 32px; }
        .header h1 { margin: 0; font-size: 20px; font-weight: 600; }
        .header p  { margin: 4px 0 0; font-size: 13px; color: #aaaacc; }
        .body { padding: 28px 32px; color: #333333; }
        .body h2 { margin: 0 0 16px; font-size: 17px; color: #111111; }
        .body p  { margin: 0 0 16px; font-size: 14px; line-height: 1.6; }
        table.items { width: 100%; border-collapse: collapse; margin: 0 0 24px; }
        table.items th { background: #f0f0f5; text-align: left;
                         padding: 8px 12px; font-size: 12px;
                         color: #666; text-transform: uppercase; }
        table.items td { padding: 10px 12px; font-size: 14px;
                         border-bottom: 1px solid #eeeeee; }
        .badge-urgent { background: #fee2e2; color: #dc2626;
                        padding: 2px 8px; border-radius: 12px;
                        font-size: 12px; font-weight: 600; }
        .badge-ok     { background: #d1fae5; color: #059669;
                        padding: 2px 8px; border-radius: 12px;
                        font-size: 12px; }
        .btn { display: inline-block; padding: 12px 28px;
               background: #4f46e5; color: #ffffff; text-decoration: none;
               border-radius: 6px; font-size: 14px; font-weight: 600;
               margin-top: 8px; }
        .footer { padding: 16px 32px; background: #f9f9f9;
                  font-size: 12px; color: #999999;
                  border-top: 1px solid #eeeeee; text-align: center; }
    </style>
    """


# ---------------------------------------------------------------------------
# 2A — Low Stock Alert
# ---------------------------------------------------------------------------

async def send_low_stock_alert(
    to_email: str,
    restaurant_name: str,
    items: list[dict],
    dashboard_url: str,
) -> None:
    """
    Send an email listing all low-stock ingredients with an "Approve Orders" button.

    Each item dict should contain:
        name, unit, stock_qty, reorder_point, recommended_qty, days_remaining (optional)
    """
    approve_url = f"{dashboard_url}/dashboard/purchase-orders"

    rows_html = ""
    for item in items:
        days = item.get("days_remaining")
        if days is not None and days < 1:
            urgency_badge = '<span class="badge-urgent">⚠️ Urgent</span>'
        elif days is not None and days < 2:
            urgency_badge = '<span class="badge-urgent">Low</span>'
        else:
            urgency_badge = '<span class="badge-ok">OK</span>'

        days_str = f"{days:.1f}d" if days is not None else "—"
        rows_html += f"""
        <tr>
            <td><strong>{item['name']}</strong></td>
            <td>{item.get('stock_qty', '—')} {item.get('unit', '')}</td>
            <td>{item.get('reorder_point', '—')} {item.get('unit', '')}</td>
            <td>{item.get('recommended_qty', '—')} {item.get('unit', '')}</td>
            <td>{days_str}</td>
            <td>{urgency_badge}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>{_base_styles()}</head>
<body>
<div class="container">
  <div class="header">
    <h1>RestaurantOS</h1>
    <p>{restaurant_name} — Low Stock Alert</p>
  </div>
  <div class="body">
    <h2>{len(items)} item{"s" if len(items) != 1 else ""} need{"s" if len(items) == 1 else ""} restocking</h2>
    <p>The following ingredients have fallen below their reorder points.
       Draft purchase orders have been created and are ready for your approval.</p>
    <table class="items">
      <thead>
        <tr>
          <th>Ingredient</th>
          <th>In Stock</th>
          <th>Reorder Point</th>
          <th>Order Qty</th>
          <th>Days Left</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    <a class="btn" href="{approve_url}">Review &amp; Approve Orders →</a>
  </div>
  <div class="footer">
    RestaurantOS · Automated Inventory Agent · <a href="{dashboard_url}">Open Dashboard</a>
  </div>
</div>
</body>
</html>"""

    subject = f"{restaurant_name}: {len(items)} purchase order{'s' if len(items) != 1 else ''} need approval"
    await _send(to_email, subject, html)


# ---------------------------------------------------------------------------
# 2B — Weekly Report
# ---------------------------------------------------------------------------

async def send_weekly_report(
    to_email: str,
    restaurant_name: str,
    report_data: dict,
    dashboard_url: str,
) -> None:
    """
    Send a weekly margin / waste summary.

    report_data keys (all optional, shown as '—' if missing):
        total_sales, order_count, food_cost_pct, target_food_cost_pct,
        total_waste_cost, top_waste_item, purchase_orders_approved,
        purchase_orders_pending, top_items (list of {name, count})
    """
    sales = report_data.get("total_sales", "—")
    orders = report_data.get("order_count", "—")
    fcp = report_data.get("food_cost_pct")
    target_fcp = report_data.get("target_food_cost_pct", 30)
    waste = report_data.get("total_waste_cost", "—")
    top_waste = report_data.get("top_waste_item", "—")
    po_approved = report_data.get("purchase_orders_approved", "—")
    po_pending = report_data.get("purchase_orders_pending", "—")
    top_items = report_data.get("top_items", [])

    fcp_str = f"{fcp:.1f}%" if fcp is not None else "—"
    fcp_color = "#dc2626" if (fcp is not None and fcp > target_fcp) else "#059669"

    top_items_html = ""
    for i, item in enumerate(top_items[:5], 1):
        top_items_html += f"<tr><td>{i}.</td><td>{item['name']}</td><td>{item.get('count', '—')} orders</td></tr>"

    html = f"""<!DOCTYPE html>
<html>
<head>{_base_styles()}</head>
<body>
<div class="container">
  <div class="header">
    <h1>RestaurantOS</h1>
    <p>{restaurant_name} — Weekly Performance Summary</p>
  </div>
  <div class="body">
    <h2>This week at a glance</h2>
    <table class="items">
      <tbody>
        <tr><td>Total Sales</td><td><strong>{sales}</strong></td></tr>
        <tr><td>Orders Processed</td><td><strong>{orders}</strong></td></tr>
        <tr><td>Food Cost %</td><td><strong style="color:{fcp_color}">{fcp_str}</strong> (target: {target_fcp}%)</td></tr>
        <tr><td>Total Waste Cost</td><td><strong>{waste}</strong></td></tr>
        <tr><td>Top Waste Item</td><td>{top_waste}</td></tr>
        <tr><td>Purchase Orders Approved</td><td>{po_approved}</td></tr>
        <tr><td>Purchase Orders Pending</td><td>{po_pending}</td></tr>
      </tbody>
    </table>
    {"<h2>Top 5 Menu Items</h2><table class='items'><tbody>" + top_items_html + "</tbody></table>" if top_items else ""}
    <a class="btn" href="{dashboard_url}/dashboard">View Full Report →</a>
  </div>
  <div class="footer">
    RestaurantOS · Automated Reporting Agent · <a href="{dashboard_url}">Open Dashboard</a>
  </div>
</div>
</body>
</html>"""

    subject = f"{restaurant_name}: Weekly Performance Summary"
    await _send(to_email, subject, html)


# ---------------------------------------------------------------------------
# 2C — Urgent Alert
# ---------------------------------------------------------------------------

async def send_urgent_alert(
    to_email: str,
    restaurant_name: str,
    subject: str,
    message: str,
    dashboard_url: str,
) -> None:
    """Send a plain urgent alert for critical issues (stockout imminent, waste spike, etc.)."""
    html = f"""<!DOCTYPE html>
<html>
<head>{_base_styles()}</head>
<body>
<div class="container">
  <div class="header" style="background:#7f1d1d;">
    <h1>⚠️ RestaurantOS Alert</h1>
    <p>{restaurant_name}</p>
  </div>
  <div class="body">
    <h2>{subject}</h2>
    <p style="white-space:pre-line;">{message}</p>
    <a class="btn" href="{dashboard_url}/dashboard" style="background:#dc2626;">
      Open Dashboard →
    </a>
  </div>
  <div class="footer">
    RestaurantOS · Automated Agent · <a href="{dashboard_url}">Open Dashboard</a>
  </div>
</div>
</body>
</html>"""

    await _send(to_email, f"[URGENT] {restaurant_name}: {subject}", html)


# ---------------------------------------------------------------------------
# 2D — Monthly ROI Summary
# ---------------------------------------------------------------------------

async def send_monthly_roi_summary(
    to_email: str,
    restaurant_name: str,
    roi_data: dict,
    dashboard_url: str,
) -> None:
    """
    Send the monthly ROI summary on the 1st of each month.

    roi_data keys (all optional):
        total_orders, total_waste_cost_saved, purchase_orders_approved,
        estimated_hours_saved, food_cost_improvement_pct, month_name
    """
    month = roi_data.get("month_name", "Last Month")
    total_orders = roi_data.get("total_orders", "—")
    waste_saved = roi_data.get("total_waste_cost_saved", "—")
    po_approved = roi_data.get("purchase_orders_approved", "—")
    hours_saved = roi_data.get("estimated_hours_saved", "—")
    fc_improvement = roi_data.get("food_cost_improvement_pct")

    fc_str = f"{fc_improvement:+.1f}%" if fc_improvement is not None else "—"

    html = f"""<!DOCTYPE html>
<html>
<head>{_base_styles()}</head>
<body>
<div class="container">
  <div class="header" style="background:#1e3a5f;">
    <h1>RestaurantOS</h1>
    <p>{restaurant_name} — Monthly ROI Summary · {month}</p>
  </div>
  <div class="body">
    <h2>Here's what RestaurantOS did for you this month</h2>
    <table class="items">
      <tbody>
        <tr><td>Orders Processed</td><td><strong>{total_orders}</strong></td></tr>
        <tr><td>Estimated Waste Cost Saved</td><td><strong>{waste_saved}</strong></td></tr>
        <tr><td>Purchase Orders Approved</td><td><strong>{po_approved}</strong></td></tr>
        <tr><td>Estimated Hours Saved</td><td><strong>{hours_saved} hrs</strong></td></tr>
        <tr><td>Food Cost % Change</td><td><strong>{fc_str}</strong></td></tr>
      </tbody>
    </table>
    <p>Keep it up! Your agents are running 24/7 to keep your kitchen profitable.</p>
    <a class="btn" href="{dashboard_url}/dashboard/reports">View Full Report →</a>
  </div>
  <div class="footer">
    RestaurantOS · Monthly Summary · <a href="{dashboard_url}">Open Dashboard</a>
  </div>
</div>
</body>
</html>"""

    subject = f"{restaurant_name}: Monthly ROI Summary — {month}"
    await _send(to_email, subject, html)


# ---------------------------------------------------------------------------
# 5B — Customer Success Check-in Email
# ---------------------------------------------------------------------------

async def send_checkin_email(
    to_email: str,
    restaurant_name: str,
    health: dict,
    insights: list,
    dashboard_url: str,
) -> None:
    """Send a proactive at-risk check-in email with specific data points.

    health must contain: score, risk_level, flags.
    insights is a list of human-readable bullet strings (2-3 items).
    """
    score = health.get("score", 0)

    insights_html = "".join(
        f"""<div style="padding:10px 14px;border-left:3px solid #f59e0b;
            background:#fffbeb;margin-bottom:10px;border-radius:0 6px 6px 0;
            font-size:14px;line-height:1.5;">{insight}</div>"""
        for insight in insights
    )

    html = f"""<!DOCTYPE html>
<html>
<head>{_base_styles()}</head>
<body>
<div class="container">
  <div class="header" style="background:#78350f;">
    <h1>RestaurantOS</h1>
    <p>{restaurant_name} — Platform Check-in</p>
  </div>
  <div class="body">
    <h2>Hi — just checking in on {restaurant_name}</h2>
    <p>Your RestaurantOS health score is <strong>{score}/100</strong>.
       Here's what we're seeing:</p>
    {insights_html}
    <p style="margin-top:20px;">
      We're here to help you get the most out of the platform.
      If you have any questions or need a hand, just reply to this email.
    </p>
    <a class="btn" href="{dashboard_url}/dashboard" style="background:#d97706;">
      Open Dashboard →
    </a>
  </div>
  <div class="footer">
    RestaurantOS · Customer Success · <a href="{dashboard_url}">Open Dashboard</a>
  </div>
</div>
</body>
</html>"""

    subject = f"{restaurant_name}: A quick check-in from RestaurantOS"
    await _send(to_email, subject, html)


# ---------------------------------------------------------------------------
# 6K — Analytics Report Email
# ---------------------------------------------------------------------------

async def send_analytics_report(
    to_email: str,
    restaurant_name: str,
    report_package: dict,
    narrative: dict,
    dashboard_url: str,
) -> None:
    """Send the full weekly analytics report email to a restaurant owner/manager.

    report_package: output of build_report_package()
    narrative: parsed JSON from Claude analytics_narrator prompt
    """
    week_start = report_package.get("week_start", "")
    week_end = report_package.get("week_end", "")
    revenue = report_package.get("revenue", {})
    food_cost = report_package.get("food_cost", {})
    inventory = report_package.get("inventory", {})
    menu = report_package.get("menu", {})
    benchmarks = report_package.get("benchmark_comparisons", {})
    anomalies = report_package.get("anomalies", [])

    # Anomaly cards
    severity_styles = {
        "critical": ("border-left:4px solid #dc2626;background:#fef2f2;", "#dc2626"),
        "warning":  ("border-left:4px solid #f59e0b;background:#fffbeb;", "#d97706"),
        "info":     ("border-left:4px solid #3b82f6;background:#eff6ff;", "#2563eb"),
    }
    anomaly_cards_html = ""
    for a in narrative.get("anomaly_highlights", []):
        sev = a.get("severity", "info")
        style, label_color = severity_styles.get(sev, severity_styles["info"])
        anomaly_cards_html += f"""
        <div style="padding:14px 16px;margin-bottom:12px;border-radius:6px;{style}">
            <div style="font-weight:700;font-size:14px;color:{label_color};margin-bottom:4px;">
                {sev.upper()}: {a.get('title', '')}
            </div>
            <div style="font-size:14px;color:#374151;margin-bottom:6px;">{a.get('description', '')}</div>
            <div style="font-size:13px;color:#6b7280;"><strong>Action:</strong> {a.get('action', '')}</div>
        </div>"""

    # 4 metric cards (2×2 grid)
    def _metric_card(title: str, value: str, subtitle: str, color: str = "#4f46e5") -> str:
        return f"""
        <td style="width:50%;padding:8px;">
            <div style="background:#f9fafb;border-radius:8px;padding:16px;
                        border-top:3px solid {color};">
                <div style="font-size:12px;color:#6b7280;text-transform:uppercase;
                             letter-spacing:.05em;margin-bottom:4px;">{title}</div>
                <div style="font-size:22px;font-weight:700;color:#111827;">{value}</div>
                <div style="font-size:12px;color:#6b7280;margin-top:4px;">{subtitle}</div>
            </div>
        </td>"""

    gross_rev = revenue.get("gross_revenue", 0)
    wow_pct = revenue.get("revenue_wow_pct", 0)
    wow_sign = "+" if wow_pct >= 0 else ""
    wow_color = "#059669" if wow_pct >= 0 else "#dc2626"

    fc_pct = food_cost.get("food_cost_pct", 0)
    fc_trend = food_cost.get("food_cost_trend", "stable")
    trend_icons = {"improving": "↓ improving", "deteriorating": "↑ worsening", "stable": "→ stable"}

    waste_rate = inventory.get("waste_rate_pct", 0)
    top_dish = menu.get("top_dish_name", "—")
    top_dish_count = menu.get("top_dish_count", 0)

    fc_color = "#dc2626" if fc_pct > 30 else "#059669"

    metric_cards_html = f"""
    <table cellpadding="0" cellspacing="0" width="100%"><tbody>
        <tr>
            {_metric_card("Revenue", f"AED {gross_rev:,.0f}", f'<span style="color:{wow_color}">{wow_sign}{wow_pct:.1f}% vs last week</span>')}
            {_metric_card("Food Cost %", f'<span style="color:{fc_color}">{fc_pct:.1f}%</span>', trend_icons.get(fc_trend, fc_trend), "#f59e0b")}
        </tr>
        <tr>
            {_metric_card("Waste Rate", f"{waste_rate:.1f}%", "of total throughput", "#6366f1")}
            {_metric_card("Top Dish", top_dish, f"{top_dish_count} orders this week", "#10b981")}
        </tr>
    </tbody></table>"""

    # Benchmark comparison section
    def _bench_row(label: str, key: str, unit: str = "", lower_better: bool = False) -> str:
        comp = benchmarks.get(key, {})
        val = comp.get("value", 0)
        bench = comp.get("benchmark", 0)
        vs = comp.get("vs_benchmark", 0)
        better = comp.get("better_than_benchmark", False)
        icon = "✓" if better else "✗"
        color = "#059669" if better else "#dc2626"
        vs_sign = "+" if vs >= 0 else ""
        return f"""
        <tr>
            <td style="padding:8px 0;font-size:14px;color:#374151;">{label}</td>
            <td style="padding:8px 0;font-size:14px;font-weight:600;">{val:.1f}{unit}</td>
            <td style="padding:8px 0;font-size:14px;color:#9ca3af;">{bench:.1f}{unit}</td>
            <td style="padding:8px 0;font-size:13px;color:{color};font-weight:600;">
                {icon} {vs_sign}{vs:.1f}{unit}
            </td>
        </tr>"""

    bench_html = f"""
    <table cellpadding="0" cellspacing="0" width="100%" style="margin-top:8px;">
        <thead>
            <tr style="border-bottom:2px solid #e5e7eb;">
                <th style="text-align:left;padding:8px 0;font-size:12px;color:#6b7280;text-transform:uppercase;">Metric</th>
                <th style="text-align:left;padding:8px 0;font-size:12px;color:#6b7280;text-transform:uppercase;">Actual</th>
                <th style="text-align:left;padding:8px 0;font-size:12px;color:#6b7280;text-transform:uppercase;">Benchmark</th>
                <th style="text-align:left;padding:8px 0;font-size:12px;color:#6b7280;text-transform:uppercase;">Gap</th>
            </tr>
        </thead>
        <tbody>
            {_bench_row("Food Cost %", "food_cost_pct", "%", lower_better=True)}
            {_bench_row("Waste Rate %", "waste_rate_pct", "%", lower_better=True)}
            {_bench_row("Avg Spend / Cover", "avg_spend_per_cover", " AED")}
            {_bench_row("Table Turn Rate", "table_turn_rate", "×")}
        </tbody>
    </table>"""

    anomaly_section = f"""
    <div style="margin:24px 0;">
        <h3 style="font-size:15px;color:#111827;margin:0 0 12px;">This Week's Alerts</h3>
        {anomaly_cards_html}
    </div>""" if anomaly_cards_html else ""

    top_rec = narrative.get("top_recommendation", "")
    top_rec_html = f"""
    <div style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:8px;
                padding:16px;margin:24px 0;">
        <div style="font-size:12px;color:#4f46e5;font-weight:700;text-transform:uppercase;
                    letter-spacing:.05em;margin-bottom:6px;">Top Recommendation</div>
        <div style="font-size:14px;color:#1e1b4b;line-height:1.6;">{top_rec}</div>
    </div>""" if top_rec else ""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f3f4f6; margin: 0; padding: 0; }}
.container {{ max-width: 640px; margin: 32px auto; background: #ffffff;
             border-radius: 10px; overflow: hidden;
             box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div style="background:#4f46e5;padding:28px 32px;">
    <div style="font-size:12px;color:#c7d2fe;text-transform:uppercase;letter-spacing:.1em;">
        Weekly Analytics Report
    </div>
    <div style="font-size:22px;font-weight:700;color:#ffffff;margin:6px 0;">
        {restaurant_name}
    </div>
    <div style="font-size:13px;color:#c7d2fe;">
        Week of {week_start} to {week_end}
    </div>
  </div>

  <!-- Headline -->
  <div style="padding:24px 32px 0;">
    <div style="font-size:20px;font-weight:700;color:#111827;line-height:1.4;">
        {narrative.get("headline", "")}
    </div>
  </div>

  <!-- Executive Summary -->
  <div style="padding:16px 32px 0;">
    <div style="background:#f9fafb;border-radius:8px;padding:16px;
                font-size:14px;color:#374151;line-height:1.7;">
        {narrative.get("executive_summary", "")}
    </div>
  </div>

  <!-- Metric Cards -->
  <div style="padding:20px 32px 0;">{metric_cards_html}</div>

  <!-- Anomaly Alerts -->
  <div style="padding:20px 32px 0;">{anomaly_section}</div>

  <!-- Revenue Section -->
  <div style="padding:8px 32px 0;">
    <h3 style="font-size:15px;color:#111827;margin:0 0 8px;border-bottom:1px solid #e5e7eb;padding-bottom:8px;">
        Revenue
    </h3>
    <p style="font-size:14px;color:#374151;line-height:1.7;margin:0;">
        {narrative.get("revenue_narrative", "")}
    </p>
  </div>

  <!-- Food Cost Section -->
  <div style="padding:20px 32px 0;">
    <h3 style="font-size:15px;color:#111827;margin:0 0 8px;border-bottom:1px solid #e5e7eb;padding-bottom:8px;">
        Food Cost
    </h3>
    <p style="font-size:14px;color:#374151;line-height:1.7;margin:0;">
        {narrative.get("food_cost_narrative", "")}
    </p>
  </div>

  <!-- Inventory Section -->
  <div style="padding:20px 32px 0;">
    <h3 style="font-size:15px;color:#111827;margin:0 0 8px;border-bottom:1px solid #e5e7eb;padding-bottom:8px;">
        Inventory &amp; Waste
    </h3>
    <p style="font-size:14px;color:#374151;line-height:1.7;margin:0;">
        {narrative.get("inventory_narrative", "")}
    </p>
  </div>

  <!-- Menu Section -->
  <div style="padding:20px 32px 0;">
    <h3 style="font-size:15px;color:#111827;margin:0 0 8px;border-bottom:1px solid #e5e7eb;padding-bottom:8px;">
        Menu Performance
    </h3>
    <p style="font-size:14px;color:#374151;line-height:1.7;margin:0;">
        {narrative.get("menu_narrative", "")}
    </p>
  </div>

  <!-- Benchmarks -->
  <div style="padding:20px 32px 0;">
    <h3 style="font-size:15px;color:#111827;margin:0 0 8px;border-bottom:1px solid #e5e7eb;padding-bottom:8px;">
        Industry Benchmarks
    </h3>
    <p style="font-size:14px;color:#374151;line-height:1.7;margin:0 0 8px;">
        {narrative.get("benchmark_commentary", "")}
    </p>
    {bench_html}
  </div>

  <!-- Top Recommendation -->
  <div style="padding:8px 32px 0;">{top_rec_html}</div>

  <!-- Closing -->
  <div style="padding:20px 32px 28px;">
    <p style="font-size:14px;color:#6b7280;line-height:1.7;margin:0 0 20px;">
        {narrative.get("closing", "")}
    </p>
    <a href="{dashboard_url}/dashboard/reports"
       style="display:inline-block;padding:12px 28px;background:#4f46e5;
              color:#ffffff;text-decoration:none;border-radius:6px;
              font-size:14px;font-weight:600;">
        View Full Dashboard →
    </a>
  </div>

  <!-- Footer -->
  <div style="padding:16px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;
              font-size:12px;color:#9ca3af;text-align:center;">
    RestaurantOS Analytics Agent · <a href="{dashboard_url}" style="color:#6b7280;">Open Dashboard</a>
  </div>
</div>
</body>
</html>"""

    subject = f"Weekly Analytics: {restaurant_name} — w/e {week_end}"
    await _send(to_email, subject, html)


# ---------------------------------------------------------------------------
# 6K — Platform Intelligence Email (internal)
# ---------------------------------------------------------------------------

async def send_platform_intelligence(
    to_email: str,
    platform_narrative: dict,
    platform_metrics: dict,
    league_table: list,
    week_start: str,
    week_end: str,
) -> None:
    """Send the internal platform intelligence briefing to the founding team.

    platform_narrative: parsed JSON from Claude platform_intelligence prompt
    platform_metrics: output of get_platform_metrics()
    league_table: output of get_client_league_table()
    """
    total_mrr = platform_metrics.get("total_mrr", 0)
    mrr_at_risk = platform_metrics.get("mrr_at_risk", 0)
    avg_health = platform_metrics.get("avg_client_health", 0)
    active_clients = platform_metrics.get("total_active_clients", 0)
    total_revenue = platform_metrics.get("total_platform_revenue", 0)
    agent_runs = platform_metrics.get("agent_total_runs", 0)

    # 4 KPI cards
    def _kpi_card(label: str, value: str, subtitle: str = "", color: str = "#4f46e5") -> str:
        return f"""
        <td style="padding:8px;width:25%;">
            <div style="background:rgba(255,255,255,0.08);border-radius:8px;
                        padding:14px;text-align:center;">
                <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;
                             letter-spacing:.05em;margin-bottom:4px;">{label}</div>
                <div style="font-size:20px;font-weight:700;color:#ffffff;">{value}</div>
                {f'<div style="font-size:11px;color:#94a3b8;margin-top:3px;">{subtitle}</div>' if subtitle else ''}
            </div>
        </td>"""

    kpi_html = f"""
    <table cellpadding="0" cellspacing="0" width="100%"><tbody><tr>
        {_kpi_card("MRR", f"AED {total_mrr:,.0f}")}
        {_kpi_card("MRR at Risk", f"AED {mrr_at_risk:,.0f}", "needs attention")}
        {_kpi_card("Avg Health", f"{avg_health:.0f}/100")}
        {_kpi_card("Active Clients", str(active_clients))}
    </tr></tbody></table>"""

    # Three priorities
    priorities = platform_narrative.get("three_priorities", [])
    priorities_html = "".join(
        f"""<div style="display:flex;align-items:flex-start;margin-bottom:12px;">
            <div style="min-width:24px;height:24px;border-radius:50%;background:#4f46e5;
                        color:white;font-size:12px;font-weight:700;display:flex;
                        align-items:center;justify-content:center;margin-right:12px;
                        flex-shrink:0;">{i}</div>
            <div style="font-size:14px;color:#374151;line-height:1.6;">{p}</div>
        </div>"""
        for i, p in enumerate(priorities[:3], 1)
    )

    # Client league table (top 5)
    league_rows_html = ""
    for i, client in enumerate(league_table[:5], 1):
        league_rows_html += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
            <td style="padding:10px 0;font-size:13px;color:#6b7280;">{i}</td>
            <td style="padding:10px 8px;font-size:14px;font-weight:600;color:#111827;">
                {client.get('restaurant_name', '—')}
            </td>
            <td style="padding:10px 8px;font-size:14px;color:#374151;">
                AED {client.get('gross_revenue', 0):,.0f}
            </td>
            <td style="padding:10px 8px;font-size:14px;color:#374151;">
                {client.get('food_cost_pct', 0):.1f}%
            </td>
            <td style="padding:10px 0;font-size:14px;color:#374151;">
                {client.get('recommendation_action_rate', 0):.0f}%
            </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             background:#f3f4f6;margin:0;padding:0;">
<div style="max-width:640px;margin:32px auto;background:#ffffff;
            border-radius:10px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.1);">

  <!-- Dark header -->
  <div style="background:#0f172a;padding:28px 32px;">
    <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.1em;">
        Internal — Platform Intelligence
    </div>
    <div style="font-size:20px;font-weight:700;color:#f1f5f9;margin:8px 0;">
        {platform_narrative.get("week_headline", "Weekly Platform Briefing")}
    </div>
    <div style="font-size:13px;color:#64748b;">
        Week of {week_start} to {week_end}
    </div>
    <!-- KPI Cards -->
    <div style="margin-top:20px;">{kpi_html}</div>
  </div>

  <!-- Body -->
  <div style="padding:28px 32px;">

    <!-- MRR Commentary -->
    <h3 style="font-size:14px;color:#111827;margin:0 0 8px;font-weight:700;">MRR & Subscriptions</h3>
    <p style="font-size:14px;color:#374151;line-height:1.7;margin:0 0 20px;">
        {platform_narrative.get("mrr_commentary", "")}
    </p>

    <!-- Platform Revenue -->
    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                padding:14px 16px;margin-bottom:20px;">
        <div style="font-size:12px;color:#15803d;font-weight:700;text-transform:uppercase;
                    margin-bottom:4px;">Platform Revenue This Week</div>
        <div style="font-size:20px;font-weight:700;color:#14532d;">
            AED {total_revenue:,.0f}
        </div>
        <div style="font-size:13px;color:#16a34a;margin-top:4px;">
            {agent_runs} agent runs · {platform_metrics.get("total_platform_covers", 0):,} covers processed
        </div>
    </div>
    <p style="font-size:14px;color:#374151;line-height:1.7;margin:0 0 20px;">
        {platform_narrative.get("platform_revenue_commentary", "")}
    </p>

    <!-- Health Distribution -->
    <h3 style="font-size:14px;color:#111827;margin:0 0 8px;font-weight:700;">Client Health</h3>
    <p style="font-size:14px;color:#374151;line-height:1.7;margin:0 0 20px;">
        {platform_narrative.get("health_distribution_commentary", "")}
    </p>

    <!-- Feature Adoption -->
    <h3 style="font-size:14px;color:#111827;margin:0 0 8px;font-weight:700;">Feature Adoption</h3>
    <p style="font-size:14px;color:#374151;line-height:1.7;margin:0 0 20px;">
        {platform_narrative.get("feature_adoption_commentary", "")}
    </p>

    <!-- Three Priorities -->
    <h3 style="font-size:14px;color:#111827;margin:0 0 12px;font-weight:700;">
        Three Priorities This Week
    </h3>
    <div style="margin-bottom:24px;">{priorities_html}</div>

    <!-- Client League Table -->
    <h3 style="font-size:14px;color:#111827;margin:0 0 12px;font-weight:700;">
        Top Clients by Revenue
    </h3>
    <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:24px;">
        <thead>
            <tr style="border-bottom:2px solid #e5e7eb;">
                <th style="text-align:left;padding:8px 0;font-size:11px;color:#9ca3af;
                           text-transform:uppercase;">#</th>
                <th style="text-align:left;padding:8px;font-size:11px;color:#9ca3af;
                           text-transform:uppercase;">Restaurant</th>
                <th style="text-align:left;padding:8px;font-size:11px;color:#9ca3af;
                           text-transform:uppercase;">Revenue</th>
                <th style="text-align:left;padding:8px;font-size:11px;color:#9ca3af;
                           text-transform:uppercase;">Food Cost</th>
                <th style="text-align:left;padding:0;font-size:11px;color:#9ca3af;
                           text-transform:uppercase;">Action Rate</th>
            </tr>
        </thead>
        <tbody>{league_rows_html}</tbody>
    </table>

    <!-- One thing going well -->
    <div style="background:#f0fdf4;border-left:4px solid #22c55e;border-radius:0 6px 6px 0;
                padding:14px 16px;margin-bottom:12px;">
        <div style="font-size:12px;color:#16a34a;font-weight:700;margin-bottom:4px;">
            GOING WELL
        </div>
        <div style="font-size:14px;color:#14532d;line-height:1.6;">
            {platform_narrative.get("one_thing_going_well", "")}
        </div>
    </div>

    <!-- One thing to watch -->
    <div style="background:#fffbeb;border-left:4px solid #f59e0b;border-radius:0 6px 6px 0;
                padding:14px 16px;margin-bottom:24px;">
        <div style="font-size:12px;color:#d97706;font-weight:700;margin-bottom:4px;">
            WATCH THIS
        </div>
        <div style="font-size:14px;color:#78350f;line-height:1.6;">
            {platform_narrative.get("one_thing_to_watch", "")}
        </div>
    </div>

  </div>

  <!-- Footer -->
  <div style="padding:16px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;
              font-size:12px;color:#9ca3af;text-align:center;">
    RestaurantOS Internal Platform Intelligence · Confidential
  </div>
</div>
</body>
</html>"""

    subject = f"Platform Intelligence — Week of {week_start}"
    await _send(to_email, subject, html)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

async def _send(to_email: str, subject: str, html: str) -> None:
    """Wrap the synchronous Resend SDK call in a thread so we stay async."""
    resend.api_key = os.environ.get("RESEND_API_KEY", "")
    from_email = _get_from_email()

    params = resend.Emails.SendParams(
        from_=from_email,
        to=[to_email],
        subject=subject,
        html=html,
    )

    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        print(f"[Email] Sent '{subject}' to {to_email} (id={result.get('id', '?')})")
    except Exception as e:
        print(f"[Email Error] Failed to send '{subject}' to {to_email}: {e}")
        raise
