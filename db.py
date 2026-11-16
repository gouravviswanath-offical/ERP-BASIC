"""Mock ERP database for a small trading business (SQLite)."""
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "erp.db"


def get_conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = get_conn()
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY, name TEXT, stock INTEGER,
            reorder_level INTEGER, price REAL);
        CREATE TABLE IF NOT EXISTS customers(
            id INTEGER PRIMARY KEY, name TEXT, phone TEXT);
        CREATE TABLE IF NOT EXISTS invoices(
            id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL,
            paid REAL DEFAULT 0, created_at TEXT);
        CREATE TABLE IF NOT EXISTS invoice_items(
            id INTEGER PRIMARY KEY, invoice_id INTEGER,
            product_id INTEGER, qty INTEGER, price REAL);
        """
    )
    if cur.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        products = [
            (1, "Tomato (kg)", 120, 50, 30),
            (2, "Onion (kg)", 40, 60, 25),
            (3, "Potato (kg)", 200, 80, 22),
            (4, "Carrot (kg)", 35, 40, 40),
        ]
        cur.executemany("INSERT INTO products VALUES(?,?,?,?,?)", products)
        price = {p[0]: p[4] for p in products}

        cur.executemany(
            "INSERT INTO customers VALUES(?,?,?)",
            [(1, "Raju Stores", "9999900001"),
             (2, "Anil Traders", "9999900002"),
             (3, "Fresh Mart", "9999900003")],
        )
        # (customer_id, days_ago, [(product_id, qty)], fraction_paid)
        sales = [
            (1, 1, [(1, 20), (3, 30)], 1.0),
            (2, 2, [(2, 25), (4, 10)], 0.5),
            (3, 3, [(1, 15), (2, 10)], 0.0),
            (1, 6, [(3, 40)], 1.0),
            (2, 10, [(1, 30), (4, 20)], 0.0),
            (3, 20, [(3, 50), (2, 15)], 1.0),
        ]
        for i, (cust, days_ago, items, frac) in enumerate(sales, start=1):
            total = sum(price[p] * q for p, q in items)
            when = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO invoices VALUES(?,?,?,?,?)",
                (i, cust, total, round(total * frac, 2), when),
            )
            for p, q in items:
                cur.execute(
                    "INSERT INTO invoice_items(invoice_id, product_id, qty, price) VALUES(?,?,?,?)",
                    (i, p, q, price[p]),
                )
    con.commit()
    con.close()


if __name__ == "__main__":
    init_db()
    print("DB ready:", DB_PATH)
