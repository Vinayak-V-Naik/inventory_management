'''LangChain tools that wrap the existing app.py analytics.

Each tool does ZERO new math — it calls the same functions the dashboard
uses and returns a compact text summary the LLM can reason over.
'''

import os
import pickle
import time

import pandas as pd
from langchain_core.tools import tool

from app import (
    load_data,
    get_static_snapshot,
    get_dynamic_snapshot,
    get_monthly_consumption,
    get_future_projections,
    get_supplier_scorecard as _supplier_scorecard,
    get_open_pos,
    get_alerts,
    forecast_from_saved_features,
)

# ── Shared context (data + models + snapshot), cached for 60s ──
_TTL_SECONDS = 60
_cache = {"time": 0.0, "ctx": None}


def _load_model_bundle():
    '''Same pkl loading as the dashboard, minus streamlit caching'''
    mdir   = os.getenv("MODELS_DIR", "models")
    bundle = {}
    for name, fname in [("lead_time", "lead_time_model.pkl"),
                        ("demand_forecast", "demand_forecast_models.pkl")]:
        path = os.path.join(mdir, fname)
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    bundle[name] = pickle.load(f)
            except Exception:
                pass
    return bundle


def get_context(refresh=False):
    '''Loads CSVs + models and builds the (dynamic if possible) snapshot'''
    if not refresh and _cache["ctx"] is not None and time.time() - _cache["time"] < _TTL_SECONDS:
        return _cache["ctx"]

    data = load_data()
    ml   = _load_model_bundle()
    fc   = ml.get("demand_forecast", {})
    lt   = ml.get("lead_time", {})

    if fc.get("models"):
        snapshot = get_dynamic_snapshot(
            data, fc["models"], fc["scalers"], fc.get("last_features", {}),
            lt.get("model"), lt.get("scaler"), lt.get("le"),
        )
    else:
        snapshot = get_static_snapshot(data)

    ctx = {"data": data, "ml": ml, "snapshot": snapshot}
    _cache["time"] = time.time()
    _cache["ctx"]  = ctx
    return ctx


def _resolve_material(snapshot, material):
    '''Finds one snapshot row by material_id or (partial) name.
    Returns (row, error_message) — exactly one of the two is None.'''
    q = str(material).strip().lower()
    if not q:
        return None, "Empty material name. " + _material_list(snapshot)

    by_id = snapshot[snapshot["material_id"].str.lower() == q]
    if len(by_id) == 1:
        return by_id.iloc[0], None

    names = snapshot["material_name"].str.lower()
    exact = snapshot[names == q]
    if len(exact) == 1:
        return exact.iloc[0], None

    partial = snapshot[names.str.contains(q, regex=False)]
    if len(partial) == 1:
        return partial.iloc[0], None
    if len(partial) > 1:
        opts = ", ".join(partial["material_name"].tolist())
        return None, f"Ambiguous material '{material}' — matches: {opts}. Ask again with one of these."

    return None, f"Unknown material '{material}'. " + _material_list(snapshot)


def _material_list(snapshot):
    pairs = [f"{r.material_id}={r.material_name}" for r in snapshot.itertuples()]
    return "Known materials: " + ", ".join(pairs)


def _df_text(df):
    return df.to_string(index=False)


# ── TOOLS ─────────────────────────────────────────────────────
@tool
def inventory_snapshot(status: str = "") -> str:
    '''Current inventory status for all materials: stock, safety stock, reorder
    point, days of stock remaining and status. Optional status filter, one of:
    NORMAL, REORDER, CRITICAL, STOCKOUT, OVERSTOCK.'''
    snap = get_context()["snapshot"]
    cols = ["material_id", "material_name", "current_stock", "safety_stock",
            "reorder_point", "days_stock_remaining", "status", "has_open_po"]
    view = snap[cols].copy()
    if status.strip():
        view = view[view["status"] == status.strip().upper()]
        if len(view) == 0:
            return f"No materials with status {status.strip().upper()}."
    kind = "ML-driven (dynamic)" if snap["rop_is_dynamic"].any() else "static formula"
    return f"Inventory snapshot ({kind} thresholds):\n" + _df_text(view)


