import pandas as pd
import pickle
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import load_data, get_monthly_consumption

from sklearn.linear_model import Ridge, LinearRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_predict, LeaveOneOut
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score, mean_absolute_error

MODELS_DIR = os.getenv("MODELS_DIR", "models")
os.makedirs(MODELS_DIR, exist_ok=True)


# ── MODEL 1 — LEAD TIME PREDICTION (Linear Regression) ──────
def train_lead_time_model(data):
    print("Training Model 1: Lead Time Prediction (Linear Regression)...")

    po  = data["purchase_orders"].copy()
    sup = data["suppliers"].copy()

    # Only use delivered POs with known actual delivery date
    po = po[po["po_status"] == "Delivered"].copy()
    po = po[po["actual_delivery_date"].notna()].copy()

    if len(po) < 5:
        print("  Not enough delivered POs. Skipping.")
        return None, None, None

    # Target: actual lead time in days (order placed -> goods received)
    po["actual_lead_days"] = (
        po["actual_delivery_date"] - po["po_date"]
    ).dt.days

    # Date and value features
    po["month_of_year"] = po["po_date"].dt.month
    po["order_value"]   = po["quantity_ordered"] * po["unit_price"]
    po["promised_days"] = (po["expected_delivery_date"] - po["po_date"]).dt.days

    # Merge supplier rating from suppliers table
    po = po.merge(
        sup[["supplier_id", "supplier_rating"]],
        on="supplier_id",
        how="left"
    )

    # Encode supplier ID as integer
    le = LabelEncoder()
    po["supplier_encoded"] = le.fit_transform(po["supplier_id"])

    # Feature columns
    feat = [
        "supplier_encoded",
        "quantity_ordered",
        "month_of_year",
        "supplier_rating",
        "order_value",
        "promised_days"
    ]

    # Drop rows with missing values in features or target
    df = po.dropna(subset=feat + ["actual_lead_days"])

    if len(df) < 10:
        print("  Not enough clean rows. Skipping.")
        return None, None, None

    X = df[feat].values
    y = df["actual_lead_days"].values

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    sc    = StandardScaler()
    Xs_tr = sc.fit_transform(X_tr)
    Xs_te = sc.transform(X_te)

    model = LinearRegression()
    model.fit(Xs_tr, y_tr)

    y_pred = model.predict(Xs_te)

    print(f"  R2:  {r2_score(y_te, y_pred):.3f}")
    print(f"  MAE: {mean_absolute_error(y_te, y_pred):.2f} days")
    print("  Saved: lead_time_model.pkl")

    return model, sc, le


