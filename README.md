# DemandPulse 360

A Flask-based business analytics project that predicts weekly product demand across multiple stores and provides a natural-language-to-SQL interface for inventory queries.

## Innovative features

1. **Weekly demand forecasting** by store and product using a trend + recent-demand model.
2. **Stockout Risk Score** based on forecast demand, current stock and supplier lead time.
3. **Smart Replenishment** recommendation with suggested order quantity.
4. **Natural Language SQL** interface that converts safe, predefined manager questions into SQL.
5. **What-if simulator** to test demand growth and lead-time changes.
6. **Demand anomaly flagging** for unusually high/low recent demand.
7. **Manager dashboard** with KPI cards and interactive charts.
8. **No paid AI API required** for the natural-language query feature.

## Run on Windows

Open PowerShell in this folder:

```powershell
python -m venv venv
.env\Scripts\Activate.ps1
pip install -r requirements.txt
python seed_data.py
python app.py
```

Then open:

http://127.0.0.1:5000

If PowerShell blocks activation, use:

```powershell
venv\Scripts\python.exe seed_data.py
venv\Scripts\python.exe app.py
```

## Demo questions

- Which products are low in stock?
- Show inventory for Chennai Central.
- Which products have high demand?
- Show demand for Laptop Stand.
- Which stores have stockouts?
- Show top products by demand.
- Show inventory below 20.
- What should I reorder?
- Show demand for Wireless Mouse at Madurai.
- Which products have high stockout risk?

## Project modules

- `app.py` - Flask routes and dashboard logic
- `database.py` - SQLite connection and schema
- `forecasting.py` - demand forecasting and risk calculations
- `nl_sql.py` - natural-language query parser and safe SQL generation
- `seed_data.py` - creates realistic demo data
