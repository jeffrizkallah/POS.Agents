-- Extended Odoo sync: sales, purchase, manufacturing, recipes, transfers
-- Run against agents Neon DB

CREATE TABLE IF NOT EXISTS sale_orders (
    id           UUID PRIMARY KEY,
    order_number VARCHAR NOT NULL,
    branch       VARCHAR,
    client_name  VARCHAR,
    order_date   DATE,
    state        VARCHAR,
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sale_order_lines (
    id              UUID PRIMARY KEY,
    sale_order_id   UUID REFERENCES sale_orders(id) ON DELETE CASCADE,
    product_name    VARCHAR,
    category        VARCHAR,
    qty             NUMERIC(12,3),
    unit            VARCHAR,
    unit_price      NUMERIC(12,5),
    price_subtotal  NUMERIC(14,3),
    is_internal     BOOLEAN DEFAULT FALSE,
    barcode         VARCHAR,
    month           INTEGER
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id            UUID PRIMARY KEY,
    order_number  VARCHAR,
    branch        VARCHAR,
    supplier_name VARCHAR,
    order_date    DATE,
    total         NUMERIC(14,3),
    vat           NUMERIC(12,3),
    bill_number   VARCHAR,
    month         INTEGER,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchase_order_lines (
    id                  UUID PRIMARY KEY,
    purchase_order_id   UUID REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_name        VARCHAR,
    category            VARCHAR,
    qty                 NUMERIC(12,3),
    unit                VARCHAR,
    unit_cost           NUMERIC(12,5),
    total               NUMERIC(14,3),
    barcode             VARCHAR
);

CREATE TABLE IF NOT EXISTS manufacturing_orders (
    id              UUID PRIMARY KEY,
    reference       VARCHAR,
    product_name    VARCHAR,
    unit            VARCHAR,
    qty_to_produce  NUMERIC(12,3),
    scheduled_date  DATE,
    state           VARCHAR,
    company         VARCHAR,
    barcode         VARCHAR,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recipes (
    id                       UUID PRIMARY KEY,
    bom_odoo_id              INTEGER,
    finished_product         VARCHAR NOT NULL,
    finished_product_barcode VARCHAR,
    component_name           VARCHAR NOT NULL,
    component_barcode        VARCHAR,
    qty                      NUMERIC(16,6),
    unit                     VARCHAR,
    unit_cost                NUMERIC(16,6),
    ingredient_total_cost    NUMERIC(16,6),
    recipe_total_cost        NUMERIC(16,6),
    is_subrecipe             BOOLEAN DEFAULT FALSE,
    child_bom_id             INTEGER,
    created_at               TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transfers (
    id              UUID PRIMARY KEY,
    reference       VARCHAR,
    from_branch     VARCHAR,
    to_branch       VARCHAR,
    effective_date  DATE,
    scheduled_date  DATE,
    product_name    VARCHAR,
    category        VARCHAR,
    qty             NUMERIC(12,3),
    unit            VARCHAR,
    cost            NUMERIC(12,5),
    barcode         VARCHAR,
    created_at      TIMESTAMP DEFAULT NOW()
);
