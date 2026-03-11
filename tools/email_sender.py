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
