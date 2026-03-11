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

from tools.database import create_pool, get_all_restaurants, get_manager_email
from agents.inventory import run_inventory_check, detect_waste_anomalies
from agents.ordering import draft_purchase_orders, send_approval_email
from tools.email_sender import send_urgent_alert

# Global pool — created once at startup, reused by every job
pool = None
scheduler = BackgroundScheduler()


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

    print("[Job] inventory_and_ordering_job complete.")


def inventory_and_ordering_job():
    """Sync wrapper called by APScheduler. Delegates to async implementation."""
    try:
        asyncio.run(_async_inventory_and_ordering_job())
    except Exception as e:
        print(f"[Scheduler Error] inventory_and_ordering_job crashed: {e}")


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

def handle_shutdown(signum, frame):
    print(f"\n[Shutdown] Signal {signum} received — shutting down gracefully...")
    scheduler.shutdown(wait=False)
    if pool:
        asyncio.run(pool.close())
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

    # 2. Database pool + startup log
    restaurant_count = asyncio.run(startup())

    # 3. Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # 4. Schedule jobs
    scheduler.add_job(
        inventory_and_ordering_job,
        CronTrigger(minute="*/15"),
        id="inventory_and_ordering",
        name="Inventory & Ordering Check",
        max_instances=1,       # never run two overlapping instances
        misfire_grace_time=60, # if a tick is missed, run within 60s or skip
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
