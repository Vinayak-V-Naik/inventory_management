import pandas as pd
import math
import os
import pickle
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load .env from same folder as this script
load_dotenv()

# ── Directory Paths ────────────────────────────────────────────
BASE_DIR   = os.getenv("BASE_DIR",   ".")
DATA_DIR   = os.getenv("DATA_DIR",   "dataset")
MODELS_DIR = os.getenv("MODELS_DIR", "models")

# 07_inventory.csv lives inside DATA_DIR — no separate path needed
INVENTORY_PATH = os.path.join(DATA_DIR, "07_inventory.csv")

os.makedirs(MODELS_DIR, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────
Z_SCORE       = 1.65   # 95% service level
SIGMA_FACTOR  = 0.25   # demand variability factor
CUTOFF_MONTHS = 12     # months of recent history to use



# ── DATA LOADER ───────────────────────────────────────────────
def load_data():
    # Reads the 7 dataset CSVs and prepares date/BOM columns
    try:
        materials       = pd.read_csv(os.path.join(DATA_DIR, "01_materials_master.csv"))
        bom             = pd.read_csv(os.path.join(DATA_DIR, "02_bill_of_materials.csv"))
        suppliers       = pd.read_csv(os.path.join(DATA_DIR, "03_suppliers.csv"))
        supplier_map    = pd.read_csv(os.path.join(DATA_DIR, "04_supplier_material_mapping.csv"))
        purchase_orders = pd.read_csv(os.path.join(DATA_DIR, "05_purchase_orders.csv"))
        sales           = pd.read_csv(os.path.join(DATA_DIR, "06_daily_sales.csv"))
        inventory       = pd.read_csv(INVENTORY_PATH)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Dataset file not found: {e.filename}"
        ) from e

    # Convert date columns to datetime
    purchase_orders["po_date"]                = pd.to_datetime(purchase_orders["po_date"])
    purchase_orders["expected_delivery_date"] = pd.to_datetime(purchase_orders["expected_delivery_date"])
    purchase_orders["actual_delivery_date"]   = pd.to_datetime(purchase_orders["actual_delivery_date"], errors="coerce")
    sales["date"] = pd.to_datetime(sales["date"])

    # Effective quantity includes scrap factor
    bom["effective_qty"] = bom["qty_per_unit"] * (1 + bom["scrap_factor"])

    # Add lead_time_days to materials from preferred supplier if missing
    if "lead_time_days" not in materials.columns:
        preferred = supplier_map[supplier_map["preferred"] == True][["material_id", "lead_time_days"]]
        preferred = preferred.drop_duplicates("material_id")
        materials = materials.merge(preferred, on="material_id", how="left")
        materials["lead_time_days"] = materials["lead_time_days"].fillna(7).astype(int)

    return {
        "materials":       materials,
        "bom":             bom,
        "suppliers":       suppliers,
        "supplier_map":    supplier_map,
        "purchase_orders": purchase_orders,
        "sales":           sales,
        "inventory":       inventory,
    }


def write_csv(df, path):
    # Save a CSV — clear error if the file is open in Excel
    try:
        df.to_csv(path, index=False)
    except PermissionError:
        raise PermissionError(
            f"Cannot write {os.path.basename(path)} — close it in Excel and try again."
        )



# ── DAILY MATERIAL CONSUMPTION ────────────────────────────────
def get_daily_consumption(sales_df, bom_df):
    # Explodes daily product sales into per-material consumption via BOM
    rows = []
    for _, sale in sales_df.iterrows():
        if sale["units_sold"] == 0:
            continue
        product_bom = bom_df[bom_df["product_id"] == sale["product_id"]]
        for _, bom_row in product_bom.iterrows():
            rows.append({
                "date":        sale["date"],
                "material_id": bom_row["material_id"],
                "quantity":    sale["units_sold"] * bom_row["effective_qty"],
            })

    if len(rows) == 0:
        return pd.DataFrame(columns=["date", "material_id", "quantity"])

    daily = pd.DataFrame(rows)
    daily = daily.groupby(["date", "material_id"])["quantity"].sum().reset_index()
    return daily


# ── RUNNING STOCK (for charts only) ───────────────────────────
def get_running_stock(data):
    # Simulates stock day by day — for charts only; current stock comes from 07_inventory.csv
    materials = data["materials"]
    sales     = data["sales"]
    bom       = data["bom"]
    pos       = data["purchase_orders"]

    # Start with 2-month buffer as opening stock
    stock = {}
    for _, m in materials.iterrows():
        stock[m["material_id"]] = round((m["annual_demand"] / 12) * 2)

    daily_consumption = get_daily_consumption(sales, bom)
    all_dates         = sorted(sales["date"].unique())
    balance_records   = []

    for d in all_dates:
        # Subtract consumption for this day
        day_consumed = daily_consumption[daily_consumption["date"] == d]
        for _, row in day_consumed.iterrows():
            mid = row["material_id"]
            stock[mid] = max(0, stock[mid] - row["quantity"])

        # Add deliveries for this day
        day_delivered = pos[
            (pos["actual_delivery_date"] == d) &
            (pos["po_status"] == "Delivered")
        ]
        for _, po in day_delivered.iterrows():
            mid = po["material_id"]
            stock[mid] = stock.get(mid, 0) + po["quantity_ordered"]

        # Record balance for each material
        for mid, qty in stock.items():
            balance_records.append({
                "date":        d,
                "material_id": mid,
                "stock":       round(qty),
            })

    return pd.DataFrame(balance_records)