@tool
def material_details(material: str) -> str:
    '''Full detail for ONE material (by name or material_id): stock levels,
    EOQ, forecast, lead time, preferred supplier, open PO and status.'''
    ctx = get_context()
    row, err = _resolve_material(ctx["snapshot"], material)
    if err:
        return err

    lines = [f"{row['material_name']} ({row['material_id']}) — {row['category']}, unit: {row['uom']}"]
    lines.append(f"Status: {row['status']} | reorder_triggered: {bool(row['reorder_triggered'])}")
    lines.append(f"Current stock: {row['current_stock']} | Safety stock: {row['safety_stock']} "
                 f"| Reorder point: {row['reorder_point']} | EOQ: {row['eoq']}")
    lines.append(f"Avg daily consumption: {row['avg_daily_consumption']} "
                 f"| Days of stock remaining: {row['days_stock_remaining']}")
    if row["forecast_next_month"] is not None:
        lines.append(f"Forecast next month: {row['forecast_next_month']} units")
    lines.append(f"Preferred supplier: {row['preferred_supplier_id']} @ INR {row['unit_price']}/unit "
                 f"| Nominal lead time: {row['supplier_lead_time']}d "
                 f"| ML-predicted lead time: {row['predicted_lead_time']}d")
    if row["has_open_po"]:
        lines.append(f"Open PO: {row['open_po_qty']} units arriving {row['next_delivery_date']} "
                     f"(in {row['days_to_delivery']} days, gap vs stockout: {row['gap_days']} days)")
    else:
        lines.append("Open PO: none")
    lines.append(f"Stock value: INR {row['current_stock'] * row['unit_cost']:,.0f}")
    return "\n".join(lines)


@tool
def reorder_recommendations() -> str:
    '''Materials that need reordering NOW (below reorder point, no open PO),
    with the best supplier, order quantity (EOQ), cost and expected delivery.'''
    ctx    = get_context()
    alerts = get_alerts(ctx["snapshot"], ctx["data"])
    if not alerts:
        return "No materials currently trigger a reorder (all above reorder point or already have an open PO)."

    out = [f"{len(alerts)} material(s) need reordering:"]
    for a in alerts:
        out.append(
            f"- {a['material_name']} ({a['material_id']}): stock {a['current_stock']}, "
            f"ROP {a['reorder_point']}, {a['days_remaining']} days left, status {a['status']}. "
            f"Recommend ordering {a['order_quantity']} units from {a['recommended_supplier_name']} "
            f"({a['recommended_supplier_id']}) @ INR {a['recommended_unit_price']}/unit "
            f"= INR {a['total_order_cost']:,.0f}, lead time {a['recommended_lead_time']}d, "
            f"expected delivery {a['expected_delivery_date']} "
            f"(delivery gap vs stockout: {a['delivery_gap_days']} days)."
        )
    return "\n".join(out)


@tool
def demand_forecast(material: str) -> str:
    '''3-month demand forecast for ONE material (by name or material_id),
    from the trained Ridge regression model.'''
    ctx = get_context()
    row, err = _resolve_material(ctx["snapshot"], material)
    if err:
        return err

    fc = ctx["ml"].get("demand_forecast", {})
    if not fc.get("models"):
        return "Demand forecast models are not trained — run `python ml_model.py` first."

    vals = forecast_from_saved_features(
        fc["models"], fc["scalers"], fc.get("last_features", {}), row["material_id"], n=3
    )
    if not vals:
        return f"No forecast model available for {row['material_name']} (too little history)."

    metrics = fc.get("metrics", {}).get(row["material_id"])
    quality = f" (model R2={metrics['r2']}, MAE={metrics['mae']})" if metrics else ""
    return (f"Demand forecast for {row['material_name']} ({row['material_id']}), next 3 months: "
            f"{vals[0]:.0f}, {vals[1]:.0f}, {vals[2]:.0f} units{quality}. "
            f"Avg daily approx {sum(vals) / 3 / 30:.1f} units/day.")


