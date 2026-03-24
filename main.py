import asyncio
import os
import signal
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

from tools.database import (
    create_pool,
    get_all_restaurants,
    get_manager_email,
    get_all_clients,
    get_brands_for_client,
)
from agents.inventory import run_inventory_check, detect_waste_anomalies
from agents.ordering import draft_purchase_orders, send_approval_email
from agents.pricing import (
    apply_approved_recommendations,
    save_food_cost_snapshots,
    generate_pricing_recommendations,
)
from agents.customer_success import (
    check_restaurant_health,
    send_checkin_if_needed,
    send_monthly_roi_summary_email,
)
from agents.reporting import run_reporting_agent
from agents.orchestrator import run_orchestrator, run_daily_briefing
from agents.scout import run_scout
from agents.pipeline import run_pipeline
from agents.customer_care import run_care_feedback, run_competitive_intel
from agents.broadcast import run_content_batch, run_publish_queue, run_engagement_sync
from agents.seo_engine import run_seo_engine
from agents.sales import run_apollo_pull, run_sales_batch
from agents.marketing import run_marketing_content, run_marketing_publish
from tools.email_sender import send_urgent_alert
from tools.integrations.odoo_sync import run_odoo_sync

# Global pool — created once at startup, reused by every job
pool = None
scheduler = BackgroundScheduler()

# One persistent event loop shared by all jobs.
# asyncio.run() creates+closes a loop each call, which breaks the DB pool.
# Using a single long-lived loop keeps the pool on the correct loop forever.
_loop = asyncio.new_event_loop()


def _run(coro):
    """Run an async coroutine on the persistent event loop (thread-safe)."""
    return _loop.run_until_complete(coro)


# ---------------------------------------------------------------------------
# Health check server (Railway pings this to confirm the process is alive)
# ---------------------------------------------------------------------------

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"RestaurantOS Agents running OK")

    def log_message(self, *args):
        pass  # silence access logs


def start_health_server():
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print("[Health] Health check server started on port 8080")


# ---------------------------------------------------------------------------
# Phase 7C: Multi-client loop pattern — reused by all Phase 8-13 agents
# ---------------------------------------------------------------------------

async def _async_client_agent_job(agent_fn) -> None:
    """Generic multi-client loop. Iterates all active clients → brands and
    calls agent_fn(pool, client, brand) for each combination.

    One failing brand never stops others. Reused by every Phase 8-13 agent:
        scheduler.add_job(lambda: _run(_async_client_agent_job(my_agent_fn)), ...)
    """
    global pool
    clients = await get_all_clients(pool)
    print(f"[MultiClient] {agent_fn.__name__} — {len(clients)} client(s)")
    for client in clients:
        brands = await get_brands_for_client(pool, str(client["id"]))
        for brand in brands:
            try:
                await agent_fn(pool, client, brand)
            except Exception as e:
                print(f"[MultiClient] {agent_fn.__name__} failed for brand '{brand['name']}': {e}")


# ---------------------------------------------------------------------------
# Per-restaurant logic (async, isolated — one failure must not stop others)
# ---------------------------------------------------------------------------

async def _run_restaurant(restaurant: dict) -> None:
    """Run inventory scan, ordering, and waste anomaly check for one restaurant.

    All exceptions are caught and printed here so a single broken restaurant
    never prevents the others from being processed.
    """
    restaurant_id = str(restaurant["id"])
    restaurant_name = restaurant["name"]

    # --- Inventory scan ---
    try:
        low_stock_items = await run_inventory_check(pool, restaurant_id)
    except Exception as e:
        print(f"[Job] Inventory scan failed for {restaurant_name}: {e}")
        low_stock_items = []

    # --- Draft purchase orders (only if low-stock items exist) ---
    if low_stock_items:
        try:
            orders_created = await draft_purchase_orders(
                pool, restaurant_id, restaurant_name, low_stock_items
            )
        except Exception as e:
            print(f"[Job] Ordering failed for {restaurant_name}: {e}")
            orders_created = []

        if orders_created:
            try:
                await send_approval_email(
                    pool, restaurant_id, restaurant_name, orders_created
                )
            except Exception as e:
                print(f"[Job] Approval email failed for {restaurant_name}: {e}")

    # --- Waste anomaly detection ---
    try:
        anomalies = await detect_waste_anomalies(pool, restaurant_id)
    except Exception as e:
        print(f"[Job] Waste anomaly check failed for {restaurant_name}: {e}")
        anomalies = []

    if anomalies:
        try:
            manager_email = await get_manager_email(pool, restaurant_id)
        except Exception:
            manager_email = None

        if manager_email:
            dashboard_url = os.environ.get("APP_URL", "https://app.restaurantos.com")
            lines = "\n".join(
                f"  • {a['ingredient_name']}: this week {a['current_week_qty']:.2f} "
                f"vs {a['avg_4week_qty']:.2f} avg ({a['ratio']}×)"
                for a in anomalies
            )
            try:
                await send_urgent_alert(
                    to_email=manager_email,
                    restaurant_name=restaurant_name,
                    subject=f"{len(anomalies)} waste anomaly(s) detected",
                    message=(
                        f"The following ingredients have unusually high waste "
                        f"this week compared to the 4-week average:\n\n{lines}\n\n"
                        f"Please review and log waste reasons in the dashboard."
                    ),
                    dashboard_url=dashboard_url,
                )
            except Exception as e:
                print(f"[Job] Waste alert email failed for {restaurant_name}: {e}")