# ── FORMULA FUNCTIONS ─────────────────────────────────────────
def calculate_eoq(annual_demand, ordering_cost, unit_cost, holding_cost_pct):
    # Economic Order Quantity — Wilson formula
    H = unit_cost * holding_cost_pct
    if H <= 0:
        return 1
    eoq = math.sqrt((2 * annual_demand * ordering_cost) / H)
    return max(1, round(eoq))


def calculate_safety_stock(avg_daily, lead_time_days):
    # Safety Stock = Z × sigma × sqrt(lead_time), sigma = avg_daily × 0.25
    sigma = avg_daily * SIGMA_FACTOR
    ss    = Z_SCORE * sigma * math.sqrt(lead_time_days)
    return round(ss)


def calculate_rop(avg_daily, lead_time_days, safety_stock):
    # Reorder Point = avg_daily × lead_time + safety_stock
    rop = avg_daily * lead_time_days + safety_stock
    return round(rop)


def calculate_days_remaining(current_stock, avg_daily):
    # How many days current stock will last at current consumption rate
    if avg_daily <= 0:
        return 999
    return round(current_stock / avg_daily, 1)


# ── DYNAMIC EOQ (rolling 12-month actual consumption) ─────────
def get_dynamic_eoq(data, material_id):
    # EOQ from actual 12-month consumption; falls back to static EOQ if no data
    today       = pd.Timestamp.today().normalize()
    cutoff      = today - pd.DateOffset(months=12)
    sales_12m   = data["sales"][data["sales"]["date"] >= cutoff]
    daily       = get_daily_consumption(sales_12m, data["bom"])
    mat_daily   = daily[daily["material_id"] == material_id]
    total_12m   = float(mat_daily["quantity"].sum())

    m = data["materials"][data["materials"]["material_id"] == material_id].iloc[0]

    if total_12m <= 0:
        # Not enough data — use static fallback
        return calculate_eoq(
            m["annual_demand"], m["ordering_cost"],
            m["unit_cost"], m["holding_cost_pct"]
        )

    H = m["unit_cost"] * m["holding_cost_pct"]
    if H <= 0:
        return int(m.get("min_order_qty", 1))

    eoq     = math.sqrt(2 * total_12m * m["ordering_cost"] / H)
    min_qty = int(m.get("min_order_qty", 1))
    return max(min_qty, round(eoq))


# ── GET CURRENT STOCK ─────────────────────────────────────────
def get_current_stock(data):
    # Reads current stock from 07_inventory.csv as a dict {material_id: stock}
    inv = data["inventory"]
    stock_dict = {}
    for _, row in inv.iterrows():
        stock_dict[row["material_id"]] = row["current_stock"]
    return stock_dict


# ── MONTHLY CONSUMPTION ───────────────────────────────────────
def get_monthly_consumption(data):
    # Monthly consumption + lag_1/2/3 + rolling 3-month avg (Model 2 features); current month excluded
    sales = data["sales"]
    bom   = data["bom"]
    daily = get_daily_consumption(sales, bom)

    if len(daily) == 0:
        return pd.DataFrame()

    daily["year"]  = daily["date"].dt.year
    daily["month"] = daily["date"].dt.month

    # Exclude current month so lag_1 is always last completed month
    today_ts = pd.Timestamp.today()
    daily = daily[
        ~((daily["year"] == today_ts.year) & (daily["month"] == today_ts.month))
    ].copy()

    if len(daily) == 0:
        return pd.DataFrame()

    monthly = daily.groupby(["year", "month", "material_id"])["quantity"].agg(
        total_consumed="sum",
        std_daily="std",
        num_days="count"
    ).reset_index()

    monthly["std_daily"] = monthly["std_daily"].fillna(0)
    monthly = monthly.sort_values(["material_id", "year", "month"]).reset_index(drop=True)

    monthly["month_index"] = monthly.groupby("material_id").cumcount() + 1

    monthly["lag_1"] = monthly.groupby("material_id")["total_consumed"].shift(1)
    monthly["lag_2"] = monthly.groupby("material_id")["total_consumed"].shift(2)
    monthly["lag_3"] = monthly.groupby("material_id")["total_consumed"].shift(3)

    def rolling_3m(x):
        return x.rolling(3, min_periods=1).mean()

    monthly["rolling_3m_avg"] = monthly.groupby("material_id")["total_consumed"].transform(rolling_3m)

    return monthly.round(2)


# ── ABC CLASSIFICATION ────────────────────────────────────────
def compute_abc(materials_df):
    # ABC classes by annual spend: A = top 70%, B = next 20%, C = rest
    df = materials_df.copy()
    df["annual_value"] = df["annual_demand"] * df["unit_cost"]
    df = df.sort_values("annual_value", ascending=False)
    total = df["annual_value"].sum()

    # Classify by where the material STARTS in cumulative value,
    # so a boundary-crossing material still gets the higher class
    abc_map  = {}
    prev_cum = 0.0
    for _, row in df.iterrows():
        cum = round(prev_cum, 6)   # avoid float error at the 0.70/0.90 boundary
        if cum < 0.70:
            abc_map[row["material_id"]] = "A"
        elif cum < 0.90:
            abc_map[row["material_id"]] = "B"
        else:
            abc_map[row["material_id"]] = "C"
        prev_cum += row["annual_value"] / total
    return abc_map


# ── HELPER: Get preferred supplier row for a material ─────────
def get_preferred_supplier(supplier_map, material_id):
    # Returns preferred supplier row; falls back to any supplier if no preferred set
    preferred = supplier_map[
        (supplier_map["material_id"] == material_id) &
        (supplier_map["preferred"] == True)
    ]
    if len(preferred) == 0:
        preferred = supplier_map[supplier_map["material_id"] == material_id]
    try:
        return preferred.iloc[0]
    except IndexError:
        raise ValueError(f"No supplier mapped for material {material_id} in 04_supplier_material_mapping.csv")