@tool
def stockout_risk_projections() -> str:
    '''90-day forward simulation for every material: projected reorder-point
    breach date, stockout date, risk level (CRITICAL/HIGH/MEDIUM/LOW/SAFE)
    and the order-by date. Use for "what is at risk" questions.'''
    ctx = get_context()
    fc  = ctx["ml"].get("demand_forecast", {})
    if not fc.get("models"):
        return "Projections need the forecast models — run `python ml_model.py` first."

    monthly = get_monthly_consumption(ctx["data"])
    projs   = get_future_projections(ctx["snapshot"], monthly, fc["models"], fc["scalers"])
    if not projs:
        return "No projections available (insufficient history)."

    at_risk = [p for p in projs if p["stockout_risk"] != "SAFE"]
    safe_n  = len(projs) - len(at_risk)
    if not at_risk:
        return f"All {len(projs)} projected materials are SAFE for the next 90 days."

    out = [f"{len(at_risk)} material(s) at risk in the next 90 days ({safe_n} safe):"]
    for p in at_risk:
        out.append(
            f"- {p['material_name']} ({p['material_id']}): risk {p['stockout_risk']}, "
            f"stock {p['current_stock']}, ROP breach in {p['days_to_breach']}d ({p['breach_date']}), "
            f"stockout in {p['days_to_stockout']}d ({p['stockout_date']}), "
            f"lead time {p['predicted_lead_time']}d → order by {p['order_by_date'] or 'NOW'}."
        )
    return "\n".join(out)


@tool
def supplier_scorecard() -> str:
    '''Delivery performance of every supplier: total delivered orders, average
    delivery variance in days (negative = early) and on-time percentage.
    Use for supplier comparison / selection questions.'''
    ctx = get_context()
    sc  = _supplier_scorecard(ctx["data"])
    if len(sc) == 0:
        return "No delivered purchase orders yet — no scorecard available."
    cols = ["supplier_id", "supplier_name", "country", "supplier_rating",
            "total_orders", "avg_variance", "on_time_pct"]
    return ("Supplier delivery scorecard (avg_variance in days, negative = early; "
            "on_time_pct in %):\n" + _df_text(sc[cols]))


@tool
def open_purchase_orders() -> str:
    '''All open, confirmed and planned purchase orders with supplier,
    quantity, value and days until expected delivery (negative = overdue).'''
    ctx = get_context()
    po  = get_open_pos(ctx["data"])
    if len(po) == 0:
        return "There are no open purchase orders."
    view = po[["po_id", "material_id", "supplier_name", "quantity_ordered",
               "po_status", "expected_delivery_date", "days_to_delivery",
               "is_overdue", "total_value"]].copy()
    view["expected_delivery_date"] = view["expected_delivery_date"].dt.strftime("%Y-%m-%d")
    return "Open purchase orders (total_value in INR):\n" + _df_text(view)


@tool
def search_policy_docs(query: str) -> str:
    '''Searches company policy and SOP documents — inventory SOP, procurement
    policy, supplier guidelines and business/model rules — and returns the most
    relevant passages. Use for "what is the policy/procedure/rule" questions,
    approval limits, rating thresholds, formula explanations.'''
    from rag.retriever import search
    hits = search(query, k=4)
    if not hits:
        return "No relevant policy passages found."
    return "\n\n".join(f"[{h['title']} — {h['source']}]\n{h['text']}" for h in hits)


TOOLS = [
    inventory_snapshot,
    material_details,
    reorder_recommendations,
    demand_forecast,
    stockout_risk_projections,
    supplier_scorecard,
    open_purchase_orders,
    search_policy_docs,
]

TOOL_MAP = {t.name: t for t in TOOLS}
