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

SYNC_DAYS = 7   # how many days of orders/waste to pull (keep tight for performance)


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
            ["id", "order_id", "product_id", "qty", "price_unit"],
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
        "supplier_info": [],
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
    rows = []
    for s in suppliers:
        neon_id = _stable_id(f"odoo:partner:{s['id']}")
        mapping[s["id"]] = neon_id
        rows.append((neon_id, s["name"], s.get("email") or ""))

    for i in range(0, len(rows), 200):
        await pool.executemany(
            """
            INSERT INTO suppliers (id, name, email, lead_time_days, is_supermarket)
            VALUES ($1, $2, $3, 3, FALSE)
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, email = EXCLUDED.email
            """,
            rows[i:i + 200],
        )
    print(f"[OdooSync] suppliers: {len(rows)} upserted (batch)")
    return mapping


async def _upsert_ingredients(
    pool: asyncpg.Pool,
    products: list,
    quants: list,
    orderpoints: list,
    supplier_info: list,
    restaurant_map: dict,
    supplier_map: dict,
) -> dict:
    """Upsert ingredients — one row per product (aggregated across all warehouses).

    Stock is summed across all internal locations. Using a single primary
    restaurant (first warehouse) keeps the row count manageable for large catalogs.
    """
    if not restaurant_map:
        return {}

    # Use first warehouse as the primary restaurant
    primary_restaurant_id = next(iter(restaurant_map.values()))

    # Aggregate stock per product across all internal locations
    stock: dict[int, float] = {}
    for q in quants:
        pid = q["product_id"][0] if isinstance(q["product_id"], list) else q["product_id"]
        stock[pid] = stock.get(pid, 0.0) + float(q["quantity"] or 0)

    # Reorder points per product
    reorder: dict[int, tuple[float, float]] = {}
    for op in orderpoints:
        pid = op["product_id"][0] if isinstance(op["product_id"], list) else op["product_id"]
        reorder[pid] = (float(op["product_min_qty"] or 0), float(op["product_max_qty"] or 0))

    # Build batch of rows
    rows = []
    mapping = {}
    for p in products:
        pid = p["id"]
        neon_id = _stable_id(f"odoo:product:{pid}")
        mapping[pid] = neon_id
        unit_name = p["uom_id"][1] if isinstance(p["uom_id"], list) else (p.get("uom_id") or "unit")
        _cap = 9_999_999.0  # max value for NUMERIC(10,3)
        stock_qty = min(float(stock.get(pid, 0.0)), _cap)
        cost = min(float(p.get("standard_price") or 0), _cap)
        min_qty, max_qty = reorder.get(pid, (min(stock_qty * 0.2, _cap), min(stock_qty * 0.5, _cap)))
        rows.append((neon_id, primary_restaurant_id, p["name"], unit_name, stock_qty, max_qty, min_qty, cost))

    # Batch upsert in chunks of 200
    for i in range(0, len(rows), 200):
        chunk = rows[i:i + 200]
        await pool.executemany(
            """
            INSERT INTO ingredients
                (id, restaurant_id, name, unit, stock_qty, par_level, reorder_point, cost_per_unit, supplier_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NULL)
            ON CONFLICT (id) DO UPDATE SET
                name          = EXCLUDED.name,
                stock_qty     = EXCLUDED.stock_qty,
                cost_per_unit = EXCLUDED.cost_per_unit,
                par_level     = EXCLUDED.par_level,
                reorder_point = EXCLUDED.reorder_point
            """,
            chunk,
        )

    print(f"[OdooSync] ingredients: {len(rows)} upserted (batch)")
    return mapping


async def _upsert_menu_items(
    pool: asyncpg.Pool,
    pos_products: list,
    restaurant_map: dict,
) -> dict:
    """Replace menu_items for the primary restaurant. Returns {odoo_product_id: neon_int_id}."""
    if not restaurant_map:
        return {}
    primary_restaurant_id = next(iter(restaurant_map.values()))

    # Full replace: must delete order_items → orders → menu_items (FK chain)
    await pool.execute(
        "DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE restaurant_id = $1)",
        primary_restaurant_id,
    )
    await pool.execute("DELETE FROM orders WHERE restaurant_id = $1", primary_restaurant_id)
    await pool.execute("DELETE FROM menu_items WHERE restaurant_id = $1", primary_restaurant_id)

    inserted_ids = []
    for p in pos_products:
        row_id = await pool.fetchval(
            """INSERT INTO menu_items (restaurant_id, name, price, category, is_available)
               VALUES ($1,$2,$3,'general',$4) RETURNING id""",
            primary_restaurant_id, p["name"],
            float(p.get("lst_price") or 0), bool(p.get("active", True)),
        )
        inserted_ids.append(row_id)

    # Build odoo_product_id → neon int id mapping
    mapping = {}
    for p, neon_int_id in zip(pos_products, inserted_ids):
        mapping[p["id"]] = neon_int_id

    print(f"[OdooSync] menu_items: {len(inserted_ids)} inserted (replace)")
    return mapping