# ── HELPER: Build open PO info for a material ─────────────────
def get_open_po_info(pos, material_id, today):
    # Open PO summary for a material: has_open_po, qty, next delivery, days to delivery
    open_pos = pos[
        (pos["material_id"] == material_id) &
        (pos["po_status"].isin(["Open", "Confirmed", "Planned"]))
    ]

    has_open_po = len(open_pos) > 0

    if not has_open_po:
        return False, 0, None, None

    open_po_qty = int(open_pos["quantity_ordered"].sum())

    # Find the next delivery date
    future_pos = open_pos[open_pos["expected_delivery_date"] >= today]
    if len(future_pos) == 0:
        return has_open_po, open_po_qty, None, None

    next_del_date = future_pos["expected_delivery_date"].min()
    next_delivery = next_del_date.strftime("%Y-%m-%d")
    days_to_delivery = (next_del_date - today).days

    return has_open_po, open_po_qty, next_delivery, days_to_delivery


# ── HELPER: Calculate status from stock vs thresholds ─────────
def get_stock_status(current_stock, safety_stock, rop):
    # Status string from stock level vs safety stock and ROP
    if current_stock <= 0:
        return "STOCKOUT"
    elif current_stock <= safety_stock:
        return "CRITICAL"
    elif current_stock <= rop:
        return "REORDER"
    elif current_stock >= rop * 2.5:
        return "OVERSTOCK"
    else:
        return "NORMAL"


# ══════════════════════════════════════════════════════════════
# STATIC SNAPSHOT — Operational Dashboard + Inventory Insights
# ══════════════════════════════════════════════════════════════
def get_static_snapshot(data):
    # Inventory status from static formulas — avg_daily = annual/365, nominal lead time, no ML
    materials    = data["materials"]
    supplier_map = data["supplier_map"]
    pos          = data["purchase_orders"]
    today        = pd.Timestamp.today().normalize()
    stock_dict   = get_current_stock(data)

    rows = []

    for _, m in materials.iterrows():
        mid = m["material_id"]

        # Get preferred supplier details
        sup_row     = get_preferred_supplier(supplier_map, mid)
        nominal_lt  = int(sup_row["lead_time_days"])
        unit_price  = float(sup_row["unit_price"])
        supplier_id = sup_row["supplier_id"]

        # Static avg daily from annual demand
        avg_daily = m["annual_demand"] / 365

        # Calculate thresholds
        safety_stock = calculate_safety_stock(avg_daily, nominal_lt)
        rop          = calculate_rop(avg_daily, nominal_lt, safety_stock)
        eoq          = calculate_eoq(
            m["annual_demand"], m["ordering_cost"],
            m["unit_cost"], m["holding_cost_pct"]
        )

        # Current stock from inventory.csv
        current_stock  = int(stock_dict.get(mid, 0))
        days_remaining = calculate_days_remaining(current_stock, avg_daily)

        # Open PO info
        has_open_po, open_po_qty, next_delivery, days_to_delivery = get_open_po_info(pos, mid, today)

        # Status
        status = get_stock_status(current_stock, safety_stock, rop)
        reorder_triggered = (current_stock <= rop) and not has_open_po

        # Gap between delivery and stockout
        gap_days = None
        if has_open_po and days_to_delivery is not None:
            gap_days = round(days_to_delivery - days_remaining, 1)

        rows.append({
            "material_id":           mid,
            "material_name":         m["material_name"],
            "category":              m["category"],
            "uom":                   m["uom"],
            "unit_cost":             m["unit_cost"],
            "current_stock":         current_stock,
            "safety_stock":          safety_stock,
            "reorder_point":         rop,
            "eoq":                   eoq,
            "avg_daily_consumption": round(avg_daily, 2),
            "forecast_next_month":   None,
            "days_stock_remaining":  days_remaining,
            "status":                status,
            "reorder_triggered":     reorder_triggered,
            "has_open_po":           has_open_po,
            "open_po_qty":           open_po_qty,
            "next_delivery_date":    next_delivery,
            "days_to_delivery":      days_to_delivery,
            "gap_days":              gap_days,
            "preferred_supplier_id": supplier_id,
            "supplier_lead_time":    nominal_lt,
            "predicted_lead_time":   nominal_lt,
            "unit_price":            unit_price,
            "stockout_risk_score":   None,
            "rop_is_dynamic":        False,
        })

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
# DYNAMIC SNAPSHOT — Planning & Forecast + Procurement Plan
# ══════════════════════════════════════════════════════════════
def forecast_from_saved_features(models, scalers, last_features, material_id, n=3):
    # Instant 3-month forecast from the precomputed last_features in the pkl
    if material_id not in models:
        return []
    if material_id not in last_features:
        return []

    model  = models[material_id]
    scaler = scalers[material_id]
    feats  = last_features[material_id]

    l1       = feats["l1"]
    l2       = feats["l2"]
    l3       = feats["l3"]
    r3       = feats["r3"]
    last_idx = feats["last_idx"]
    last_mo  = feats["last_mo"]
    avail    = feats["avail"]

    fc_vals = []
    for i in range(n):
        mo = ((last_mo + i) % 12) + 1

        row = {
            "month_index":    last_idx + i + 1,
            "month":          mo,
            "lag_1":          l1,
            "lag_2":          l2,
            "lag_3":          l3,
            "rolling_3m_avg": r3,
        }

        X  = scaler.transform(pd.DataFrame([row])[avail].values)
        pr = max(0.0, float(model.predict(X)[0]))
        fc_vals.append(round(pr, 2))

        l3 = l2
        l2 = l1
        l1 = pr
        r3 = (r3 * 2 + pr) / 3

    return fc_vals


