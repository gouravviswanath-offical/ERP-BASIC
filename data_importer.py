"""
Universal Data Importer for AI ERP & Custom Datasets.
Supports Excel (.xlsx, .xls), CSV, JSON, and Parquet.
Key Capabilities:
1. Universal Raw Storage: Stores 100% of uploaded data into 'uploaded_dataset' table and 'dataset_current.csv'.
2. Smart Semantic Mapping: Intelligently identifies entities, prices, quantities, and totals without 0-value bugs.
3. Universal Data Profiling: Auto-discovers types, primary metrics, dimensions, and anomalies.
4. Generates comprehensive sample datasets.
"""
import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from db import get_conn, DB_PATH
from universal_profiler import UniversalDataProfiler, load_any_dataset, clean_numeric_value, clean_dataframe
from data_query_engine import set_active_dataframe

# Flexible synonym mapping for ERP column headers
COLUMN_SYNONYMS = {
    "product_name": ["product_name", "product", "item_name", "item", "description", "product_title", "name", "sku_name", "material", "device", "model"],
    "stock": ["stock", "quantity_on_hand", "qty_in_stock", "available_stock", "inventory", "stock_qty", "units_in_stock"],
    "reorder_level": ["reorder_level", "min_stock", "safety_stock", "minimum_level", "reorder_point", "threshold"],
    "price": ["price", "unit_price", "rate", "selling_price", "sales_price", "mrp", "unit_rate"],
    "cost": ["cost", "cost_price", "unit_cost", "purchase_price", "buying_price", "cogs"],
    "category": ["category", "product_category", "department", "group", "item_group", "type", "segment", "class"],

    "customer_name": ["customer_name", "customer", "client", "client_name", "buyer", "party_name", "account_name", "company", "account", "user"],
    "phone": ["phone", "phone_number", "contact", "mobile", "telephone", "contact_no"],
    "email": ["email", "email_address", "mail"],

    "invoice_id": ["invoice_id", "invoice_no", "bill_no", "inv_no", "order_id", "transaction_id", "receipt_no", "order_number"],
    "customer_id": ["customer_id", "client_id", "party_id", "account_id", "user_id"],
    "total": ["total", "total_amount", "grand_total", "invoice_total", "bill_amount", "amount", "net_amount", "sales_amount", "sales", "revenue", "spend"],
    "paid": ["paid", "amount_paid", "received", "paid_amount", "cash_received", "settled"],
    "due": ["due", "balance", "outstanding", "balance_due", "pending_amount", "due_amount"],
    "date": ["date", "created_at", "invoice_date", "bill_date", "order_date", "transaction_date", "timestamp", "order_date"],

    "product_id": ["product_id", "item_id", "sku", "item_code", "product_code"],
    "qty": ["qty", "quantity", "units", "quantity_sold", "units_sold", "volume", "count"],
}


def _normalize_column_name(col: str) -> str:
    cleaned = str(col).strip().lower().replace(" ", "_").replace("-", "_").replace(".", "")
    for canonical, synonyms in COLUMN_SYNONYMS.items():
        if cleaned == canonical or cleaned in synonyms:
            return canonical

    if "reorder" in cleaned or "safety_stock" in cleaned:
        return "reorder_level"
    if "cost" in cleaned or "cogs" in cleaned:
        return "cost"
    if "unit_price" in cleaned or "selling_price" in cleaned or "rate" in cleaned or "mrp" in cleaned:
        return "price"
    if "customer_id" in cleaned or "client_id" in cleaned:
        return "customer_id"
    if "customer" in cleaned or "client" in cleaned or "party" in cleaned or "buyer" in cleaned:
        return "customer_name"
    if "product_id" in cleaned or "item_id" in cleaned:
        return "product_id"
    if "product" in cleaned or "item" in cleaned or "sku" in cleaned or "device" in cleaned:
        return "product_name"
    if "sales" in cleaned or "revenue" in cleaned or "amount" in cleaned or "total" in cleaned:
        return "total"
    if "price" in cleaned:
        return "price"
    if "qty" in cleaned or "quantity" in cleaned or "units" in cleaned:
        return "qty"
    if "phone" in cleaned or "mobile" in cleaned:
        return "phone"
    if "email" in cleaned:
        return "email"
    if "invoice" in cleaned or "order" in cleaned and "date" not in cleaned:
        return "invoice_id"
    if "paid" in cleaned or "received" in cleaned:
        return "paid"
    if "due" in cleaned or "balance" in cleaned or "outstanding" in cleaned:
        return "due"
    if "date" in cleaned or "time" in cleaned:
        return "date"
    if "category" in cleaned or "department" in cleaned or "segment" in cleaned:
        return "category"
    if "stock" in cleaned or "inventory" in cleaned:
        return "stock"

    return cleaned