async def _upsert_orders(
    pool: asyncpg.Pool,
    pos_orders: list,
    pos_lines: list,
    menu_item_map: dict,
    restaurant_map: dict,
) -> None:
    """Batch-replace orders + lines for the primary restaurant (last SYNC_DAYS)."""
    if not restaurant_map or not pos_orders:
        print("[OdooSync] orders: 0 inserted (no data)")
        return
    primary_restaurant_id = next(iter(restaurant_map.values()))

    # Build order rows
    order_rows = []
    for order in pos_orders:
        try:
            date_str = order.get("date_order") or ""
            created_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") if date_str else datetime.utcnow()
        except ValueError:
            created_at = datetime.utcnow()
        status = "completed" if order.get("state") in ("done", "invoiced") else "cancelled"
        order_num = str(order.get("name") or "") or f"ODOO-{order.get('id', uuid.uuid4())}"
        order_rows.append((primary_restaurant_id, order_num, status, created_at))

    # Batch insert orders
    await pool.executemany(
        "INSERT INTO orders (restaurant_id, order_number, status, created_at) VALUES ($1,$2,$3,$4)",
        order_rows,
    )

    # Fetch back inserted IDs by order_number
    order_numbers = [r[1] for r in order_rows]
    id_rows = await pool.fetch(
        "SELECT id, order_number FROM orders WHERE restaurant_id = $1 AND order_number = ANY($2::text[])",
        primary_restaurant_id, order_numbers,
    )
    order_num_to_id = {r["order_number"]: r["id"] for r in id_rows}
    odoo_id_to_order_num = {o["id"]: (o.get("name") or f"ODOO-{o['id']}") for o in pos_orders}

    # Build order_item rows
    lines_by_order: dict[int, list] = {}
    for line in pos_lines:
        oid = line["order_id"][0] if isinstance(line["order_id"], list) else line["order_id"]
        lines_by_order.setdefault(oid, []).append(line)

    item_rows = []
    for order in pos_orders:
        order_num = odoo_id_to_order_num[order["id"]]
        neon_order_id = order_num_to_id.get(order_num)
        if not neon_order_id:
            continue
        for line in lines_by_order.get(order["id"], []):
            prod_id = line["product_id"][0] if isinstance(line["product_id"], list) else line["product_id"]
            menu_item_id = menu_item_map.get(prod_id)
            if not menu_item_id:
                continue
            raw_name = line["product_id"][1] if isinstance(line["product_id"], list) and len(line["product_id"]) > 1 else None
            prod_name = str(raw_name) if raw_name else str(prod_id)
            qty = float(line.get("qty") or 0)
            price_unit = float(line.get("price_unit") or 0)
            item_rows.append((neon_order_id, menu_item_id, prod_name, qty, price_unit, qty * price_unit))

    # Batch insert order_items in chunks
    for i in range(0, len(item_rows), 500):
        await pool.executemany(
            "INSERT INTO order_items (order_id, menu_item_id, menu_item_name, quantity, unit_price, subtotal) VALUES ($1,$2,$3,$4,$5,$6)",
            item_rows[i:i + 500],
        )

    print(f"[OdooSync] orders: {len(order_rows)} inserted, {len(item_rows)} lines (batch)")


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
            created_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") if date_str else datetime.utcnow()
        except ValueError:
            created_at = datetime.utcnow()

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
# Extended sync: sale orders, purchase orders, manufacturing, recipes, transfers
# ---------------------------------------------------------------------------

_SINCE_2025 = "2025-01-01 00:00:00"
_PAGE = 300  # orders per page (keep small for large line sets)