# ---------------------------------------------------------------------------
# Scheduler job (sync wrapper — APScheduler calls this every 15 minutes)
# ---------------------------------------------------------------------------

async def _async_inventory_and_ordering_job():
    """Async core of the inventory & ordering job.

    Fetches all restaurants and runs the full pipeline for each one,
    catching per-restaurant exceptions so one failure never stops the rest.
    """
    global pool
    restaurants = await get_all_restaurants(pool)
    print(f"[Job] inventory_and_ordering_job — {len(restaurants)} restaurant(s)")

    for restaurant in restaurants:
        await _run_restaurant(restaurant)

    # Apply any pricing recommendations that were approved in the POS dashboard
    for restaurant in restaurants:
        restaurant_id = str(restaurant["id"])
        restaurant_name = restaurant["name"]
        try:
            await apply_approved_recommendations(pool, restaurant_id, restaurant_name)
        except Exception as e:
            print(f"[Job] Price application failed for {restaurant_name}: {e}")

    print("[Job] inventory_and_ordering_job complete.")


def inventory_and_ordering_job():
    """Sync wrapper called by APScheduler. Delegates to async implementation."""
    try:
        _run(_async_inventory_and_ordering_job())
    except Exception as e:
        print(f"[Scheduler Error] inventory_and_ordering_job crashed: {e}")


# ---------------------------------------------------------------------------
# Pricing jobs (nightly 02:00 snapshots, 02:30 recommendations)
# ---------------------------------------------------------------------------

async def _async_food_cost_snapshot_job():
    """Save nightly food cost snapshots for all restaurants (runs at 02:00)."""
    global pool
    restaurants = await get_all_restaurants(pool)
    print(f"[Job] food_cost_snapshot_job — {len(restaurants)} restaurant(s)")

    for restaurant in restaurants:
        restaurant_id = str(restaurant["id"])
        restaurant_name = restaurant["name"]
        try:
            await save_food_cost_snapshots(pool, restaurant_id, restaurant_name)
        except Exception as e:
            print(f"[Job] Snapshot failed for {restaurant_name}: {e}")

    print("[Job] food_cost_snapshot_job complete.")


def food_cost_snapshot_job():
    """Sync wrapper called by APScheduler at 02:00."""
    try:
        _run(_async_food_cost_snapshot_job())
    except Exception as e:
        print(f"[Scheduler Error] food_cost_snapshot_job crashed: {e}")


async def _async_pricing_recommendation_job():
    """Generate pricing recommendations for over-target items (runs at 02:30)."""
    global pool
    restaurants = await get_all_restaurants(pool)
    print(f"[Job] pricing_recommendation_job — {len(restaurants)} restaurant(s)")

    for restaurant in restaurants:
        restaurant_id = str(restaurant["id"])
        restaurant_name = restaurant["name"]
        target_pct = float(restaurant.get("target_food_cost_pct") or 30.0)
        try:
            await generate_pricing_recommendations(
                pool, restaurant_id, restaurant_name, target_pct
            )
        except Exception as e:
            print(f"[Job] Pricing recommendations failed for {restaurant_name}: {e}")

    print("[Job] pricing_recommendation_job complete.")


def pricing_recommendation_job():
    """Sync wrapper called by APScheduler at 02:30."""
    try:
        _run(_async_pricing_recommendation_job())
    except Exception as e:
        print(f"[Scheduler Error] pricing_recommendation_job crashed: {e}")


# ---------------------------------------------------------------------------
# Customer success job (daily 08:00 health checks + check-in emails)
# ---------------------------------------------------------------------------

