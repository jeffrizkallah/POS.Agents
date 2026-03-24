"""
Odoo → Neon sync
================
Read-only from Odoo (XML-RPC search_read calls only).
Writes exclusively to the agents Neon DB.

Syncs nightly at 01:00 (before the 02:00 food-cost snapshot job).

Tables populated:
  restaurants       ← stock.warehouse
  suppliers         ← res.partner (supplier_rank > 0)
  ingredients       ← product.product (stockable/consumable) + stock.quant
  menu_items        ← product.product (available_in_pos = True)
  orders            ← pos.order (last 90 days)
  order_items       ← pos.order.line (last 90 days)
  waste_records     ← stock.scrap (last 90 days)

UUIDs are deterministic (uuid5) so repeated syncs safely upsert existing rows.
"""

import asyncio
import os
import ssl
import uuid
import xmlrpc.client
from datetime import datetime, timedelta, timezone

import asyncpg

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ODOO_URL      = os.environ.get("ODOO_URL", "")
ODOO_DB       = os.environ.get("ODOO_DB", "")
ODOO_USERNAME = os.environ.get("ODOO_USERNAME", "")
ODOO_API_KEY  = os.environ.get("ODOO_API_KEY", "")

_NS = uuid.NAMESPACE_DNS  # namespace for deterministic UUIDs

SYNC_DAYS = 90  # how many days of orders/waste to pull


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stable_id(key: str) -> str:
    """Return a deterministic UUID string from an Odoo record key."""
    return str(uuid.uuid5(_NS, key))


