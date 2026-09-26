import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "demandpulse.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS stores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        city TEXT NOT NULL,
        region TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        unit_price REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        stock_qty INTEGER NOT NULL DEFAULT 0,
        reorder_point INTEGER NOT NULL DEFAULT 10,
        lead_time_days INTEGER NOT NULL DEFAULT 5,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(store_id, product_id),
        FOREIGN KEY(store_id) REFERENCES stores(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS weekly_demand (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        week_start TEXT NOT NULL,
        units_sold INTEGER NOT NULL,
        UNIQUE(store_id, product_id, week_start),
        FOREIGN KEY(store_id) REFERENCES stores(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );
    """)
    conn.commit()
    conn.close()
