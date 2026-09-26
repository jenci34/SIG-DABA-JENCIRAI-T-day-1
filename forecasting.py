from datetime import date, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression

def forecast_series(rows, horizon=4):
    """
    Forecast weekly demand using recent history with a small trend component.
    Returns a list of future weekly predictions.
    """
    if not rows:
        return []

    values = np.array([r["units_sold"] for r in rows], dtype=float)
    n = len(values)

    # Keep the most recent 12 weeks to prevent old history dominating.
    values = values[-12:]
    n = len(values)

    if n < 2:
        predicted = max(0, round(float(values[-1])))
    else:
        x = np.arange(n).reshape(-1, 1)
        model = LinearRegression().fit(x, values)
        future_x = np.arange(n, n + horizon).reshape(-1, 1)
        predicted_values = model.predict(future_x)
        predicted = max(0, round(float(np.mean(predicted_values))))

    last_week = date.fromisoformat(rows[-1]["week_start"])
    forecast = []
    for i in range(1, horizon + 1):
        if n >= 2:
            x = np.arange(n).reshape(-1, 1)
            model = LinearRegression().fit(x, values)
            future_value = max(0, round(float(model.predict([[n + i - 1]])[0])))
        else:
            future_value = predicted
        forecast.append({
            "week": (last_week + timedelta(days=7 * i)).isoformat(),
            "demand": future_value
        })
    return forecast

def stockout_risk(stock_qty, forecast_weekly, lead_time_days):
    """
    Estimates risk from demand expected during supplier lead time.
    """
    weekly = max(1, forecast_weekly)
    lead_weeks = max(1, lead_time_days / 7)
    lead_time_demand = weekly * lead_weeks

    ratio = stock_qty / lead_time_demand
    if stock_qty <= 0:
        return 100, "Critical"
    if ratio < 0.50:
        return 90, "High"
    if ratio < 0.85:
        return 65, "Medium"
    if ratio < 1.20:
        return 35, "Watch"
    return 10, "Safe"

def reorder_quantity(stock_qty, forecast_weekly, lead_time_days, safety_weeks=1):
    weekly = max(1, forecast_weekly)
    coverage_weeks = max(1, lead_time_days / 7) + safety_weeks
    target = round(weekly * coverage_weeks)
    return max(0, target - stock_qty)