async def _async_customer_success_job():
    """Run engagement health checks for all restaurants and send check-in emails."""
    global pool
    restaurants = await get_all_restaurants(pool)
    print(f"[Job] customer_success_job — {len(restaurants)} restaurant(s)")

    for restaurant in restaurants:
        restaurant_id = str(restaurant["id"])
        restaurant_name = restaurant["name"]
        try:
            health = await check_restaurant_health(pool, restaurant_id, restaurant_name)
            await send_checkin_if_needed(pool, restaurant_id, restaurant_name, health)
        except Exception as e:
            print(f"[Job] Customer success check failed for {restaurant_name}: {e}")

    print("[Job] customer_success_job complete.")


def customer_success_job():
    """Sync wrapper called by APScheduler at 08:00."""
    try:
        _run(_async_customer_success_job())
    except Exception as e:
        print(f"[Scheduler Error] customer_success_job crashed: {e}")


# ---------------------------------------------------------------------------
# Monthly ROI summary job (1st of each month, 09:00)
# ---------------------------------------------------------------------------

async def _async_monthly_roi_job():
    """Send monthly ROI summary emails to all restaurant managers."""
    global pool
    restaurants = await get_all_restaurants(pool)
    print(f"[Job] monthly_roi_job — {len(restaurants)} restaurant(s)")

    for restaurant in restaurants:
        restaurant_id = str(restaurant["id"])
        restaurant_name = restaurant["name"]
        try:
            await send_monthly_roi_summary_email(pool, restaurant_id, restaurant_name)
        except Exception as e:
            print(f"[Job] Monthly ROI email failed for {restaurant_name}: {e}")

    print("[Job] monthly_roi_job complete.")


def monthly_roi_job():
    """Sync wrapper called by APScheduler on the 1st of each month at 09:00."""
    try:
        _run(_async_monthly_roi_job())
    except Exception as e:
        print(f"[Scheduler Error] monthly_roi_job crashed: {e}")


# ---------------------------------------------------------------------------
# Weekly reporting job (Monday 06:00 UTC)
# ---------------------------------------------------------------------------

async def _async_reporting_job():
    """Run the full weekly reporting & analytics pipeline."""
    global pool
    print("[Job] reporting_job — starting weekly analytics run")
    await run_reporting_agent(pool)
    print("[Job] reporting_job complete.")


def reporting_job():
    """Sync wrapper called by APScheduler every Monday at 06:00."""
    try:
        _run(_async_reporting_job())
    except Exception as e:
        print(f"[Scheduler Error] reporting_job crashed: {e}")


# ---------------------------------------------------------------------------
# Phase 8: Orchestrator jobs (every 4 hours + weekday 07:30 briefing)
# ---------------------------------------------------------------------------

def orchestrator_job():
    """Sync wrapper: approval routing + ROI classification for all clients/brands."""
    try:
        _run(_async_client_agent_job(run_orchestrator))
    except Exception as e:
        print(f"[Scheduler Error] orchestrator_job crashed: {e}")


def daily_briefing_job():
    """Sync wrapper: daily briefing email for all clients/brands (weekdays 07:30)."""
    try:
        _run(_async_client_agent_job(run_daily_briefing))
    except Exception as e:
        print(f"[Scheduler Error] daily_briefing_job crashed: {e}")


# ---------------------------------------------------------------------------
# Phase 9: Scout job (weekdays 07:00 — qualify prospects + flag renewals)
# ---------------------------------------------------------------------------

def scout_job():
    """Sync wrapper: prospect qualification for all clients/brands (weekdays 07:00)."""
    try:
        _run(_async_client_agent_job(run_scout))
    except Exception as e:
        print(f"[Scheduler Error] scout_job crashed: {e}")


# ---------------------------------------------------------------------------
# Phase 10: Pipeline job (weekdays 09:00 — outreach sequencing + step execution)
# ---------------------------------------------------------------------------

def pipeline_job():
    """Sync wrapper: generate outreach sequences and execute approved steps."""
    try:
        _run(_async_client_agent_job(run_pipeline))
    except Exception as e:
        print(f"[Scheduler Error] pipeline_job crashed: {e}")


# ---------------------------------------------------------------------------
# Phase 11: Customer Care jobs
# ---------------------------------------------------------------------------

def care_feedback_job():
    """Sync wrapper: feedback triage for all clients/brands (every 30 min)."""
    try:
        _run(_async_client_agent_job(run_care_feedback))
    except Exception as e:
        print(f"[Scheduler Error] care_feedback_job crashed: {e}")


