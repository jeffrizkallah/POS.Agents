# Odoo Integration Guide — Mikana (mknmis-uae.com)

> Read this when agent logic is complete and you're ready to connect a real client.

---

## Prerequisites (do these before writing any code)

### 1. Fix data quality in Odoo (client's job)
- Go to **Inventory → Products** in Odoo
- Rename every product named "Reference", "Ref", "reference222111" etc. to its real name (e.g. "Chicken Breast", "Rice", "Tomato Paste")
- Fix the item showing `150,015` quantity — almost certainly a typo
- Archive or delete the product named "To Delete"
- Set correct on-hand quantities via the **Update Quantity** button on each product

### 2. Confirm Odoo modules are active
Make sure these are installed in their Odoo:
- Point of Sale
- Inventory
- Purchase

---

## What You Already Know Works

- **URL:** `https://mknmis-uae.com`
- **Database:** `OdoodbProdUAE07012022`
- **API:** XML-RPC works (tested March 2026)
- **Login:** Your email + password authenticates successfully
- **Data confirmed:** Inventory items pull correctly, POS orders pull correctly
- **Multiple locations confirmed:** ISC_Ajman, ISC_RAK, ISC_Soufouh, ISC_Khalifa, ISC_DIP, ISC_Ain, ISC_SHARJA, Sabis_YAS, SIS_Ruwais

---

## Step 1 — Create the connector file

Create `connectors/odoo_connector.py` in the agents repo.

This file pulls data from Odoo and writes it into your Neon DB. It runs once per night before the agents wake up.

**Data to pull and where it comes from:**

| What | Odoo model | Maps to your table |
|---|---|---|
| Locations | `pos.config` | `restaurants` |
| Products/ingredients | `stock.quant` + `product.product` | `ingredients` |
| Stock movements | `stock.move.line` | `inventory_transactions` |
| Purchase orders | `purchase.order` + `purchase.order.line` | `purchase_orders` |
| Suppliers | `res.partner` (supplier_rank > 0) | `suppliers` |
| Menu items | `product.template` (available in POS) | `menu_items` |
| Sales | `pos.order` + `pos.order.line` | `orders` + `order_items` |

---

## Step 2 — Add Mikana's locations to your DB

Each Odoo POS location (ISC_Ajman, ISC_RAK etc.) becomes one row in your `restaurants` table. Run this once in Neon SQL Editor after the connector is built:

```sql
INSERT INTO restaurants (name, contact_email)
VALUES
  ('ISC Ajman',   'manager@mikana.com'),
  ('ISC RAK',     'manager@mikana.com'),
  ('ISC DIP',     'manager@mikana.com'),
  ('ISC Khalifa', 'manager@mikana.com'),
  ('ISC Ain',     'manager@mikana.com'),
  ('ISC Soufouh', 'manager@mikana.com'),
  ('ISC SHARJA',  'manager@mikana.com'),
  ('Sabis YAS',   'manager@mikana.com'),
  ('SIS Ruwais',  'manager@mikana.com');
```

---

## Step 3 — Schedule the connector in main.py

Add the connector job to run at 00:30 (before agents run):

```python
from connectors.odoo_connector import sync_odoo_data

scheduler.add_job(
    lambda: asyncio.run(sync_odoo_data()),
    CronTrigger(hour=0, minute=30),
    id="odoo_sync",
    max_instances=1
)
```

Agents already run at 02:00 (pricing) and 08:00 (customer success) — the connector feeds them fresh data 90 minutes before.

---

## Step 4 — Create a read-only API user in Odoo (security)

Don't use your personal login in production. Create a dedicated read-only user:

1. Go to **Settings → Users → New User**
2. Name: `RestaurantOS Agent`
3. Email: something like `agent@mikana.com`
4. Set access rights to **read-only** on Inventory, POS, Purchase
5. Use this user's credentials in the connector's environment variables

Add to Railway environment variables:
```
MIKANA_ODOO_URL=https://mknmis-uae.com
MIKANA_ODOO_DB=OdoodbProdUAE07012022
MIKANA_ODOO_USER=agent@mikana.com
MIKANA_ODOO_PASSWORD=...
```

---

## What Does NOT Need to Change

- All agent logic (inventory, ordering, pricing, customer success, reporting) stays identical
- The agents loop through `restaurants` table — Mikana's locations just appear as new rows
- Emails go to whatever contact email you set in the restaurants table

---

## Checklist for Go-Live

- [ ] All Odoo products have real names (not "Reference")
- [ ] Stock quantities are accurate in Odoo
- [ ] POS is recording live sales
- [ ] `connectors/odoo_connector.py` built and tested locally
- [ ] Mikana locations added to `restaurants` table in Neon
- [ ] Read-only Odoo API user created
- [ ] Credentials added to Railway environment variables
- [ ] Connector scheduled in main.py at 00:30
- [ ] First sync run manually and verified (check Neon for new rows)
- [ ] Agents pick up Mikana data on next scheduled run
- [ ] First email report received at manager email