# ── MODEL 2 — DEMAND FORECAST (Ridge, one model per material) ──
def train_demand_forecast(data):
    print("Training Model 2: Demand Forecast (Ridge per material)...")

    # current month excluded inside get_monthly_consumption
    monthly = get_monthly_consumption(data)

    if len(monthly) == 0:
        print("  No monthly data available.")
        return {}, {}, {}, {}

    # Rename month column if needed
    if "month_of_year" in monthly.columns and "month" not in monthly.columns:
        monthly = monthly.rename(columns={"month_of_year": "month"})

    # Only keep rows where all 3 lag features are available
    monthly = monthly.dropna(subset=["lag_1", "lag_2", "lag_3"])

    feat_cols = ["month_index", "month", "lag_1", "lag_2", "lag_3", "rolling_3m_avg"]

    models        = {}
    scalers       = {}
    metrics       = {}
    last_features = {}

    for mid in monthly["material_id"].unique():

        mdf   = monthly[monthly["material_id"] == mid].copy()
        avail = [c for c in feat_cols if c in mdf.columns]

        if len(mdf) < 6:
            print(f"  {mid}: skipped — only {len(mdf)} months of data")
            continue

        X = mdf[avail].values
        y = mdf["total_consumed"].values

        # One bad material should not stop the other 14 from training
        try:
            # Leave-one-out CV: honest R2 when there are only ~12 rows
            pipe   = make_pipeline(StandardScaler(), Ridge(alpha=0.1))
            y_pred = cross_val_predict(pipe, X, y, cv=LeaveOneOut())
            r2     = r2_score(y, y_pred)
            mae    = mean_absolute_error(y, y_pred)

            # Final model trained on all months
            sc    = StandardScaler()
            model = Ridge(alpha=0.1)
            model.fit(sc.fit_transform(X), y)
        except Exception as e:
            print(f"  {mid}: training failed — {e}")
            continue

        print(f"  {mid:<8}  R2={r2:.3f}  MAE={mae:.1f} units")

        models[mid]  = model
        scalers[mid] = sc
        metrics[mid] = {"r2": round(r2, 3), "mae": round(mae, 1)}

        # Last completed month values — app.py predicts straight from these
        last = mdf.iloc[-1]

        l1_val = float(last["total_consumed"])
        l2_val = float(last.get("lag_1", l1_val))
        l3_val = float(last.get("lag_2", l1_val))
        r3_val = float(last.get("rolling_3m_avg", l1_val))
        idx_val = int(last["month_index"])
        mo_val  = int(last.get("month", 6))

        last_features[mid] = {
            "l1":       l1_val,
            "l2":       l2_val,
            "l3":       l3_val,
            "r3":       r3_val,
            "last_idx": idx_val,
            "last_mo":  mo_val,
            "avail":    avail,
        }

        print(f"    last_features saved: {mid}  l1={l1_val:.1f}  l2={l2_val:.1f}  l3={l3_val:.1f}  month={mo_val}  features={avail}")

    print(f"  Trained {len(models)} material models.")
    print(f"  Saved last_features for {len(last_features)} materials.")
    print("  Saved: demand_forecast_models.pkl")

    return models, scalers, metrics, last_features


# ── MAIN ────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("InventIP — ML Model Training")
    print("=" * 55)
    print()

    data = load_data()
    print(f"Sales rows:          {len(data['sales']):,}")
    print(f"Purchase order rows: {len(data['purchase_orders']):,}")
    print(f"Materials:           {len(data['materials'])}")
    print()

    # ── Model 1: Lead Time ────────────────────────────────────
    # If Model 1 fails, Model 2 should still train
    try:
        lt_model, lt_scaler, lt_le = train_lead_time_model(data)
    except Exception as e:
        print(f"  [ERROR] Lead time training failed: {e}")
        lt_model, lt_scaler, lt_le = None, None, None

    if lt_model is not None:
        lt_bundle = {
            "model":  lt_model,
            "scaler": lt_scaler,
            "le":     lt_le,
        }
        pkl_path = os.path.join(MODELS_DIR, "lead_time_model.pkl")
        try:
            with open(pkl_path, "wb") as f:
                pickle.dump(lt_bundle, f)
        except OSError as e:
            print(f"  [ERROR] Could not save {pkl_path}: {e}")
    print()

    # ── Model 2: Demand Forecast ─────────────────────────────
    try:
        fc_models, fc_scalers, fc_metrics, fc_last_feats = train_demand_forecast(data)
    except Exception as e:
        print(f"  [ERROR] Demand forecast training failed: {e}")
        fc_models, fc_scalers, fc_metrics, fc_last_feats = {}, {}, {}, {}

    if fc_models:
        fc_bundle = {
            "models":        fc_models,
            "scalers":       fc_scalers,
            "metrics":       fc_metrics,
            "last_features": fc_last_feats,
        }
        pkl_path = os.path.join(MODELS_DIR, "demand_forecast_models.pkl")
        try:
            with open(pkl_path, "wb") as f:
                pickle.dump(fc_bundle, f)
        except OSError as e:
            print(f"  [ERROR] Could not save {pkl_path}: {e}")
    print()

    # ── Summary ───────────────────────────────────────────────
    print("=" * 55)
    print("Training complete. Files saved:")
    for fname in ["lead_time_model.pkl", "demand_forecast_models.pkl"]:
        path = os.path.join(MODELS_DIR, fname)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  {fname:<35} {size:,} bytes")


if __name__ == "__main__":
    main()