def care_intel_job():
    """Sync wrapper: monthly competitive intelligence (1st of month at 06:00)."""
    try:
        _run(_async_client_agent_job(run_competitive_intel))
    except Exception as e:
        print(f"[Scheduler Error] care_intel_job crashed: {e}")


# ---------------------------------------------------------------------------
# Phase 12: Broadcast Agent jobs
# ---------------------------------------------------------------------------

def broadcast_batch_job():
    """Sync wrapper: generate weekly social posts for all clients/brands (Monday 06:00)."""
    try:
        _run(_async_client_agent_job(run_content_batch))
    except Exception as e:
        print(f"[Scheduler Error] broadcast_batch_job crashed: {e}")


def broadcast_publish_job():
    """Sync wrapper: publish approved posts with scheduled_for <= now (every 30 min)."""
    try:
        _run(_async_client_agent_job(run_publish_queue))
    except Exception as e:
        print(f"[Scheduler Error] broadcast_publish_job crashed: {e}")


def broadcast_engagement_job():
    """Sync wrapper: sync engagement metrics and classify new comments (every 2 hours)."""
    try:
        _run(_async_client_agent_job(run_engagement_sync))
    except Exception as e:
        print(f"[Scheduler Error] broadcast_engagement_job crashed: {e}")


# ---------------------------------------------------------------------------
# Phase 13: SEO Engine job (Monday 06:00 — alongside broadcast batch)
# ---------------------------------------------------------------------------

def seo_engine_job():
    """Sync wrapper: generate SEO keyword clusters and articles for all clients/brands."""
    try:
        _run(_async_client_agent_job(run_seo_engine))
    except Exception as e:
        print(f"[Scheduler Error] seo_engine_job crashed: {e}")


# ---------------------------------------------------------------------------
# Phase 14A: Sales Outreach jobs
# ---------------------------------------------------------------------------

def sales_apollo_job():
    """Sync wrapper: weekly Apollo.io lead pull + scoring + cold email drafting (Monday 08:00)."""
    try:
        _run(run_apollo_pull(pool))
    except Exception as e:
        print(f"[Scheduler Error] sales_apollo_job crashed: {e}")


def sales_batch_job():
    """Sync wrapper: daily cold email batch send — up to 20 emails (weekdays 10:00)."""
    try:
        _run(run_sales_batch(pool))
    except Exception as e:
        print(f"[Scheduler Error] sales_batch_job crashed: {e}")


# ---------------------------------------------------------------------------
# Phase 14B: Marketing Content jobs
# ---------------------------------------------------------------------------

def marketing_content_job():
    """Sync wrapper: weekly blog post generation (Monday 07:00)."""
    try:
        _run(run_marketing_content(pool))
    except Exception as e:
        print(f"[Scheduler Error] marketing_content_job crashed: {e}")


def marketing_publish_job():
    """Sync wrapper: daily Buffer publish of approved blog posts (weekdays 10:30)."""
    try:
        _run(run_marketing_publish(pool))
    except Exception as e:
        print(f"[Scheduler Error] marketing_publish_job crashed: {e}")


# ---------------------------------------------------------------------------
# Odoo sync job (nightly 01:00 — before food cost snapshot at 02:00)
# ---------------------------------------------------------------------------

def odoo_sync_job():
    """Sync wrapper: pull Odoo data into Neon for all restaurant agents."""
    try:
        _run(run_odoo_sync(pool))
    except Exception as e:
        print(f"[Scheduler Error] odoo_sync_job crashed: {e}")


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