def _sale_page(uid: int, offset: int):
    """Blocking: fetch one page of sale orders + their lines."""
    _, models = _odoo_proxies()
    orders = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, "sale.order", "search_read",
        [[["date_order", ">=", _SINCE_2025], ["state", "in", ["sale", "done"]]]],
        {"fields": ["id", "name", "partner_id", "date_order", "state", "warehouse_id"],
         "limit": _PAGE, "offset": offset},
    )
    if not orders:
        return [], []
    order_ids = [o["id"] for o in orders]
    lines = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, "sale.order.line", "search_read",
        [[["order_id", "in", order_ids]]],
        {"fields": ["id", "order_id", "product_id", "product_uom_qty",
                    "product_uom", "price_unit", "price_subtotal"]},
    )
    return orders, lines


async def _sync_sale_orders(pool: asyncpg.Pool, uid: int) -> None:
    loop = asyncio.get_event_loop()
    # Fresh start
    await pool.execute("TRUNCATE sale_order_lines, sale_orders CASCADE")

    offset, total_orders, total_lines = 0, 0, 0
    while True:
        orders, lines = await loop.run_in_executor(None, lambda o=offset: _sale_page(uid, o))
        if not orders:
            break

        odoo_to_neon: dict[int, str] = {}
        order_rows = []
        for o in orders:
            nid = _stable_id(f"odoo:sale.order:{o['id']}")
            odoo_to_neon[o["id"]] = nid
            client = (o["partner_id"][1] if isinstance(o.get("partner_id"), list) else "") or ""
            branch = (o["warehouse_id"][1] if isinstance(o.get("warehouse_id"), list) else "") or ""
            ds = o.get("date_order") or ""
            od = None
            if len(ds) >= 10:
                try:
                    od = datetime.strptime(ds[:10], "%Y-%m-%d").date()
                except ValueError:
                    pass
            order_rows.append((nid, str(o.get("name") or ""), branch, client, od, o.get("state") or ""))

        await pool.executemany(
            "INSERT INTO sale_orders (id, order_number, branch, client_name, order_date, state) "
            "VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT (id) DO NOTHING",
            order_rows,
        )

        line_rows = []
        for line in lines:
            nid = _stable_id(f"odoo:sale.order.line:{line['id']}")
            oid = line["order_id"][0] if isinstance(line.get("order_id"), list) else line.get("order_id")
            soid = odoo_to_neon.get(oid)
            if not soid:
                continue
            pname = (line["product_id"][1] if isinstance(line.get("product_id"), list) else "") or ""
            unit  = (line["product_uom"][1] if isinstance(line.get("product_uom"), list) else "") or ""
            qty   = float(line.get("product_uom_qty") or 0)
            up    = float(line.get("price_unit") or 0)
            sub   = float(line.get("price_subtotal") or 0)
            # Get month from parent order
            parent = next((o for o in orders if o["id"] == oid), None)
            ds = parent.get("date_order") or "" if parent else ""
            month = int(ds[5:7]) if len(ds) >= 7 else None
            line_rows.append((nid, soid, pname, qty, unit, up, sub, up == 0.0, None, month))

        for i in range(0, len(line_rows), 500):
            await pool.executemany(
                "INSERT INTO sale_order_lines "
                "(id, sale_order_id, product_name, qty, unit, unit_price, price_subtotal, is_internal, barcode, month) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) ON CONFLICT (id) DO NOTHING",
                line_rows[i:i + 500],
            )

        total_orders += len(orders)
        total_lines  += len(line_rows)
        offset       += len(orders)
        print(f"[OdooSync] sale_orders: {total_orders} orders, {total_lines} lines so far...")
        if len(orders) < _PAGE:
            break

    print(f"[OdooSync] sale_orders: done — {total_orders} orders, {total_lines} lines")


def _purchase_page(uid: int, offset: int):
    """Blocking: fetch one page of purchase orders + their lines."""
    _, models = _odoo_proxies()
    orders = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, "purchase.order", "search_read",
        [[["date_order", ">=", _SINCE_2025], ["state", "in", ["purchase", "done"]]]],
        {"fields": ["id", "name", "partner_id", "date_order", "amount_total",
                    "amount_tax", "picking_type_id"],
         "limit": _PAGE, "offset": offset},
    )
    if not orders:
        return [], []
    order_ids = [o["id"] for o in orders]
    lines = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, "purchase.order.line", "search_read",
        [[["order_id", "in", order_ids]]],
        {"fields": ["id", "order_id", "product_id", "product_qty",
                    "product_uom", "price_unit", "price_subtotal"]},
    )
    return orders, lines