def _odoo_proxies():
    """Return (common, models) XML-RPC proxies with SSL verification disabled."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common", context=ctx)
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object", context=ctx)
    return common, models


def _read(models, uid: int, model: str, domain: list, fields: list, limit: int = 5000) -> list:
    """Thin wrapper around execute_kw search_read."""
    return models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        model, "search_read",
        [domain],
        {"fields": fields, "limit": limit},
    )


# ---------------------------------------------------------------------------
# Odoo fetch functions (all blocking — called via run_in_executor)
# ---------------------------------------------------------------------------

def _fetch_all(uid: int):
    """Pull all required data from Odoo in one call and return a dict of lists."""
    _, models = _odoo_proxies()
    since = (datetime.now(timezone.utc) - timedelta(days=SYNC_DAYS)).strftime("%Y-%m-%d %H:%M:%S")

    warehouses = _read(models, uid, "stock.warehouse", [], ["id", "name", "lot_stock_id"])

    suppliers = _read(
        models, uid, "res.partner",
        [["supplier_rank", ">", 0], ["active", "=", True]],
        ["id", "name", "email", "property_supplier_payment_term_id"],
    )

    products = _read(
        models, uid, "product.product",
        [["type", "in", ["consu", "product"]], ["active", "=", True]],
        ["id", "name", "uom_id", "standard_price", "type"],
    )

    quants = _read(
        models, uid, "stock.quant",
        [["location_id.usage", "=", "internal"]],
        ["id", "product_id", "location_id", "quantity"],
    )

    orderpoints = _read(
        models, uid, "stock.warehouse.orderpoint",
        [["active", "=", True]],
        ["id", "product_id", "warehouse_id", "product_min_qty", "product_max_qty"],
    )

    supplier_info = _read(
        models, uid, "product.supplierinfo",
        [],
        ["id", "product_tmpl_id", "partner_id", "delay"],
    )

    pos_products = _read(
        models, uid, "product.product",
        [["available_in_pos", "=", True], ["active", "=", True]],
        ["id", "name", "lst_price", "active"],
    )

    pos_orders = _read(
        models, uid, "pos.order",
        [["date_order", ">=", since], ["state", "in", ["done", "invoiced"]]],
        ["id", "name", "date_order", "config_id", "state"],
    )

    pos_lines = []
    if pos_orders:
        order_ids = [o["id"] for o in pos_orders]
        pos_lines = _read(
            models, uid, "pos.order.line",
            [["order_id", "in", order_ids]],
            ["id", "order_id", "product_id", "qty"],
        )

    scraps = _read(
        models, uid, "stock.scrap",
        [["date_done", ">=", since], ["state", "=", "done"]],
        ["id", "product_id", "location_id", "scrap_qty", "date_done"],
    )

    # POS configs to resolve warehouse → restaurant
    pos_configs = _read(models, uid, "pos.config", [], ["id", "name", "picking_type_id"])

    return {
        "warehouses": warehouses,
        "suppliers": suppliers,
        "products": products,
        "quants": quants,
        "orderpoints": orderpoints,
        "supplier_info": supplier_info,
        "pos_products": pos_products,
        "pos_orders": pos_orders,
        "pos_lines": pos_lines,
        "scraps": scraps,
        "pos_configs": pos_configs,
    }


# ---------------------------------------------------------------------------
# Neon upsert functions (all async using pool)
# ---------------------------------------------------------------------------

async def _upsert_restaurants(pool: asyncpg.Pool, warehouses: list) -> dict:
    """Upsert warehouses as restaurants. Returns {odoo_id: neon_uuid}."""
    mapping = {}
    for wh in warehouses:
        neon_id = _stable_id(f"odoo:warehouse:{wh['id']}")
        mapping[wh["id"]] = neon_id
        await pool.execute(
            """
            INSERT INTO restaurants (id, name, timezone, target_food_cost_pct, currency)
            VALUES ($1, $2, 'Asia/Dubai', 30.0, 'AED')
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
            """,
            neon_id, wh["name"],
        )
    print(f"[OdooSync] restaurants: {len(warehouses)} upserted")
    return mapping


async def _upsert_suppliers(pool: asyncpg.Pool, suppliers: list) -> dict:
    """Upsert Odoo partners as suppliers. Returns {odoo_id: neon_uuid}."""
    mapping = {}
    for s in suppliers:
        neon_id = _stable_id(f"odoo:partner:{s['id']}")
        mapping[s["id"]] = neon_id
        email = s.get("email") or ""
        await pool.execute(
            """
            INSERT INTO suppliers (id, name, email, lead_time_days, is_supermarket)
            VALUES ($1, $2, $3, 3, FALSE)
            ON CONFLICT (id) DO UPDATE SET
                name  = EXCLUDED.name,
                email = EXCLUDED.email
            """,
            neon_id, s["name"], email,
        )
    print(f"[OdooSync] suppliers: {len(suppliers)} upserted")
    return mapping


async def _upsert_ingredients(
    pool: asyncpg.Pool,
    products: list,
    quants: list,
    orderpoints: list,
    supplier_info: list,
    restaurant_map: dict,   # odoo warehouse_id → neon restaurant_id
    supplier_map: dict,     # odoo partner_id  → neon supplier_id
) -> dict:
    """Upsert products as ingredients in every warehouse. Returns {odoo_product_id: neon_uuid}."""
    # Aggregate stock per product across internal locations
    stock: dict[int, float] = {}
    for q in quants:
        pid = q["product_id"][0] if isinstance(q["product_id"], list) else q["product_id"]
        stock[pid] = stock.get(pid, 0.0) + float(q["quantity"] or 0)

    # Reorder points per product (use first warehouse found)
    reorder: dict[int, tuple[float, float]] = {}  # product_id → (min_qty, max_qty)
    for op in orderpoints:
        pid = op["product_id"][0] if isinstance(op["product_id"], list) else op["product_id"]
        reorder[pid] = (float(op["product_min_qty"] or 0), float(op["product_max_qty"] or 0))

    # Supplier per product template
    tmpl_supplier: dict[int, int] = {}  # tmpl_id → partner_id
    for si in supplier_info:
        tmpl_id = si["product_tmpl_id"][0] if isinstance(si["product_tmpl_id"], list) else si["product_tmpl_id"]
        partner_id = si["partner_id"][0] if isinstance(si["partner_id"], list) else si["partner_id"]
        if tmpl_id not in tmpl_supplier:
            tmpl_supplier[tmpl_id] = partner_id

    mapping = {}
    for wh_odoo_id, restaurant_id in restaurant_map.items():
        for p in products:
            pid = p["id"]
            neon_id = _stable_id(f"odoo:product:{pid}:wh:{wh_odoo_id}")
            mapping[pid] = neon_id

            unit_name = p["uom_id"][1] if isinstance(p["uom_id"], list) else (p.get("uom_id") or "unit")
            stock_qty = stock.get(pid, 0.0)
            cost = float(p.get("standard_price") or 0)
            min_qty, max_qty = reorder.get(pid, (stock_qty * 0.2, stock_qty * 0.5))

            # Resolve supplier (product_tmpl_id is not directly on product.product here,
            # so we skip tmpl lookup and leave supplier_id NULL unless we have a direct match)
            supplier_neon_id = None

            await pool.execute(
                """
                INSERT INTO ingredients
                    (id, restaurant_id, name, unit, stock_qty, par_level,
                     reorder_point, cost_per_unit, supplier_id, is_available)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, TRUE)
                ON CONFLICT (id) DO UPDATE SET
                    name          = EXCLUDED.name,
                    stock_qty     = EXCLUDED.stock_qty,
                    cost_per_unit = EXCLUDED.cost_per_unit,
                    par_level     = EXCLUDED.par_level,
                    reorder_point = EXCLUDED.reorder_point
                """,
                neon_id, restaurant_id, p["name"], unit_name,
                stock_qty, max_qty, min_qty, cost, supplier_neon_id,
            )

    print(f"[OdooSync] ingredients: {len(products)} × {len(restaurant_map)} warehouse(s) upserted")
    return mapping


async def _upsert_menu_items(
    pool: asyncpg.Pool,
    pos_products: list,
    restaurant_map: dict,
) -> dict:
    """Upsert POS products as menu_items. Returns {odoo_product_id: neon_uuid}."""
    mapping = {}
    for wh_odoo_id, restaurant_id in restaurant_map.items():
        for p in pos_products:
            neon_id = _stable_id(f"odoo:pos_product:{p['id']}:wh:{wh_odoo_id}")
            mapping[p["id"]] = neon_id
            price = float(p.get("lst_price") or 0)
            await pool.execute(
                """
                INSERT INTO menu_items (id, restaurant_id, name, price, is_available)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE SET
                    name  = EXCLUDED.name,
                    price = EXCLUDED.price,
                    is_available = EXCLUDED.is_available
                """,
                neon_id, restaurant_id, p["name"], price, bool(p.get("active", True)),
            )
    print(f"[OdooSync] menu_items: {len(pos_products)} × {len(restaurant_map)} warehouse(s) upserted")
    return mapping


async def _upsert_orders(
    pool: asyncpg.Pool,
    pos_orders: list,
    pos_lines: list,
    menu_item_map: dict,
    restaurant_map: dict,
) -> None:
    """Upsert POS orders and order lines."""
    # Build a lookup of order_id → pos.config → warehouse for restaurant mapping
    # For simplicity, use the first warehouse when we can't resolve
    default_restaurant_id = next(iter(restaurant_map.values())) if restaurant_map else None

    lines_by_order: dict[int, list] = {}
    for line in pos_lines:
        oid = line["order_id"][0] if isinstance(line["order_id"], list) else line["order_id"]
        lines_by_order.setdefault(oid, []).append(line)

    for order in pos_orders:
        neon_order_id = _stable_id(f"odoo:pos.order:{order['id']}")
        restaurant_id = default_restaurant_id
        if not restaurant_id:
            continue

        try:
            date_str = order.get("date_order") or ""
            created_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) if date_str else datetime.now(timezone.utc)
        except ValueError:
            created_at = datetime.now(timezone.utc)

        state = order.get("state", "done")
        status = "completed" if state in ("done", "invoiced") else "cancelled"

        await pool.execute(
            """
            INSERT INTO orders (id, restaurant_id, status, created_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status
            """,
            neon_order_id, restaurant_id, status, created_at,
        )

        for line in lines_by_order.get(order["id"], []):
            neon_line_id = _stable_id(f"odoo:pos.order.line:{line['id']}")
            prod_id = line["product_id"][0] if isinstance(line["product_id"], list) else line["product_id"]
            menu_item_id = menu_item_map.get(prod_id)
            if not menu_item_id:
                continue

            await pool.execute(
                """
                INSERT INTO order_items (id, order_id, menu_item_id, quantity)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET quantity = EXCLUDED.quantity
                """,
                neon_line_id, neon_order_id, menu_item_id, float(line.get("qty") or 0),
            )

    print(f"[OdooSync] orders: {len(pos_orders)} upserted, {len(pos_lines)} lines")


async def _upsert_waste(
    pool: asyncpg.Pool,
    scraps: list,
    ingredient_map: dict,
    restaurant_map: dict,
) -> None:
    """Upsert stock scrap records as waste_records."""
    default_restaurant_id = next(iter(restaurant_map.values())) if restaurant_map else None
    if not default_restaurant_id:
        return

    for scrap in scraps:
        neon_id = _stable_id(f"odoo:stock.scrap:{scrap['id']}")
        prod_id = scrap["product_id"][0] if isinstance(scrap["product_id"], list) else scrap["product_id"]
        ingredient_id = ingredient_map.get(prod_id)
        if not ingredient_id:
            continue

        try:
            date_str = scrap.get("date_done") or ""
            created_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) if date_str else datetime.now(timezone.utc)
        except ValueError:
            created_at = datetime.now(timezone.utc)

        await pool.execute(
            """
            INSERT INTO waste_records (id, restaurant_id, ingredient_id, quantity_wasted, created_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE SET quantity_wasted = EXCLUDED.quantity_wasted
            """,
            neon_id, default_restaurant_id, ingredient_id,
            float(scrap.get("scrap_qty") or 0), created_at,
        )

    print(f"[OdooSync] waste_records: {len(scraps)} upserted")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_odoo_sync(pool: asyncpg.Pool) -> None:
    """Pull data from Odoo and upsert into the agents Neon DB. Read-only from Odoo."""
    if not all([ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_API_KEY]):
        print("[OdooSync] Skipping — ODOO_URL / ODOO_DB / ODOO_USERNAME / ODOO_API_KEY not set")
        return

    print(f"[OdooSync] Starting sync from {ODOO_URL} ...")

    # 1. Authenticate (blocking → thread executor)
    loop = asyncio.get_event_loop()
    try:
        common, _ = _odoo_proxies()
        uid: int = await loop.run_in_executor(
            None,
            lambda: common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_API_KEY, {}),
        )
    except Exception as e:
        print(f"[OdooSync] Authentication failed: {e}")
        return

    if not uid:
        print("[OdooSync] Authentication returned uid=0 — check credentials")
        return

    print(f"[OdooSync] Authenticated as uid={uid}")

    # 2. Fetch everything from Odoo in one executor call
    try:
        data = await loop.run_in_executor(None, lambda: _fetch_all(uid))
    except Exception as e:
        print(f"[OdooSync] Odoo fetch failed: {e}")
        return

    # 3. Upsert into Neon
    try:
        restaurant_map = await _upsert_restaurants(pool, data["warehouses"])
        supplier_map   = await _upsert_suppliers(pool, data["suppliers"])
        ingredient_map = await _upsert_ingredients(
            pool, data["products"], data["quants"], data["orderpoints"],
            data["supplier_info"], restaurant_map, supplier_map,
        )
        menu_item_map  = await _upsert_menu_items(pool, data["pos_products"], restaurant_map)
        await _upsert_orders(pool, data["pos_orders"], data["pos_lines"], menu_item_map, restaurant_map)
        await _upsert_waste(pool, data["scraps"], ingredient_map, restaurant_map)
    except Exception as e:
        print(f"[OdooSync] Neon upsert failed: {e}")
        return

    print("[OdooSync] Sync complete.")