def handle_shutdown(signum, frame):
    print(f"\n[Shutdown] Signal {signum} received — shutting down gracefully...")
    scheduler.shutdown(wait=False)
    if pool:
        _run(pool.close())
    print("[Shutdown] Done.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def startup():
    global pool
    pool = await create_pool()
    restaurants = await get_all_restaurants(pool)
    print(
        f"[Startup] RestaurantOS Agents started. "
        f"Monitoring {len(restaurants)} restaurant(s)."
    )
    return len(restaurants)


def main():
    # 1. Health check server
    start_health_server()

    # 2. Database pool + startup log (use persistent loop — same loop jobs will use)
    asyncio.set_event_loop(_loop)
    restaurant_count = _run(startup())

    # 3. Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # 4. Schedule jobs
    scheduler.add_job(
        inventory_and_ordering_job,
        CronTrigger(minute="*/15"),
        id="inventory_and_ordering",
        name="Inventory & Ordering Check",
        max_instances=1,
        misfire_grace_time=60,
    )

    scheduler.add_job(
        food_cost_snapshot_job,
        CronTrigger(hour=2, minute=0),
        id="food_cost_snapshot",
        name="Nightly Food Cost Snapshot",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        pricing_recommendation_job,
        CronTrigger(hour=2, minute=30),
        id="pricing_recommendations",
        name="Nightly Pricing Recommendations",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        customer_success_job,
        CronTrigger(hour=8, minute=0),
        id="customer_success",
        name="Daily Customer Success Health Check",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        monthly_roi_job,
        CronTrigger(day=1, hour=9, minute=0),
        id="monthly_roi_summary",
        name="Monthly ROI Summary Email",
        max_instances=1,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        reporting_job,
        CronTrigger(day_of_week="mon", hour=6, minute=0),
        id="weekly_reporting",
        name="Weekly Reporting & Analytics",
        max_instances=1,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        orchestrator_job,
        CronTrigger(hour="*/4"),
        id="orchestrator",
        name="Orchestrator — Approval Routing & ROI Classification",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        daily_briefing_job,
        CronTrigger(day_of_week="mon-fri", hour=7, minute=30),
        id="daily_briefing",
        name="Daily Briefing Email",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        scout_job,
        CronTrigger(day_of_week="mon-fri", hour=7, minute=0),
        id="scout",
        name="Scout — Prospect Qualification & Renewal Alerts",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        pipeline_job,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=0),
        id="pipeline",
        name="Pipeline — Outreach Sequencing & Step Execution",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        care_feedback_job,
        CronTrigger(minute="*/30"),
        id="care_feedback",
        name="Customer Care — Feedback Triage",
        max_instances=1,
        misfire_grace_time=120,
    )

    scheduler.add_job(
        care_intel_job,
        CronTrigger(day=1, hour=6, minute=0),
        id="care_intel",
        name="Customer Care — Monthly Competitive Intelligence",
        max_instances=1,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        broadcast_batch_job,
        CronTrigger(day_of_week="mon", hour=6, minute=0),
        id="broadcast_batch",
        name="Broadcast — Weekly Content Generation",
        max_instances=1,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        broadcast_publish_job,
        CronTrigger(minute="*/30"),
        id="broadcast_publish",
        name="Broadcast — Publish Approved Posts",
        max_instances=1,
        misfire_grace_time=120,
    )

    scheduler.add_job(
        broadcast_engagement_job,
        CronTrigger(hour="*/2"),
        id="broadcast_engagement",
        name="Broadcast — Engagement Sync & Comment Classification",
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        seo_engine_job,
        CronTrigger(day_of_week="mon", hour=6, minute=0),
        id="seo_engine",
        name="SEO Engine — Keyword Clusters & Article Generation",
        max_instances=1,
        misfire_grace_time=3600,
    )

    # Phase 14A: Sales Outreach
    scheduler.add_job(
        sales_apollo_job,
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="sales_apollo",
        name="Sales — Weekly Apollo Lead Pull & Cold Email Drafting",
        max_instances=1,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        sales_batch_job,
        CronTrigger(day_of_week="mon-fri", hour=10, minute=0),
        id="sales_batch",
        name="Sales — Daily Cold Email Batch Send (max 20/day)",
        max_instances=1,
        misfire_grace_time=300,
    )

    # Phase 14B: Marketing Content
    scheduler.add_job(
        marketing_content_job,
        CronTrigger(day_of_week="mon", hour=7, minute=0),
        id="marketing_content",
        name="Marketing — Weekly Blog Post Generation",
        max_instances=1,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        marketing_publish_job,
        CronTrigger(day_of_week="mon-fri", hour=10, minute=30),
        id="marketing_publish",
        name="Marketing — Publish Approved Blog Posts via Buffer",
        max_instances=1,
        misfire_grace_time=300,
    )

    # Odoo sync (nightly 01:00 — populates restaurants, ingredients, menu_items, orders, waste)
    scheduler.add_job(
        odoo_sync_job,
        CronTrigger(hour=1, minute=0),
        id="odoo_sync",
        name="Odoo → Neon Sync",
        max_instances=1,
        misfire_grace_time=1800,
    )

    scheduler.start()
    print(
        f"[Scheduler] Running. Next inventory check in <15 min. "
        f"({restaurant_count} restaurant(s) monitored)"
    )

    # 5. Keep-alive loop
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