async def _sync_purchase_orders(pool: asyncpg.Pool, uid: int) -> None:
    loop = asyncio.get_event_loop()
    await pool.execute("TRUNCATE purchase_order_lines, purchase_orders CASCADE")

    offset, total_orders, total_lines = 0, 0, 0
    while True:
        orders, lines = await loop.run_in_executor(None, lambda o=offset: _purchase_page(uid, o))
        if not orders:
            break

        odoo_to_neon: dict[int, str] = {}
        order_rows = []
        for o in orders:
            nid = _stable_id(f"odoo:purchase.order:{o['id']}")
            odoo_to_neon[o["id"]] = nid
            supplier = (o["partner_id"][1] if isinstance(o.get("partner_id"), list) else "") or ""
            branch   = (o["picking_type_id"][1] if isinstance(o.get("picking_type_id"), list) else "") or ""
            ds = o.get("date_order") or ""
            od = None
            if len(ds) >= 10:
                try:
                    od = datetime.strptime(ds[:10], "%Y-%m-%d").date()
                except ValueError:
                    pass
            month = int(ds[5:7]) if len(ds) >= 7 else None
            total = min(float(o.get("amount_total") or 0), 9_999_999.0)
            vat   = min(float(o.get("amount_tax") or 0), 9_999_999.0)
            order_rows.append((nid, str(o.get("name") or ""), branch, supplier, od, total, vat, None, month))

        await pool.executemany(
            "INSERT INTO purchase_orders "
            "(id, order_number, branch, supplier_name, order_date, total, vat, bill_number, month) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT (id) DO NOTHING",
            order_rows,
        )

        line_rows = []
        for line in lines:
            nid  = _stable_id(f"odoo:purchase.order.line:{line['id']}")
            oid  = line["order_id"][0] if isinstance(line.get("order_id"), list) else line.get("order_id")
            poid = odoo_to_neon.get(oid)
            if not poid:
                continue
            pname = (line["product_id"][1] if isinstance(line.get("product_id"), list) else "") or ""
            unit  = (line["product_uom"][1] if isinstance(line.get("product_uom"), list) else "") or ""
            qty   = float(line.get("product_qty") or 0)
            uc    = min(float(line.get("price_unit") or 0), 9_999_999.0)
            sub   = min(float(line.get("price_subtotal") or 0), 9_999_999.0)
            line_rows.append((nid, poid, pname, "", qty, unit, uc, sub, None))

        for i in range(0, len(line_rows), 500):
            await pool.executemany(
                "INSERT INTO purchase_order_lines "
                "(id, purchase_order_id, product_name, category, qty, unit, unit_cost, total, barcode) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT (id) DO NOTHING",
                line_rows[i:i + 500],
            )

        total_orders += len(orders)
        total_lines  += len(line_rows)
        offset       += len(orders)
        print(f"[OdooSync] purchase_orders: {total_orders} orders, {total_lines} lines so far...")
        if len(orders) < _PAGE:
            break

    print(f"[OdooSync] purchase_orders: done — {total_orders} orders, {total_lines} lines")


def _fetch_manufacturing(uid: int, offset: int):
    """Blocking: fetch one page of manufacturing orders."""
    _, models = _odoo_proxies()
    return models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, "mrp.production", "search_read",
        [[["date_planned_start", ">=", _SINCE_2025], ["state", "=", "done"]]],
        {"fields": ["id", "name", "product_id", "product_uom_id", "product_qty",
                    "date_planned_start", "state", "company_id"],
         "limit": 1000, "offset": offset},
    )


async def _sync_manufacturing(pool: asyncpg.Pool, uid: int) -> None:
    loop = asyncio.get_event_loop()
    await pool.execute("TRUNCATE manufacturing_orders")

    offset, total = 0, 0
    while True:
        records = await loop.run_in_executor(None, lambda o=offset: _fetch_manufacturing(uid, o))
        if not records:
            break

        rows = []
        for r in records:
            nid     = _stable_id(f"odoo:mrp.production:{r['id']}")
            pname   = (r["product_id"][1] if isinstance(r.get("product_id"), list) else "") or ""
            unit    = (r["product_uom_id"][1] if isinstance(r.get("product_uom_id"), list) else "") or ""
            company = (r["company_id"][1] if isinstance(r.get("company_id"), list) else "") or ""
            ds      = r.get("date_planned_start") or ""
            sd = None
            if len(ds) >= 10:
                try:
                    sd = datetime.strptime(ds[:10], "%Y-%m-%d").date()
                except ValueError:
                    pass
            qty = min(float(r.get("product_qty") or 0), 9_999_999.0)
            rows.append((nid, str(r.get("name") or ""), pname, unit, qty, sd, r.get("state") or "", company, None))

        for i in range(0, len(rows), 500):
            await pool.executemany(
                "INSERT INTO manufacturing_orders "
                "(id, reference, product_name, unit, qty_to_produce, scheduled_date, state, company, barcode) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT (id) DO NOTHING",
                rows[i:i + 500],
            )
        total  += len(records)
        offset += len(records)
        if len(records) < 1000:
            break

    print(f"[OdooSync] manufacturing_orders: {total} records")


