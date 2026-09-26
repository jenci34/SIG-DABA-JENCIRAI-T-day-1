import re
from database import get_db

def clean_text(text):
    return re.sub(r"\s+", " ", text.strip().lower())

def find_store(text, conn):
    stores = conn.execute("SELECT name FROM stores").fetchall()
    for row in stores:
        if row["name"].lower() in text:
            return row["name"]
    return None

def find_product(text, conn):
    products = conn.execute("SELECT name FROM products").fetchall()
    for row in products:
        if row["name"].lower() in text:
            return row["name"]
    return None

def build_query(question):
    """
    Converts a controlled set of natural-language manager requests
    into parameterized SQLite SQL. This intentionally avoids executing
    arbitrary SQL supplied by a user.
    """
    q = clean_text(question)
    conn = get_db()

    store = find_store(q, conn)
    product = find_product(q, conn)

    params = []
    where = []

    if store:
        where.append("s.name = ?")
        params.append(store)

    if product:
        where.append("p.name = ?")
        params.append(product)

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    # Explicit inventory filters.
    match = re.search(r"(?:below|under|less than)\s+(\d+)", q)
    if match and any(k in q for k in ["stock", "inventory", "units"]):
        where_sql += (" AND " if where_sql else " WHERE ") + "i.stock_qty < ?"
        params.append(int(match.group(1)))
        sql = f"""
        SELECT s.name AS store, p.name AS product, p.category,
               i.stock_qty, i.reorder_point, i.lead_time_days
        FROM inventory i
        JOIN stores s ON s.id=i.store_id
        JOIN products p ON p.id=i.product_id
        {where_sql}
        ORDER BY i.stock_qty ASC
        LIMIT 50
        """
        conn.close()
        return sql, params, "Inventory below threshold"

    if any(k in q for k in ["low stock", "low inventory", "short stock", "stockout", "out of stock"]):
        extra = (" AND " if where_sql else " WHERE ") + "i.stock_qty <= i.reorder_point"
        sql = f"""
        SELECT s.name AS store, p.name AS product, p.category,
               i.stock_qty, i.reorder_point, i.lead_time_days
        FROM inventory i
        JOIN stores s ON s.id=i.store_id
        JOIN products p ON p.id=i.product_id
        {where_sql}{extra}
        ORDER BY i.stock_qty ASC
        LIMIT 50
        """
        conn.close()
        return sql, params, "Low-stock inventory"

    if any(k in q for k in ["top products", "highest demand", "most demanded", "best selling"]):
        sql = f"""
        SELECT p.name AS product, p.category, SUM(w.units_sold) AS total_demand
        FROM weekly_demand w
        JOIN products p ON p.id=w.product_id
        JOIN stores s ON s.id=w.store_id
        {where_sql}
        GROUP BY p.id
        ORDER BY total_demand DESC
        LIMIT 10
        """
        conn.close()
        return sql, params, "Top products by demand"

    if any(k in q for k in ["demand", "sales", "sold"]):
        sql = f"""
        SELECT s.name AS store, p.name AS product,
               w.week_start, w.units_sold
        FROM weekly_demand w
        JOIN stores s ON s.id=w.store_id
        JOIN products p ON p.id=w.product_id
        {where_sql}
        ORDER BY w.week_start DESC
        LIMIT 30
        """
        conn.close()
        return sql, params, "Weekly demand history"

    if any(k in q for k in ["inventory", "stock", "available"]):
        sql = f"""
        SELECT s.name AS store, p.name AS product, p.category,
               i.stock_qty, i.reorder_point, i.lead_time_days
        FROM inventory i
        JOIN stores s ON s.id=i.store_id
        JOIN products p ON p.id=i.product_id
        {where_sql}
        ORDER BY i.stock_qty ASC
        LIMIT 50
        """
        conn.close()
        return sql, params, "Inventory levels"

    # Smart reorder request.
    if any(k in q for k in ["reorder", "restock", "purchase"]):
        sql = f"""
        SELECT s.name AS store, p.name AS product,
               i.stock_qty, i.reorder_point, i.lead_time_days
        FROM inventory i
        JOIN stores s ON s.id=i.store_id
        JOIN products p ON p.id=i.product_id
        {where_sql}
        ORDER BY i.stock_qty ASC
        LIMIT 50
        """
        conn.close()
        return sql, params, "Replenishment candidates"

    conn.close()
    return None, [], "I can answer inventory, demand, low-stock, top-product and reorder questions."

def run_nl_query(question):
    sql, params, title = build_query(question)
    if not sql:
        return {
            "title": title,
            "sql": "",
            "columns": [],
            "rows": [],
            "error": title,
        }

    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return {
        "title": title,
        "sql": " ".join(sql.split()),
        "columns": list(rows[0].keys()) if rows else [],
        "rows": [dict(r) for r in rows],
        "error": None,
    }