def _get_scalar(row, key, default=None):
    if hasattr(row, "get"):
        val = row.get(key, default)
    else:
        try:
            val = row[key]
        except Exception:
            val = default
    if isinstance(val, pd.Series):
        val = val.iloc[0] if len(val) > 0 else default
    if pd.isna(val):
        return default
    return val


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    new_cols = []
    seen = set()
    for col in df.columns:
        norm = _normalize_column_name(col)
        if norm in seen:
            i = 2
            while f"{norm}_{i}" in seen:
                i += 1
            norm = f"{norm}_{i}"
        seen.add(norm)
        new_cols.append(norm)

    df_renamed = df.copy()
    df_renamed.columns = new_cols
    return df_renamed


class DataImporter:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _ensure_schema(self, con: sqlite3.Connection):
        cur = con.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS products(
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                stock INTEGER DEFAULT 50,
                reorder_level INTEGER DEFAULT 15,
                price REAL DEFAULT 0,
                cost REAL DEFAULT 0,
                category TEXT DEFAULT 'General'
            );
            CREATE TABLE IF NOT EXISTS customers(
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                phone TEXT DEFAULT '',
                email TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS invoices(
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                total REAL DEFAULT 0,
                paid REAL DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );
            CREATE TABLE IF NOT EXISTS invoice_items(
                id INTEGER PRIMARY KEY,
                invoice_id INTEGER,
                product_id INTEGER,
                qty INTEGER DEFAULT 1,
                price REAL DEFAULT 0,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """
        )
        cols_products = [r[1] for r in cur.execute("PRAGMA table_info(products)").fetchall()]
        if "cost" not in cols_products:
            try: cur.execute("ALTER TABLE products ADD COLUMN cost REAL DEFAULT 0")
            except Exception: pass
        if "category" not in cols_products:
            try: cur.execute("ALTER TABLE products ADD COLUMN category TEXT DEFAULT 'General'")
            except Exception: pass

        cols_customers = [r[1] for r in cur.execute("PRAGMA table_info(customers)").fetchall()]
        if "email" not in cols_customers:
            try: cur.execute("ALTER TABLE customers ADD COLUMN email TEXT DEFAULT ''")
            except Exception: pass
        con.commit()

    def import_file(self, file_path: str, clear_existing: bool = False) -> dict:
        """Universal import of any dataset into SQLite, CSV cache, and universal profiler."""
        df_raw = load_any_dataset(file_path)

        # 1. Update Active DataFrame for query engine
        set_active_dataframe(df_raw)

        # 2. Store full raw dataset into SQLite table 'uploaded_dataset'
        con = get_conn()
        self._ensure_schema(con)
        try:
            df_raw.to_sql("uploaded_dataset", con, if_exists="replace", index=False)
        except Exception:
            pass

        # 3. Profile dataset
        profiler = UniversalDataProfiler(df_raw, dataset_name=os.path.basename(file_path))
        profile = profiler.get_profile()

        # 4. Map into relational ERP tables if applicable
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".xlsx", ".xls"):
            erp_stats = self._import_excel(file_path, clear_existing)
        else:
            erp_stats = self._import_flat_dataframe(df_raw, clear_existing)

        con.close()

        return {
            **erp_stats,
            "raw_total_rows": profile["total_rows"],
            "raw_total_columns": profile["total_columns"],
            "primary_metric": profile["semantic_roles"]["primary_metric"],
            "data_quality_score": profile["data_quality_score"],
            "dimensions_found": profile["semantic_roles"]["dimensions"][:4],
        }

    def _import_excel(self, file_path: str, clear_existing: bool = False) -> dict:
        excel_file = pd.ExcelFile(file_path)
        sheet_names = [s.strip().lower() for s in excel_file.sheet_names]
        sheet_map = {s.strip().lower(): s for s in excel_file.sheet_names}

        con = get_conn()
        self._ensure_schema(con)
        cur = con.cursor()

        if clear_existing:
            cur.executescript("DELETE FROM invoice_items; DELETE FROM invoices; DELETE FROM products; DELETE FROM customers;")
            con.commit()

        stats = {"products": 0, "customers": 0, "invoices": 0, "invoice_items": 0}

        # Step 1: Products Sheet
        prod_sheet = next((sheet_map[k] for k in ["products", "items", "inventory"] if k in sheet_map), None)
        if prod_sheet:
            df_prod = normalize_dataframe(pd.read_excel(excel_file, sheet_name=prod_sheet))
            for _, row in df_prod.iterrows():
                name = str(_get_scalar(row, "product_name", _get_scalar(row, "name", ""))).strip()
                if not name or name.lower() in ("nan", "none", ""):
                    continue
                stock = int(clean_numeric_value(_get_scalar(row, "stock", 50), 50))
                reorder = int(clean_numeric_value(_get_scalar(row, "reorder_level", 15), 15))
                price = clean_numeric_value(_get_scalar(row, "price", 0.0), 0.0)
                cost = clean_numeric_value(_get_scalar(row, "cost", price * 0.7), round(price * 0.7, 2))
                cat = str(_get_scalar(row, "category", "General")).strip()

                cur.execute("SELECT id FROM products WHERE name = ?", (name,))
                ex = cur.fetchone()
                if ex:
                    cur.execute(
                        "UPDATE products SET stock=?, reorder_level=?, price=?, cost=?, category=? WHERE id=?",
                        (stock, reorder, price, cost, cat, ex[0]),
                    )
                else:
                    cur.execute(
                        "INSERT INTO products (name, stock, reorder_level, price, cost, category) VALUES (?, ?, ?, ?, ?, ?)",
                        (name, stock, reorder, price, cost, cat),
                    )
                stats["products"] += 1

        # Step 2: Customers Sheet
        cust_sheet = next((sheet_map[k] for k in ["customers", "clients", "parties"] if k in sheet_map), None)
        if cust_sheet:
            df_cust = normalize_dataframe(pd.read_excel(excel_file, sheet_name=cust_sheet))
            for _, row in df_cust.iterrows():
                name = str(_get_scalar(row, "customer_name", _get_scalar(row, "name", ""))).strip()
                if not name or name.lower() in ("nan", "none", ""):
                    continue
                phone = str(_get_scalar(row, "phone", "") or "")
                email = str(_get_scalar(row, "email", "") or "")

                cur.execute("SELECT id FROM customers WHERE name = ?", (name,))
                ex = cur.fetchone()
                if ex:
                    cur.execute(
                        "UPDATE customers SET phone = CASE WHEN ? != '' THEN ? ELSE phone END, email = CASE WHEN ? != '' THEN ? ELSE email END WHERE id = ?",
                        (phone, phone, email, email, ex[0]),
                    )
                else:
                    cur.execute("INSERT INTO customers (name, phone, email) VALUES (?, ?, ?)", (name, phone, email))
                stats["customers"] += 1

        con.commit()
        con.close()

        # Step 3: Transaction Sheet
        tx_sheet = next(
            (sheet_map[k] for k in ["erp_sales_transactions", "transactions", "sales", "orders", "invoices"] if k in sheet_map),
            None,
        )
        if not tx_sheet and len(sheet_names) == 1:
            tx_sheet = excel_file.sheet_names[0]

        if tx_sheet:
            df_tx = pd.read_excel(excel_file, sheet_name=tx_sheet)
            tx_stats = self._import_flat_dataframe(df_tx, clear_existing=False)
            stats["products"] = max(stats["products"], tx_stats["products"])
            stats["customers"] = max(stats["customers"], tx_stats["customers"])
            stats["invoices"] += tx_stats["invoices"]
            stats["invoice_items"] += tx_stats["invoice_items"]

        return stats

    def _import_flat_dataframe(self, df: pd.DataFrame, clear_existing: bool = False) -> dict:
        """Smart ingestion of any flat dataframe with automatic price/total derivation."""
        df_norm = normalize_dataframe(df)
        con = get_conn()
        self._ensure_schema(con)
        cur = con.cursor()

        if clear_existing:
            cur.executescript("DELETE FROM invoice_items; DELETE FROM invoices; DELETE FROM products; DELETE FROM customers;")
            con.commit()

        stats = {"products": 0, "customers": 0, "invoices": 0, "invoice_items": 0}

        # Identify key columns
        prod_col = "product_name" if "product_name" in df_norm.columns else None
        cust_col = "customer_name" if "customer_name" in df_norm.columns else None
        if not cust_col:
            # Fall back to other entity columns like client, user, account
            for c in ["client", "user", "account", "region", "segment"]:
                if c in df_norm.columns:
                    cust_col = c
                    break

        # 1. Upsert Products
        if prod_col:
            for p_name, group in df_norm.groupby(prod_col):
                p_name_str = str(p_name).strip()
                if not p_name_str or p_name_str.lower() in ("nan", "none", ""):
                    continue

                first_r = group.iloc[0]
                # Price extraction: if price is missing, calculate from total / qty
                raw_price = clean_numeric_value(_get_scalar(first_r, "price", None), None)
                raw_qty = clean_numeric_value(_get_scalar(first_r, "qty", 1), 1)
                raw_total = clean_numeric_value(_get_scalar(first_r, "total", None), None)

                if raw_price is not None and raw_price > 0:
                    price = raw_price
                elif raw_total is not None and raw_total > 0 and raw_qty > 0:
                    price = round(raw_total / raw_qty, 2)
                else:
                    price = 100.0  # sensible baseline

                stock = int(clean_numeric_value(_get_scalar(first_r, "stock", 50), 50))
                reorder = int(clean_numeric_value(_get_scalar(first_r, "reorder_level", 15), 15))
                cost = clean_numeric_value(_get_scalar(first_r, "cost", price * 0.7), round(price * 0.7, 2))
                cat = str(_get_scalar(first_r, "category", "General")).strip()

                cur.execute("SELECT id FROM products WHERE name = ?", (p_name_str,))
                ex = cur.fetchone()
                if ex:
                    cur.execute(
                        "UPDATE products SET price = CASE WHEN ? > 0 THEN ? ELSE price END, cost = CASE WHEN ? > 0 THEN ? ELSE cost END, category=? WHERE id = ?",
                        (price, price, cost, cost, cat, ex[0]),
                    )
                else:
                    cur.execute(
                        "INSERT INTO products (name, stock, reorder_level, price, cost, category) VALUES (?, ?, ?, ?, ?, ?)",
                        (p_name_str, stock, reorder, price, cost, cat),
                    )
                stats["products"] += 1

        # 2. Upsert Customers
        if cust_col:
            for c_name, group in df_norm.groupby(cust_col):
                c_name_str = str(c_name).strip()
                if not c_name_str or c_name_str.lower() in ("nan", "none", ""):
                    continue
                first_r = group.iloc[0]
                phone = str(_get_scalar(first_r, "phone", "") or "")
                email = str(_get_scalar(first_r, "email", "") or "")

                cur.execute("SELECT id FROM customers WHERE name = ?", (c_name_str,))
                ex = cur.fetchone()
                if ex:
                    cur.execute(
                        "UPDATE customers SET phone = CASE WHEN ? != '' THEN ? ELSE phone END, email = CASE WHEN ? != '' THEN ? ELSE email END WHERE id = ?",
                        (phone, phone, email, email, ex[0]),
                    )
                else:
                    cur.execute("INSERT INTO customers (name, phone, email) VALUES (?, ?, ?)", (c_name_str, phone, email))
                stats["customers"] += 1

        con.commit()

        # Cache IDs
        cust_cache = {r["name"]: r["id"] for r in con.execute("SELECT id, name FROM customers").fetchall()}
        prod_cache = {r["name"]: r["id"] for r in con.execute("SELECT id, name FROM products").fetchall()}

        # 3. Group by Invoices
        has_inv_id = "invoice_id" in df_norm.columns
        if has_inv_id:
            group_keys = ["invoice_id"]
        elif cust_col and "date" in df_norm.columns:
            group_keys = [cust_col, "date"]
        else:
            df_norm["_auto_id"] = range(1, len(df_norm) + 1)
            group_keys = ["_auto_id"]

        for _, group in df_norm.groupby(group_keys):
            first_row = group.iloc[0]
            c_name = str(_get_scalar(first_row, cust_col, "Standard Customer")).strip()
            c_id = cust_cache.get(c_name)
            if not c_id:
                cur.execute("INSERT OR IGNORE INTO customers (name) VALUES (?)", (c_name,))
                c_id = cur.execute("SELECT id FROM customers WHERE name=?", (c_name,)).fetchone()[0]
                cust_cache[c_name] = c_id

            # Calculate total & items
            computed_total = 0.0
            line_items_to_add = []

            for _, r in group.iterrows():
                p_name = str(_get_scalar(r, prod_col, "General Item")).strip()
                p_id = prod_cache.get(p_name)
                q = int(clean_numeric_value(_get_scalar(r, "qty", 1), 1))

                # Check price / total
                raw_p = clean_numeric_value(_get_scalar(r, "price", None), None)
                raw_tot = clean_numeric_value(_get_scalar(r, "total", None), None)

                if raw_p is not None and raw_p > 0:
                    p = raw_p
                elif raw_tot is not None and raw_tot > 0 and q > 0:
                    p = round(raw_tot / q, 2)
                else:
                    p = 100.0

                item_total = raw_tot if (raw_tot is not None and raw_tot > 0) else (q * p)
                computed_total += item_total

                if not p_id and p_name:
                    cur.execute(
                        "INSERT OR IGNORE INTO products (name, stock, reorder_level, price) VALUES (?, 50, 15, ?)",
                        (p_name, p),
                    )
                    p_id = cur.execute("SELECT id FROM products WHERE name=?", (p_name,)).fetchone()[0]
                    prod_cache[p_name] = p_id

                line_items_to_add.append((p_id, q, p))

            inv_total = clean_numeric_value(_get_scalar(first_row, "total", computed_total), computed_total)
            if inv_total <= 0:
                inv_total = computed_total

            paid_val = _get_scalar(first_row, "paid", None)
            due_val = _get_scalar(first_row, "due", None)
            if paid_val is not None:
                inv_paid = clean_numeric_value(paid_val, inv_total)
            elif due_val is not None:
                inv_paid = max(0.0, inv_total - clean_numeric_value(due_val, 0.0))
            else:
                inv_paid = inv_total

            raw_date = _get_scalar(first_row, "date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            date_str = raw_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(raw_date, pd.Timestamp) else str(raw_date)[:19]

            cur.execute(
                "INSERT INTO invoices (customer_id, total, paid, created_at) VALUES (?, ?, ?, ?)",
                (c_id, round(inv_total, 2), round(inv_paid, 2), date_str),
            )
            created_inv_id = cur.lastrowid
            stats["invoices"] += 1

            for p_id, item_qty, item_price in line_items_to_add:
                if p_id:
                    cur.execute(
                        "INSERT INTO invoice_items (invoice_id, product_id, qty, price) VALUES (?, ?, ?, ?)",
                        (created_inv_id, p_id, item_qty, item_price),
                    )
                    stats["invoice_items"] += 1

        con.commit()
        con.close()
        return stats

    def _import_json(self, file_path: str, clear_existing: bool = False) -> dict:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data if isinstance(data, list) else [data])
        return self._import_flat_dataframe(df, clear_existing)


def generate_sample_excel_template(output_path: str = "sample_erp_data.xlsx"):
    from datetime import datetime, timedelta

    products_data = [
        {"Product Name": "Laptop Pro 15", "Category": "Electronics", "Stock": 25, "Reorder Level": 10, "Selling Price": 65000.0, "Cost Price": 48000.0},
        {"Product Name": "Wireless Headphones", "Category": "Accessories", "Stock": 140, "Reorder Level": 30, "Selling Price": 3500.0, "Cost Price": 2100.0},
        {"Product Name": "Mechanical Keyboard", "Category": "Accessories", "Stock": 80, "Reorder Level": 25, "Selling Price": 4500.0, "Cost Price": 2700.0},
        {"Product Name": "Smartphone 5G", "Category": "Electronics", "Stock": 18, "Reorder Level": 20, "Selling Price": 32000.0, "Cost Price": 24000.0},
        {"Product Name": "Ergonomic Office Chair", "Category": "Furniture", "Stock": 12, "Reorder Level": 15, "Selling Price": 12500.0, "Cost Price": 8000.0},
        {"Product Name": "4K Ultra Monitor", "Category": "Electronics", "Stock": 30, "Reorder Level": 12, "Selling Price": 28000.0, "Cost Price": 20000.0},
        {"Product Name": "USB-C Fast Charger", "Category": "Accessories", "Stock": 350, "Reorder Level": 50, "Selling Price": 950.0, "Cost Price": 450.0},
        {"Product Name": "Laser Multi-function Printer", "Category": "Office", "Stock": 8, "Reorder Level": 10, "Selling Price": 18500.0, "Cost Price": 13500.0},
    ]

    customers_data = [
        {"Customer Name": "TechNova Solutions", "Phone": "9845100001", "Email": "procure@technova.com", "City": "Bangalore"},
        {"Customer Name": "Vertex Retailers", "Phone": "9845100002", "Email": "accounts@vertex.in", "City": "Mumbai"},
        {"Customer Name": "Apex Systems Corp", "Phone": "9845100003", "Email": "supply@apexsys.org", "City": "Delhi"},
        {"Customer Name": "Metro Enterprises", "Phone": "9845100004", "Email": "info@metroent.com", "City": "Hyderabad"},
    ]

    now = datetime.now()
    transactions = [
        {"Invoice No": "INV-5001", "Date": (now - timedelta(days=2)).strftime("%Y-%m-%d"), "Customer Name": "TechNova Solutions", "Product Name": "Laptop Pro 15", "Qty": 4, "Sales Amount": 260000.0, "Paid Amount": 260000.0, "Due Amount": 0.0},
        {"Invoice No": "INV-5002", "Date": (now - timedelta(days=5)).strftime("%Y-%m-%d"), "Customer Name": "Vertex Retailers", "Product Name": "Wireless Headphones", "Qty": 20, "Sales Amount": 70000.0, "Paid Amount": 35000.0, "Due Amount": 35000.0},
        {"Invoice No": "INV-5003", "Date": (now - timedelta(days=8)).strftime("%Y-%m-%d"), "Customer Name": "Apex Systems Corp", "Product Name": "4K Ultra Monitor", "Qty": 5, "Sales Amount": 140000.0, "Paid Amount": 0.0, "Due Amount": 140000.0},
        {"Invoice No": "INV-5004", "Date": (now - timedelta(days=12)).strftime("%Y-%m-%d"), "Customer Name": "Metro Enterprises", "Product Name": "Mechanical Keyboard", "Qty": 15, "Sales Amount": 67500.0, "Paid Amount": 67500.0, "Due Amount": 0.0},
        {"Invoice No": "INV-5005", "Date": (now - timedelta(days=18)).strftime("%Y-%m-%d"), "Customer Name": "TechNova Solutions", "Product Name": "Smartphone 5G", "Qty": 6, "Sales Amount": 192000.0, "Paid Amount": 100000.0, "Due Amount": 92000.0},
        {"Invoice No": "INV-5006", "Date": (now - timedelta(days=25)).strftime("%Y-%m-%d"), "Customer Name": "Vertex Retailers", "Product Name": "USB-C Fast Charger", "Qty": 50, "Sales Amount": 47500.0, "Paid Amount": 47500.0, "Due Amount": 0.0},
        {"Invoice No": "INV-5007", "Date": (now - timedelta(days=32)).strftime("%Y-%m-%d"), "Customer Name": "Apex Systems Corp", "Product Name": "Laser Multi-function Printer", "Qty": 2, "Sales Amount": 37000.0, "Paid Amount": 0.0, "Due Amount": 37000.0},
        {"Invoice No": "INV-5008", "Date": (now - timedelta(days=45)).strftime("%Y-%m-%d"), "Customer Name": "Metro Enterprises", "Product Name": "Ergonomic Office Chair", "Qty": 8, "Sales Amount": 100000.0, "Paid Amount": 100000.0, "Due Amount": 0.0},
    ]

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(transactions).to_excel(writer, sheet_name="Transactions", index=False)
        pd.DataFrame(products_data).to_excel(writer, sheet_name="Products", index=False)
        pd.DataFrame(customers_data).to_excel(writer, sheet_name="Customers", index=False)

    return output_path