def _fetch_boms(uid: int):
    """Blocking: fetch all BOMs and all BOM lines."""
    _, models = _odoo_proxies()
    boms = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, "mrp.bom", "search_read",
        [[["active", "=", True]]],
        {"fields": ["id", "product_id", "product_tmpl_id", "product_qty",
                    "product_uom_id", "bom_line_ids"], "limit": 5000},
    )
    # Fetch all BOM lines at once
    lines = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, "mrp.bom.line", "search_read",
        [[]],
        {"fields": ["id", "bom_id", "product_id", "product_qty",
                    "product_uom_id", "child_bom_id"], "limit": 50000},
    )
    # Fetch product standard prices for cost calculation
    product_ids = list({
        (line["product_id"][0] if isinstance(line.get("product_id"), list) else line.get("product_id"))
        for line in lines if line.get("product_id")
    })
    costs: dict[int, float] = {}
    for i in range(0, len(product_ids), 500):
        chunk = product_ids[i:i+500]
        prods = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY, "product.product", "search_read",
            [[["id", "in", chunk]]],
            {"fields": ["id", "standard_price"]},
        )
        for p in prods:
            costs[p["id"]] = float(p.get("standard_price") or 0)
    return boms, lines, costs


async def _sync_recipes(pool: asyncpg.Pool, uid: int) -> None:
    loop = asyncio.get_event_loop()
    await pool.execute("TRUNCATE recipes")

    boms, lines, costs = await loop.run_in_executor(None, lambda: _fetch_boms(uid))

    # Build maps
    bom_by_id: dict[int, dict] = {b["id"]: b for b in boms}
    # product_id → bom (for sub-recipe detection)
    product_to_bom: dict[int, int] = {}
    for b in boms:
        pid = b["product_id"][0] if isinstance(b.get("product_id"), list) else b.get("product_id")
        if pid:
            product_to_bom[pid] = b["id"]

    # Lines by bom_id
    lines_by_bom: dict[int, list] = {}
    for line in lines:
        bid = line["bom_id"][0] if isinstance(line.get("bom_id"), list) else line.get("bom_id")
        if bid:
            lines_by_bom.setdefault(bid, []).append(line)

    # Compute recipe total cost per bom_id (sum of ingredient_total_cost)
    def bom_total_cost(bom_id: int) -> float:
        total = 0.0
        for line in lines_by_bom.get(bom_id, []):
            pid = line["product_id"][0] if isinstance(line.get("product_id"), list) else line.get("product_id")
            qty = float(line.get("product_qty") or 0)
            uc  = costs.get(pid, 0.0) if pid else 0.0
            total += qty * uc
        return total

    rows = []
    for bom in boms:
        bid       = bom["id"]
        fpid      = bom["product_id"][0] if isinstance(bom.get("product_id"), list) else bom.get("product_id")
        fpname    = (bom["product_id"][1] if isinstance(bom.get("product_id"), list) else "") or ""
        recipe_cost = bom_total_cost(bid)

        for line in lines_by_bom.get(bid, []):
            pid   = line["product_id"][0] if isinstance(line.get("product_id"), list) else line.get("product_id")
            cname = (line["product_id"][1] if isinstance(line.get("product_id"), list) else "") or ""
            unit  = (line["product_uom_id"][1] if isinstance(line.get("product_uom_id"), list) else "") or ""
            qty   = float(line.get("product_qty") or 0)
            uc    = costs.get(pid, 0.0) if pid else 0.0
            itc   = qty * uc
            # Detect sub-recipe
            child_bom_id = None
            if isinstance(line.get("child_bom_id"), list):
                child_bom_id = line["child_bom_id"][0] if line["child_bom_id"] else None
            elif isinstance(line.get("child_bom_id"), int):
                child_bom_id = line["child_bom_id"]
            is_sub = child_bom_id is not None or (pid in product_to_bom)

            row_key = f"odoo:bom.line:{line['id']}:{bid}"
            nid = _stable_id(row_key)
            rows.append((
                nid, bid, fpname, None,
                cname, None,
                qty, unit,
                min(uc, 9_999_999.0),
                min(itc, 9_999_999.0),
                min(recipe_cost, 9_999_999.0),
                is_sub, child_bom_id,
            ))

    for i in range(0, len(rows), 500):
        await pool.executemany(
            "INSERT INTO recipes "
            "(id, bom_odoo_id, finished_product, finished_product_barcode, "
            " component_name, component_barcode, qty, unit, unit_cost, "
            " ingredient_total_cost, recipe_total_cost, is_subrecipe, child_bom_id) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13) ON CONFLICT (id) DO NOTHING",
            rows[i:i + 500],
        )

    print(f"[OdooSync] recipes: {len(boms)} BOMs, {len(rows)} component rows")