def get_dynamic_snapshot(data, fc_models, fc_scalers,
                         fc_last_features=None,
                         lt_model=None, lt_scaler=None, lt_le=None):
    # Inventory status from ML — avg_daily from Model 2 forecast, lead time predicted by Model 1
    materials    = data["materials"]
    supplier_map = data["supplier_map"]
    pos          = data["purchase_orders"]
    today        = pd.Timestamp.today().normalize()
    stock_dict   = get_current_stock(data)

    # 12-month consumption computed once, then EOQ per material from it
    cutoff_12m    = today - pd.DateOffset(months=12)
    sales_12m     = data["sales"][data["sales"]["date"] >= cutoff_12m]
    daily_12m_all = get_daily_consumption(sales_12m, data["bom"])

    # Pre-compute EOQ per material from that one computation
    eoq_map = {}
    for _, mat in materials.iterrows():
        mid_eoq   = mat["material_id"]
        mat_daily = daily_12m_all[daily_12m_all["material_id"] == mid_eoq]
        total_12m = float(mat_daily["quantity"].sum())

        if total_12m <= 0:
            eoq_map[mid_eoq] = calculate_eoq(
                mat["annual_demand"], mat["ordering_cost"],
                mat["unit_cost"], mat["holding_cost_pct"]
            )
        else:
            H = mat["unit_cost"] * mat["holding_cost_pct"]
            if H <= 0:
                eoq_map[mid_eoq] = int(mat.get("min_order_qty", 1))
            else:
                eoq_val = math.sqrt(2 * total_12m * mat["ordering_cost"] / H)
                min_qty = int(mat.get("min_order_qty", 1))
                eoq_map[mid_eoq] = max(min_qty, round(eoq_val))

    rows = []

    for _, m in materials.iterrows():
        mid = m["material_id"]

        sup_row     = get_preferred_supplier(supplier_map, mid)
        nominal_lt  = int(sup_row["lead_time_days"])
        unit_price  = float(sup_row["unit_price"])
        supplier_id = sup_row["supplier_id"]

        # Model 1: predicted lead time — falls back to nominal if it fails.
        predicted_lt = nominal_lt

        if lt_model is not None and lt_scaler is not None and lt_le is not None:
            try:
                if supplier_id in lt_le.classes_:
                    sup_enc = lt_le.transform([supplier_id])[0]
                else:
                    sup_enc = 0

                sup_details = data["suppliers"][
                    data["suppliers"]["supplier_id"] == supplier_id
                ].iloc[0]
                rating = float(sup_details["supplier_rating"])

                qty          = 100  # typical order size
                order_value  = unit_price * qty
                features     = [[sup_enc, qty, today.month, rating, order_value, nominal_lt]]
                pred_days    = float(lt_model.predict(lt_scaler.transform(features))[0])
                predicted_lt = max(1, round(pred_days))

            except Exception as e:
                print(f"[WARN] Lead time prediction failed for {mid}: {e}")
                predicted_lt = nominal_lt

        # Model 2: forecast avg_daily — falls back to annual/365 if it fails
        avg_daily           = m["annual_demand"] / 365
        forecast_next_month = None

        if mid in fc_models and fc_last_features:
            try:
                fc_vals = forecast_from_saved_features(
                    fc_models, fc_scalers, fc_last_features, mid, n=3
                )

                if fc_vals and len(fc_vals) == 3 and sum(fc_vals) > 0:
                    forecast_next_month = fc_vals[0]
                    avg_daily = sum(fc_vals) / 3 / 30

            except Exception as e:
                print(f"[WARN] Forecast failed for {mid}: {e}")

        safety_stock = calculate_safety_stock(avg_daily, predicted_lt)
        rop          = calculate_rop(avg_daily, predicted_lt, safety_stock)
        eoq          = eoq_map.get(mid, calculate_eoq(m["annual_demand"], m["ordering_cost"], m["unit_cost"], m["holding_cost_pct"]))

        current_stock  = int(stock_dict.get(mid, 0))
        days_remaining = calculate_days_remaining(current_stock, avg_daily)

        has_open_po, open_po_qty, next_delivery, days_to_delivery = get_open_po_info(
            pos, mid, today
        )

        status            = get_stock_status(current_stock, safety_stock, rop)
        reorder_triggered = (current_stock <= rop) and not has_open_po

        gap_days = None
        if has_open_po and days_to_delivery is not None:
            gap_days = round(days_to_delivery - days_remaining, 1)

        if forecast_next_month is not None:
            forecast_next_month = round(forecast_next_month, 1)

        rows.append({
            "material_id":           mid,
            "material_name":         m["material_name"],
            "category":              m["category"],
            "uom":                   m["uom"],
            "unit_cost":             m["unit_cost"],
            "current_stock":         current_stock,
            "safety_stock":          safety_stock,
            "reorder_point":         rop,
            "eoq":                   eoq,
            "avg_daily_consumption": round(avg_daily, 4),
            "forecast_next_month":   forecast_next_month,
            "days_stock_remaining":  days_remaining,
            "status":                status,
            "reorder_triggered":     reorder_triggered,
            "has_open_po":           has_open_po,
            "open_po_qty":           open_po_qty,
            "next_delivery_date":    next_delivery,
            "days_to_delivery":      days_to_delivery,
            "gap_days":              gap_days,
            "preferred_supplier_id": supplier_id,
            "supplier_lead_time":    nominal_lt,
            "predicted_lead_time":   predicted_lt,
            "unit_price":            unit_price,
            "stockout_risk_score":   None,
            "rop_is_dynamic":        True,
        })

    return pd.DataFrame(rows)

