from database import get_db, init_db
from datetime import date, timedelta
import random

random.seed(42)

stores = [
    ("Chennai Central", "Chennai", "North Tamil Nadu"),
    ("Coimbatore Hub", "Coimbatore", "West Tamil Nadu"),
    ("Madurai Main", "Madurai", "South Tamil Nadu"),
    ("Trichy Plaza", "Tiruchirappalli", "Central Tamil Nadu"),
    ("Salem Point", "Salem", "West Tamil Nadu"),
]

products = [
    ("Wireless Mouse", "Computer Accessories", 799),
    ("Mechanical Keyboard", "Computer Accessories", 2499),
    ("Laptop Stand", "Computer Accessories", 1599),
    ("USB-C Hub", "Computer Accessories", 1299),
    ("Bluetooth Speaker", "Audio", 1899),
    ("Power Bank", "Mobile Accessories", 1499),
    ("Webcam HD", "Computer Accessories", 2299),
    ("Desk Lamp", "Office", 999),
    ("Notebook Pack", "Stationery", 349),
    ("Smartphone Tripod", "Mobile Accessories", 899),
]

def main():
    init_db()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM weekly_demand")
    cur.execute("DELETE FROM inventory")
    cur.execute("DELETE FROM products")
    cur.execute("DELETE FROM stores")

    cur.executemany(
        "INSERT INTO stores(name, city, region) VALUES (?, ?, ?)", stores
    )
    cur.executemany(
        "INSERT INTO products(name, category, unit_price) VALUES (?, ?, ?)", products
    )
    conn.commit()

    store_rows = cur.execute("SELECT id, name FROM stores").fetchall()
    product_rows = cur.execute("SELECT id, name FROM products").fetchall()

    base_demand = {
        "Wireless Mouse": 42,
        "Mechanical Keyboard": 27,
        "Laptop Stand": 31,
        "USB-C Hub": 36,
        "Bluetooth Speaker": 24,
        "Power Bank": 39,
        "Webcam HD": 18,
        "Desk Lamp": 28,
        "Notebook Pack": 55,
        "Smartphone Tripod": 22,
    }

    # 26 weeks of realistic demand history.
    start = date.today() - timedelta(days=25 * 7)
    demand_rows = []

    for store_id, store_name in store_rows:
        store_factor = {
            "Chennai Central": 1.25,
            "Coimbatore Hub": 1.08,
            "Madurai Main": 0.92,
            "Trichy Plaza": 0.84,
            "Salem Point": 0.76,
        }[store_name]

        for product_id, product_name in product_rows:
            product_factor = 1 + random.uniform(-0.12, 0.12)
            for w in range(26):
                week = start + timedelta(days=w * 7)
                trend = 1 + (w * random.uniform(0.002, 0.012))
                season = 1 + 0.10 * ((w % 6) / 5)
                noise = random.uniform(0.82, 1.18)

                units = round(
                    base_demand[product_name]
                    * store_factor
                    * product_factor
                    * trend
                    * season
                    * noise
                )

                # A few intentional demand spikes for anomaly detection.
                if (store_name, product_name, w) in [
                    ("Chennai Central", "Wireless Mouse", 24),
                    ("Madurai Main", "Power Bank", 23),
                    ("Coimbatore Hub", "Laptop Stand", 25),
                ]:
                    units = round(units * 1.8)

                demand_rows.append(
                    (store_id, product_id, week.isoformat(), max(1, units))
                )

    cur.executemany(
        """INSERT INTO weekly_demand
        (store_id, product_id, week_start, units_sold)
        VALUES (?, ?, ?, ?)""",
        demand_rows,
    )

    # Inventory is intentionally mixed so the dashboard demonstrates risk.
    inventory_rows = []
    for store_id, store_name in store_rows:
        for product_id, product_name in product_rows:
            recent = cur.execute(
                """SELECT AVG(units_sold) FROM weekly_demand
                   WHERE store_id=? AND product_id=?
                   ORDER BY week_start DESC LIMIT 4""",
                (store_id, product_id),
            ).fetchone()[0] or 10

            reorder_point = max(8, round(recent * 0.65))
            lead_time = random.choice([3, 5, 7, 10])
            stock = max(
                0,
                round(recent * random.uniform(0.25, 1.45))
            )

            # Deliberate low-stock examples.
            if product_name in ["Wireless Mouse", "Power Bank"] and store_name == "Chennai Central":
                stock = max(2, round(recent * 0.15))

            inventory_rows.append(
                (
                    store_id,
                    product_id,
                    stock,
                    reorder_point,
                    lead_time,
                    date.today().isoformat(),
                )
            )

    cur.executemany(
        """INSERT INTO inventory
        (store_id, product_id, stock_qty, reorder_point, lead_time_days, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)""",
        inventory_rows,
    )

    conn.commit()
    conn.close()
    print("DemandPulse database created successfully: demandpulse.db")

if __name__ == "__main__":
    main()