def _transfer_page(uid: int, offset: int):
    """Blocking: fetch one page of done internal transfers + their moves."""
    _, models = _odoo_proxies()
    pickings = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, "stock.picking", "search_read",
        [[["date_done", ">=", _SINCE_2025],
          ["state", "=", "done"],
          ["picking_type_code", "=", "internal"]]],
        {"fields": ["id", "name", "location_id", "location_dest_id",
                    "date_done", "scheduled_date"],
         "limit": _PAGE, "offset": offset},
    )
    if not pickings:
        return [], []
    picking_ids = [p["id"] for p in pickings]
    moves = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, "stock.move", "search_read",
        [[["picking_id", "in", picking_ids], ["state", "=", "done"]]],
        {"fields": ["id", "picking_id", "product_id", "quantity_done",
                    "product_uom", "price_unit"]},
    )
    return pickings, moves


async def _sync_transfers(pool: asyncpg.Pool, uid: int) -> None:
    loop = asyncio.get_event_loop()
    await pool.execute("TRUNCATE transfers")

    offset, total = 0, 0
    while True:
        pickings, moves = await loop.run_in_executor(None, lambda o=offset: _transfer_page(uid, o))
        if not pickings:
            break

        pick_map: dict[int, dict] = {p["id"]: p for p in pickings}
        rows = []
        for move in moves:
            nid   = _stable_id(f"odoo:stock.move:{move['id']}")
            pid   = move["picking_id"][0] if isinstance(move.get("picking_id"), list) else move.get("picking_id")
            pick  = pick_map.get(pid)
            if not pick:
                continue
            from_b = (pick["location_id"][1] if isinstance(pick.get("location_id"), list) else "") or ""
            to_b   = (pick["location_dest_id"][1] if isinstance(pick.get("location_dest_id"), list) else "") or ""
            pname  = (move["product_id"][1] if isinstance(move.get("product_id"), list) else "") or ""
            unit   = (move["product_uom"][1] if isinstance(move.get("product_uom"), list) else "") or ""
            qty    = float(move.get("quantity_done") or 0)
            cost   = min(float(move.get("price_unit") or 0), 9_999_999.0)
            ref    = str(pick.get("name") or "")
            ds_eff = pick.get("date_done") or ""
            ds_sch = pick.get("scheduled_date") or ""
            eff_d  = datetime.strptime(ds_eff[:10], "%Y-%m-%d").date() if len(ds_eff) >= 10 else None
            sch_d  = datetime.strptime(ds_sch[:10], "%Y-%m-%d").date() if len(ds_sch) >= 10 else None
            rows.append((nid, ref, from_b, to_b, eff_d, sch_d, pname, None, qty, unit, cost, None))

        for i in range(0, len(rows), 500):
            await pool.executemany(
                "INSERT INTO transfers "
                "(id, reference, from_branch, to_branch, effective_date, scheduled_date, "
                " product_name, category, qty, unit, cost, barcode) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) ON CONFLICT (id) DO NOTHING",
                rows[i:i + 500],
            )

        total  += len(rows)
        offset += len(pickings)
        print(f"[OdooSync] transfers: {total} moves so far...")
        if len(pickings) < _PAGE:
            break

    print(f"[OdooSync] transfers: done — {total} stock moves")


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
        await _sync_sale_orders(pool, uid)
        await _sync_purchase_orders(pool, uid)
        await _sync_manufacturing(pool, uid)
        await _sync_recipes(pool, uid)
        await _sync_transfers(pool, uid)
    except Exception as e:
        print(f"[OdooSync] Neon upsert failed: {e}")
        return

    print("[OdooSync] Sync complete.")