# ── FUTURE PROJECTIONS ────────────────────────────────────────
def get_future_projections(snapshot_df, monthly_df, fc_models, fc_scalers):
    # Simulates 90 days ahead — finds ROP breach/stockout dates, risk level and order_by_date
    today   = datetime.today()
    results = []

    for _, mat in snapshot_df.iterrows():
        mid = mat["material_id"]

        if mid not in fc_models:
            continue

        model  = fc_models[mid]
        scaler = fc_scalers[mid]

        # Get monthly history for this material — need at least 3 rows for lags
        mat_monthly = monthly_df[monthly_df["material_id"] == mid].dropna(
            subset=["lag_1", "lag_2", "lag_3"]
        ).copy()

        if len(mat_monthly) < 3:
            continue

        # Features available for this model
        all_features  = ["month_index", "month", "lag_1", "lag_2", "lag_3", "rolling_3m_avg"]
        avail_features = [f for f in all_features if f in mat_monthly.columns]

        # Starting values from last month
        last_row = mat_monthly.iloc[-1]
        l1       = float(last_row["total_consumed"])
        l2       = float(last_row.get("lag_1", l1))
        l3       = float(last_row.get("lag_2", l1))
        r3       = float(last_row.get("rolling_3m_avg", l1))
        last_idx = int(last_row["month_index"])
        last_mo  = int(last_row.get("month", 6))

        stock_now    = float(mat["current_stock"])
        rop          = float(mat["reorder_point"])
        lead_time    = int(mat["predicted_lead_time"])
        breach_day   = None
        stockout_day = None

        # Cache forecast by month offset to avoid repeated model calls
        daily_rate_cache = {}

        for day_offset in range(90):
            month_offset = day_offset // 30

            # Forecast this month if not already cached
            if month_offset not in daily_rate_cache:
                mo = ((last_mo + month_offset) % 12) + 1
                row = {
                    "month_index":    last_idx + month_offset + 1,
                    "month":          mo,
                    "lag_1":          l1,
                    "lag_2":          l2,
                    "lag_3":          l3,
                    "rolling_3m_avg": r3,
                }
                features_array      = pd.DataFrame([row])[avail_features].values
                monthly_forecast    = max(0, float(model.predict(scaler.transform(features_array))[0]))
                daily_rate_cache[month_offset] = monthly_forecast / 30

                # Shift lags for next month
                if month_offset > 0:
                    l3 = l2
                    l2 = l1
                    l1 = monthly_forecast
                    r3 = (r3 * 2 + monthly_forecast) / 3

            # Reduce stock by daily rate
            stock_now = max(0, stock_now - daily_rate_cache[month_offset])
            current_date = today + timedelta(days=day_offset + 1)

            # Record first breach and first stockout
            if stock_now <= rop and breach_day is None:
                breach_day = current_date

            if stock_now <= 0 and stockout_day is None:
                stockout_day = current_date

        # Calculate days to each event
        days_to_breach   = (breach_day - today).days if breach_day is not None else None
        days_to_stockout = (stockout_day - today).days if stockout_day is not None else None

        # Assign risk level
        if days_to_stockout is not None and days_to_stockout <= lead_time:
            risk = "CRITICAL"   # will stockout before delivery can arrive
        elif days_to_breach is not None and days_to_breach < 15:
            risk = "HIGH"
        elif days_to_breach is not None and days_to_breach < 30:
            risk = "MEDIUM"
        elif days_to_breach is not None:
            risk = "LOW"
        else:
            risk = "SAFE"

        # Calculate order by date
        if days_to_breach is not None:
            order_by_days = max(0, days_to_breach - lead_time)
            order_by_date = (today + timedelta(days=order_by_days)).strftime("%Y-%m-%d")
        else:
            order_by_days = None
            order_by_date = None

        results.append({
            "material_id":           mid,
            "material_name":         mat["material_name"],
            "category":              mat["category"],
            "current_stock":         int(mat["current_stock"]),
            "reorder_point":         int(rop),
            "safety_stock":          int(mat["safety_stock"]),
            "eoq":                   int(mat["eoq"]),
            "avg_daily":             float(mat["avg_daily_consumption"]),
            "predicted_lead_time":   lead_time,
            "days_to_breach":        days_to_breach,
            "days_to_stockout":      days_to_stockout,
            "breach_date":           breach_day.strftime("%Y-%m-%d") if breach_day else None,
            "stockout_date":         stockout_day.strftime("%Y-%m-%d") if stockout_day else None,
            "order_by_date":         order_by_date,
            "order_by_days":         order_by_days,
            "stockout_risk":         risk,
            "preferred_supplier_id": mat["preferred_supplier_id"],
            "unit_price":            mat["unit_price"],
            "rop_is_dynamic":        bool(mat.get("rop_is_dynamic", False)),
        })

    # Sort by urgency — CRITICAL first, then by days to breach
    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "SAFE": 4}
    results.sort(key=lambda x: (
        risk_order.get(x["stockout_risk"], 5),
        x["days_to_breach"] if x["days_to_breach"] is not None else 999
    ))

    return results


