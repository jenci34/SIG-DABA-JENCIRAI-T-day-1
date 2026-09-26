from flask import Flask, render_template, request, jsonify
from database import get_db, init_db
from forecasting import forecast_series, stockout_risk, reorder_quantity
from nl_sql import run_nl_query

app = Flask(__name__)
app.config["SECRET_KEY"] = "demandpulse360-demo-key"

init_db()

def scalar(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else 0

@app.route("/")
def dashboard():
    conn = get_db()

    stores = conn.execute("SELECT * FROM stores ORDER BY name").fetchall()
    products = conn.execute("SELECT * FROM products ORDER BY name").fetchall()

    total_stock = scalar(conn, "SELECT COALESCE(SUM(stock_qty),0) FROM inventory")
    low_stock = scalar(
        conn,
        "SELECT COUNT(*) FROM inventory WHERE stock_qty <= reorder_point"
    )
    total_demand = scalar(
        conn,
        """SELECT COALESCE(SUM(units_sold),0) FROM weekly_demand
           WHERE week_start >= date('now','-28 days')"""
    )

    # Estimate current forecast and risk across all inventory records.
    records = conn.execute("""
        SELECT i.*, s.name AS store_name, p.name AS product_name
        FROM inventory i
        JOIN stores s ON s.id=i.store_id
        JOIN products p ON p.id=i.product_id
        ORDER BY i.stock_qty ASC
    """).fetchall()

    risk_rows = []
    for item in records:
        history = conn.execute("""
            SELECT week_start, units_sold
            FROM weekly_demand
            WHERE store_id=? AND product_id=?
            ORDER BY week_start ASC
        """, (item["store_id"], item["product_id"])).fetchall()

        forecast = forecast_series(history, 4)
        weekly = forecast[0]["demand"] if forecast else 0
        risk, label = stockout_risk(
            item["stock_qty"], weekly, item["lead_time_days"]
        )
        reorder = reorder_quantity(
            item["stock_qty"], weekly, item["lead_time_days"]
        )

        risk_rows.append({
            "store": item["store_name"],
            "product": item["product_name"],
            "stock": item["stock_qty"],
            "weekly_forecast": weekly,
            "risk": risk,
            "risk_label": label,
            "reorder": reorder
        })

    high_risk = sum(1 for r in risk_rows if r["risk"] >= 65)
    top_risk = sorted(risk_rows, key=lambda x: x["risk"], reverse=True)[:8]

    # Chart data.
    weekly_chart = conn.execute("""
        SELECT week_start, SUM(units_sold) AS units
        FROM weekly_demand
        GROUP BY week_start
        ORDER BY week_start DESC
        LIMIT 12
    """).fetchall()
    weekly_chart = list(reversed(weekly_chart))

    category_chart = conn.execute("""
        SELECT p.category, SUM(w.units_sold) AS units
        FROM weekly_demand w
        JOIN products p ON p.id=w.product_id
        GROUP BY p.category
        ORDER BY units DESC
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        stores=stores,
        products=products,
        total_stock=total_stock,
        low_stock=low_stock,
        total_demand=total_demand,
        high_risk=high_risk,
        top_risk=top_risk,
        weekly_labels=[r["week_start"] for r in weekly_chart],
        weekly_values=[r["units"] for r in weekly_chart],
        category_labels=[r["category"] for r in category_chart],
        category_values=[r["units"] for r in category_chart],
    )

@app.route("/forecast")
def forecast_page():
    conn = get_db()
    store_id = request.args.get("store_id", "")
    product_id = request.args.get("product_id", "")

    stores = conn.execute("SELECT * FROM stores ORDER BY name").fetchall()
    products = conn.execute("SELECT * FROM products ORDER BY name").fetchall()

    selected = None
    forecast = []
    history = []

    if store_id and product_id:
        selected = conn.execute("""
            SELECT s.name AS store_name, p.name AS product_name,
                   i.stock_qty, i.reorder_point, i.lead_time_days
            FROM inventory i
            JOIN stores s ON s.id=i.store_id
            JOIN products p ON p.id=i.product_id
            WHERE i.store_id=? AND i.product_id=?
        """, (store_id, product_id)).fetchone()

        history = conn.execute("""
            SELECT week_start, units_sold
            FROM weekly_demand
            WHERE store_id=? AND product_id=?
            ORDER BY week_start
        """, (store_id, product_id)).fetchall()

        forecast = forecast_series(history, 4)

    conn.close()

    return render_template(
        "forecast.html",
        stores=stores,
        products=products,
        selected=selected,
        history=history,
        forecast=forecast,
    )

@app.route("/replenishment")
def replenishment():
    conn = get_db()
    records = conn.execute("""
        SELECT i.*, s.name AS store_name, p.name AS product_name
        FROM inventory i
        JOIN stores s ON s.id=i.store_id
        JOIN products p ON p.id=i.product_id
    """).fetchall()

    rows = []
    for item in records:
        history = conn.execute("""
            SELECT week_start, units_sold
            FROM weekly_demand
            WHERE store_id=? AND product_id=?
            ORDER BY week_start
        """, (item["store_id"], item["product_id"])).fetchall()

        forecast = forecast_series(history, 4)
        weekly = forecast[0]["demand"] if forecast else 0
        risk, label = stockout_risk(
            item["stock_qty"], weekly, item["lead_time_days"]
        )
        reorder = reorder_quantity(
            item["stock_qty"], weekly, item["lead_time_days"]
        )

        rows.append({
            "store": item["store_name"],
            "product": item["product_name"],
            "stock": item["stock_qty"],
            "forecast": weekly,
            "lead_time": item["lead_time_days"],
            "risk": risk,
            "risk_label": label,
            "reorder": reorder
        })

    conn.close()
    rows.sort(key=lambda x: (x["risk"], x["reorder"]), reverse=True)

    return render_template("replenishment.html", rows=rows)

@app.route("/sql")
def sql_page():
    return render_template("sql.html")

@app.post("/api/sql")
def api_sql():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "Please enter a question."}), 400

    result = run_nl_query(question)
    return jsonify(result)

@app.get("/api/what-if")
def what_if():
    store_id = request.args.get("store_id")
    product_id = request.args.get("product_id")
    growth = float(request.args.get("growth", 0))
    lead_time = int(request.args.get("lead_time", 7))

    conn = get_db()
    history = conn.execute("""
        SELECT week_start, units_sold
        FROM weekly_demand
        WHERE store_id=? AND product_id=?
        ORDER BY week_start
    """, (store_id, product_id)).fetchall()
    inventory = conn.execute("""
        SELECT stock_qty
        FROM inventory
        WHERE store_id=? AND product_id=?
    """, (store_id, product_id)).fetchone()
    conn.close()

    if not history or not inventory:
        return jsonify({"error": "Select a valid store and product."}), 400

    forecast = forecast_series(history, 4)
    adjusted = []
    for item in forecast:
        demand = round(item["demand"] * (1 + growth / 100))
        adjusted.append({"week": item["week"], "demand": demand})

    avg = sum(x["demand"] for x in adjusted) / len(adjusted)
    risk, label = stockout_risk(inventory["stock_qty"], avg, lead_time)
    reorder = reorder_quantity(inventory["stock_qty"], avg, lead_time)

    return jsonify({
        "forecast": adjusted,
        "stock": inventory["stock_qty"],
        "risk": risk,
        "risk_label": label,
        "reorder": reorder
    })

if __name__ == "__main__":
    app.run(debug=True)