# ── ALERT GENERATOR ───────────────────────────────────────────
def get_alerts(snapshot_df, data):
    # Alerts for materials below ROP (no open PO); supplier score = 40% rating + 30% price + 30% lead time
    supplier_map = data["supplier_map"]
    suppliers    = data["suppliers"]
    alerts       = []

    # Only materials that triggered reorder
    triggered = snapshot_df[snapshot_df["reorder_triggered"] == True].copy()
    triggered = triggered.sort_values("days_stock_remaining")

    for _, row in triggered.iterrows():
        mid = row["material_id"]

        # Get all eligible suppliers (rating >= 0.60)
        eligible = supplier_map[supplier_map["material_id"] == mid].copy()
        eligible = eligible.merge(
            suppliers[["supplier_id", "supplier_rating"]],
            on="supplier_id", how="left"
        )
        eligible = eligible[eligible["supplier_rating"] >= 0.60]

        # If no eligible suppliers pass the filter, use all suppliers
        if len(eligible) == 0:
            eligible = supplier_map[supplier_map["material_id"] == mid].copy()
            eligible = eligible.merge(
                suppliers[["supplier_id", "supplier_rating"]],
                on="supplier_id", how="left"
            )

        # Still none — skip this material instead of crashing all alerts
        if len(eligible) == 0:
            print(f"[WARN] get_alerts: no suppliers mapped for {mid} — skipped")
            continue

        # Score each supplier
        max_price = eligible["unit_price"].max()
        max_lt    = eligible["lead_time_days"].max()

        if max_price > 0:
            eligible["price_score"] = 1 - (eligible["unit_price"] / max_price)
        else:
            eligible["price_score"] = 0

        if max_lt > 0:
            eligible["lt_score"] = 1 - (eligible["lead_time_days"] / max_lt)
        else:
            eligible["lt_score"] = 0

        eligible["total_score"] = (
            0.4 * eligible["supplier_rating"] +
            0.3 * eligible["price_score"] +
            0.3 * eligible["lt_score"]
        )

        # Pick the best supplier
        best     = eligible.sort_values("total_score", ascending=False).iloc[0]
        best_sup = suppliers[suppliers["supplier_id"] == best["supplier_id"]].iloc[0]

        today   = datetime.today()
        exp_del = today + timedelta(days=int(best["lead_time_days"]))
        gap     = round(best["lead_time_days"] - row["days_stock_remaining"], 1)

        alerts.append({
            "material_id":               mid,
            "material_name":             row["material_name"],
            "category":                  row["category"],
            "current_stock":             row["current_stock"],
            "safety_stock":              row["safety_stock"],
            "reorder_point":             row["reorder_point"],
            "eoq":                       row["eoq"],
            "days_remaining":            row["days_stock_remaining"],
            "status":                    row["status"],
            "recommended_supplier_id":   best["supplier_id"],
            "recommended_supplier_name": best_sup["supplier_name"],
            "recommended_unit_price":    round(best["unit_price"], 2),
            "recommended_lead_time":     int(best["lead_time_days"]),
            "supplier_score":            round(best["total_score"], 3),
            "order_quantity":            row["eoq"],
            "total_order_cost":          round(row["eoq"] * best["unit_price"], 2),
            "expected_delivery_date":    exp_del.strftime("%Y-%m-%d"),
            "delivery_gap_days":         gap,
            "all_suppliers":             eligible[[
                "supplier_id", "unit_price", "lead_time_days",
                "supplier_rating", "total_score"
            ]].to_dict("records"),
        })

    return alerts


# ── APPROVE PO ────────────────────────────────────────────────
def approve_po(alert, next_po_id=None):
    # Creates an Open PO in purchase_orders.csv from an alert
    po_path = os.path.join(DATA_DIR, "05_purchase_orders.csv")
    pos     = pd.read_csv(po_path)

    if next_po_id is None:
        existing_nums = pos["po_id"].str.replace("PO", "").astype(int)
        next_po_id    = f"PO{(existing_nums.max() + 1):05d}"

    today   = datetime.today()
    exp_del = today + timedelta(days=alert["recommended_lead_time"])

    new_po = pd.DataFrame([{
        "po_id":                  next_po_id,
        "po_date":                today.strftime("%Y-%m-%d"),
        "material_id":            alert["material_id"],
        "supplier_id":            alert["recommended_supplier_id"],
        "quantity_ordered":       alert["order_quantity"],
        "unit_price":             alert["recommended_unit_price"],
        "expected_delivery_date": exp_del.strftime("%Y-%m-%d"),
        "actual_delivery_date":   None,
        "po_status":              "Open",
    }])

    updated = pd.concat([pos, new_po], ignore_index=True)
    write_csv(updated, po_path)

    return next_po_id, exp_del.strftime("%Y-%m-%d")


# ── CONFIRM PO ────────────────────────────────────────────────
def confirm_po(po_id):
    # Changes PO status from Open to Confirmed
    po_path = os.path.join(DATA_DIR, "05_purchase_orders.csv")
    pos = pd.read_csv(po_path)
    pos.loc[pos["po_id"] == po_id, "po_status"] = "Confirmed"
    write_csv(pos, po_path)


# ── MARK AS RECEIVED ──────────────────────────────────────────
def mark_received(po_id, material_id, qty_received, receipt_date_str):
    # Marks PO as Delivered and adds received qty to stock in inventory.csv
    po_path = os.path.join(DATA_DIR, "05_purchase_orders.csv")
    pos = pd.read_csv(po_path)
    pos.loc[pos["po_id"] == po_id, "po_status"]            = "Delivered"
    pos.loc[pos["po_id"] == po_id, "actual_delivery_date"] = receipt_date_str
    write_csv(pos, po_path)

    inv = pd.read_csv(INVENTORY_PATH)
    try:
        current_qty = int(inv.loc[inv["material_id"] == material_id, "current_stock"].values[0])
    except IndexError:
        raise ValueError(f"Material {material_id} not found in 07_inventory.csv")
    inv.loc[inv["material_id"] == material_id, "current_stock"] = current_qty + int(qty_received)
    inv.loc[inv["material_id"] == material_id, "last_updated"]  = receipt_date_str
    write_csv(inv, INVENTORY_PATH)


# ── SAVE DAILY SALES ──────────────────────────────────────────
def save_daily_sales(date_str, product_sales):
    # Appends new sales to daily_sales.csv and reduces inventory via BOM
    sales_path    = os.path.join(DATA_DIR, "06_daily_sales.csv")
    sales         = pd.read_csv(sales_path)

    product_names = {
        "PRD001": "Family Sedan Kit",
        "PRD002": "SUV Drive Kit",
        "PRD003": "Hatchback Brake Kit",
    }

    new_rows = []
    for pid, units in product_sales.items():
        new_rows.append({
            "date":         date_str,
            "product_id":   pid,
            "product_name": product_names.get(pid, pid),
            "units_sold":   int(units),
        })

    updated = pd.concat([sales, pd.DataFrame(new_rows)], ignore_index=True)
    updated["date"] = pd.to_datetime(updated["date"])
    updated = updated.sort_values("date").reset_index(drop=True)
    updated["date"] = updated["date"].dt.strftime("%Y-%m-%d")
    write_csv(updated, sales_path)

    # Reduce inventory based on BOM
    bom = pd.read_csv(os.path.join(DATA_DIR, "02_bill_of_materials.csv"))
    bom["effective_qty"] = bom["qty_per_unit"] * (1 + bom["scrap_factor"])
    inv = pd.read_csv(INVENTORY_PATH)

    # Calculate total consumption per material
    consumption = {}
    for pid, units in product_sales.items():
        if units == 0:
            continue
        product_bom = bom[bom["product_id"] == pid]
        for _, b in product_bom.iterrows():
            mid = b["material_id"]
            if mid not in consumption:
                consumption[mid] = 0
            consumption[mid] = consumption[mid] + round(units * b["effective_qty"])

    # Update inventory
    for mid, qty in consumption.items():
        if mid not in inv["material_id"].values:
            continue
        current_qty = int(inv.loc[inv["material_id"] == mid, "current_stock"].values[0])
        inv.loc[inv["material_id"] == mid, "current_stock"] = max(0, current_qty - qty)
        inv.loc[inv["material_id"] == mid, "last_updated"]  = date_str

    write_csv(inv, INVENTORY_PATH)


# ── OPEN PO TRACKER ───────────────────────────────────────────
def get_open_pos(data):
    # All open/confirmed/planned POs with supplier name and days to delivery
    pos   = data["purchase_orders"]
    sup   = data["suppliers"]
    today = pd.Timestamp.today().normalize()

    open_po = pos[pos["po_status"].isin(["Open", "Confirmed", "Planned"])].copy()

    if len(open_po) == 0:
        return pd.DataFrame()

    open_po = open_po.merge(
        sup[["supplier_id", "supplier_name"]],
        on="supplier_id", how="left"
    )
    open_po["days_to_delivery"] = (open_po["expected_delivery_date"] - today).dt.days
    open_po["is_overdue"]       = open_po["days_to_delivery"] < 0
    open_po["total_value"]      = (open_po["quantity_ordered"] * open_po["unit_price"]).round(2)

    return open_po.sort_values("days_to_delivery")


# ── SUPPLIER SCORECARD ────────────────────────────────────────
def get_supplier_scorecard(data):
    # Delivery performance per supplier — total orders, avg variance days, on-time %
    pos = data["purchase_orders"]
    sup = data["suppliers"]

    delivered = pos[pos["po_status"] == "Delivered"].copy()
    if len(delivered) == 0:
        return pd.DataFrame()

    delivered["delivery_variance"] = (
        delivered["actual_delivery_date"] - delivered["expected_delivery_date"]
    ).dt.days

    delivered["on_time"] = delivered["delivery_variance"] <= 0

    scorecard = delivered.groupby("supplier_id").agg(
        total_orders=("po_id",          "count"),
        avg_variance=("delivery_variance", "mean"),
        on_time_pct= ("on_time",          "mean"),
    ).reset_index()

    scorecard = scorecard.merge(
        sup[["supplier_id", "supplier_name", "country", "supplier_rating"]],
        on="supplier_id"
    )
    scorecard["avg_variance"] = scorecard["avg_variance"].round(1)
    scorecard["on_time_pct"]  = (scorecard["on_time_pct"] * 100).round(1)

    return scorecard.sort_values("on_time_pct", ascending=False)


# ── RAISE PLANNED PO ──────────────────────────────────────────
def raise_planned_po(proj, suppliers_df, supplier_map_df):
    # Creates a Planned PO from a future breach — supplier picked by urgency (speed vs cost)
    mid       = proj["material_id"]
    today     = datetime.today()
    days_left = proj["days_to_breach"] or 90

    # Get eligible suppliers
    eligible = supplier_map_df[supplier_map_df["material_id"] == mid].copy()
    eligible = eligible.merge(
        suppliers_df[["supplier_id", "supplier_rating"]],
        on="supplier_id", how="left"
    )
    eligible = eligible[eligible["supplier_rating"] >= 0.60]

    if len(eligible) == 0:
        eligible = supplier_map_df[supplier_map_df["material_id"] == mid].copy()
        eligible = eligible.merge(
            suppliers_df[["supplier_id", "supplier_rating"]],
            on="supplier_id", how="left"
        )

    if len(eligible) == 0:
        raise ValueError(f"No supplier mapped for material {mid} — cannot raise PO")

    max_price = eligible["unit_price"].max()
    max_lt    = eligible["lead_time_days"].max()

    price_norm = 1 - (eligible["unit_price"] / max_price) if max_price > 0 else 0
    lt_norm    = 1 - (eligible["lead_time_days"] / max_lt) if max_lt > 0 else 0

    if days_left < 15:
        eligible["score"] = 0.4 * eligible["supplier_rating"] + 0.1 * price_norm + 0.5 * lt_norm
        reason = "Fastest supplier — breach window critical"
    elif days_left < 30:
        eligible["score"] = 0.4 * eligible["supplier_rating"] + 0.2 * price_norm + 0.4 * lt_norm
        reason = "Balanced speed and cost — breach within 30 days"
    else:
        eligible["score"] = 0.4 * eligible["supplier_rating"] + 0.4 * price_norm + 0.2 * lt_norm
        reason = "Most cost-effective supplier"

    best       = eligible.sort_values("score", ascending=False).iloc[0]
    sup_name   = suppliers_df[suppliers_df["supplier_id"] == best["supplier_id"]]["supplier_name"].values[0]
    unit_price = float(best["unit_price"])
    lead_time  = int(best["lead_time_days"])
    eoq        = proj["eoq"]
    exp_del    = today + timedelta(days=lead_time)

    po_path      = os.path.join(DATA_DIR, "05_purchase_orders.csv")
    pos          = pd.read_csv(po_path)
    existing_nums = pos["po_id"].str.replace("PO", "").astype(int)
    next_id       = f"PO{(existing_nums.max() + 1):05d}"

    new_po = pd.DataFrame([{
        "po_id":                  next_id,
        "po_date":                today.strftime("%Y-%m-%d"),
        "material_id":            mid,
        "supplier_id":            best["supplier_id"],
        "quantity_ordered":       eoq,
        "unit_price":             unit_price,
        "expected_delivery_date": exp_del.strftime("%Y-%m-%d"),
        "actual_delivery_date":   None,
        "po_status":              "Planned",
    }])

    write_csv(pd.concat([pos, new_po], ignore_index=True), po_path)

    return {
        "po_id":             next_id,
        "supplier_name":     sup_name,
        "unit_price":        unit_price,
        "quantity":          eoq,
        "total_cost":        round(eoq * unit_price, 2),
        "expected_delivery": exp_del.strftime("%Y-%m-%d"),
        "selection_reason":  reason,
        "lead_time":         lead_time,
    }


# ── TERMINAL TEST ─────────────────────────────────────────────
if __name__ == "__main__":
    print("Loading data...")
    data = load_data()
    print(f"  Materials:       {len(data['materials'])}")
    print(f"  Sales rows:      {len(data['sales']):,}")
    print(f"  Purchase Orders: {len(data['purchase_orders'])}")
    print(f"  Inventory rows:  {len(data['inventory'])}")
    print()

    # Try to load ML models
    bundle = {}
    for model_name, file_name in [("lead_time", "lead_time_model.pkl"),
                                   ("demand_forecast", "demand_forecast_models.pkl")]:
        file_path = os.path.join(MODELS_DIR, file_name)
        if os.path.exists(file_path):
            try:
                with open(file_path, "rb") as f:
                    bundle[model_name] = pickle.load(f)
            except Exception as e:
                print(f"[WARN] Could not load {file_name}: {e}")

    ml_loaded = len(bundle) > 0
    print(f"ML Models: {'LOADED' if ml_loaded else 'NOT FOUND — run model.py first'}")

    if ml_loaded:
        fm   = bundle["demand_forecast"]["models"]
        fs   = bundle["demand_forecast"]["scalers"]
        flf  = bundle["demand_forecast"].get("last_features", {})
        lt_m = bundle["lead_time"].get("model")  if "lead_time" in bundle else None
        lt_s = bundle["lead_time"].get("scaler") if "lead_time" in bundle else None
        lt_l = bundle["lead_time"].get("le")     if "lead_time" in bundle else None
        snapshot = get_dynamic_snapshot(data, fm, fs, flf, lt_m, lt_s, lt_l)
        print("Using: get_dynamic_snapshot (ML-driven values)\n")
    else:
        snapshot = get_static_snapshot(data)
        print("Using: get_static_snapshot (annual_demand/365 fallback)\n")

    header = f"{'Material':<25} {'Stock':>6} {'ROP':>6} {'SS':>6} {'AvgDay':>7} {'PredLT':>7} {'EOQ':>6} {'Days':>6}  Status"
    print(header)
    print("-" * len(header))

    for _, row in snapshot.iterrows():
        rop_str  = str(row["reorder_point"]) if row["reorder_point"] is not None else "N/A"
        ss_str   = str(row["safety_stock"])  if row["safety_stock"]  is not None else "N/A"
        avg_str  = f"{row['avg_daily_consumption']:.2f}" if row["avg_daily_consumption"] is not None else "N/A"
        days_str = f"{row['days_stock_remaining']:.1f}"  if row["days_stock_remaining"]  is not None else "N/A"
        flag     = " ⚠ ALERT" if row["reorder_triggered"] else ""
        ml_tag   = "[DYN]" if row.get("rop_is_dynamic") else "[STA]"

        print(
            f"{row['material_name']:<25} {row['current_stock']:>6} "
            f"{rop_str:>6} {ss_str:>6} "
            f"{avg_str:>7} {int(row['predicted_lead_time']):>7} "
            f"{str(row['eoq']):>6} {days_str:>6}  "
            f"{row['status']:<12} {ml_tag}{flag}"
        )

    print()
    alerts = get_alerts(snapshot, data)
    print(f"Active reorder alerts: {len(alerts)}")
    for a in alerts:
        print(f"  {a['material_name']:<25} stock={a['current_stock']}  ROP={a['reorder_point']}  days_left={a['days_remaining']}")
