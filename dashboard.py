import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import math, os, sys, pickle
import streamlit.components.v1 as components


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import (
    load_data, get_static_snapshot, get_dynamic_snapshot, get_alerts,
    get_running_stock, get_monthly_consumption,
    get_open_pos, get_supplier_scorecard,
    approve_po, confirm_po, mark_received, save_daily_sales,
    get_future_projections, raise_planned_po
)

st.set_page_config(page_title="InventIP",page_icon="🏭",layout="wide",initial_sidebar_state="expanded")

# ── CSS STYLES ────────────────────────────────────────────────
# All custom styling lives here: page titles, KPI cards (st-key-kpi_*),
# health-grid cards (.mat-card), navbar buttons (st-key-nav_*),
# invisible click-overlay for grid cards (st-key-det_*), back-to-top arrow.
# To change a card color: edit the matching .st-key-... rule below.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.block-container{padding-top:3.5rem;padding-bottom:2rem;}
.page-title{font-size:1.75rem;font-weight:700;color:#1B3A6B;margin-top:0.5rem;margin-bottom:0.1rem;padding-top:0.4rem;}
.page-sub{font-size:0.85rem;color:#64748B;margin-bottom:1.4rem;}
.kpi-card{background:#fff;border:1px solid #E2E8F0;border-radius:10px;padding:1rem 1.2rem;box-shadow:0 1px 3px rgba(0,0,0,.06);}
.kpi-value{font-size:1.7rem;font-weight:700;color:#0F172A;}
.kpi-label{font-size:.74rem;color:#64748B;margin-top:2px;}
.section-title{font-size:.95rem;font-weight:600;color:#1B3A6B;margin-bottom:.8rem;}
.alert-card{background:#FFF7F7;border:1.5px solid #FDA4A4;border-radius:10px;padding:1.2rem;margin-bottom:1rem;}
.amber-card{background:#FFFBEB;border:1.5px solid #FCD34D;border-radius:10px;padding:1.2rem;margin-bottom:1rem;}
.plan-card{background:#F0F9FF;border:1.5px solid #7DD3FC;border-radius:10px;padding:1.2rem;margin-bottom:1rem;}
.gap-warn{background:#FEF3C7;color:#92400E;border-radius:6px;padding:3px 10px;font-size:.75rem;font-weight:600;display:inline-block;margin-top:6px;}
.gap-crit{background:#FEE2E2;color:#991B1B;border-radius:6px;padding:3px 10px;font-size:.75rem;font-weight:600;display:inline-block;margin-top:6px;}
.mat-card{background:#fff;border:1.5px solid #E2E8F0;border-radius:12px;padding:1rem 1.05rem;margin-bottom:.7rem;box-shadow:0 1px 3px rgba(0,0,0,.05);}
.mat-kv{display:flex;justify-content:space-between;align-items:center;font-size:.72rem;margin-top:3px;}
.mat-name{font-size:1.05rem;font-weight:700;color:#0F172A;line-height:1.3;}
.mat-cat{font-size:.72rem;color:#94A3B8;margin-bottom:4px;}
.mat-stock{font-size:1.7rem;font-weight:800;letter-spacing:-.02em;}
.mat-meta{font-size:.7rem;color:#64748B;margin-top:3px;}
.badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:.68rem;font-weight:700;margin-top:4px;}
.risk-crit{background:#7F1D1D;color:#fff;border-radius:6px;padding:2px 10px;font-size:.72rem;font-weight:700;}
.risk-high{background:#FEE2E2;color:#991B1B;border-radius:6px;padding:2px 10px;font-size:.72rem;font-weight:700;}
.risk-med{background:#FEF3C7;color:#92400E;border-radius:6px;padding:2px 10px;font-size:.72rem;font-weight:700;}
.risk-low{background:#DBEAFE;color:#1E40AF;border-radius:6px;padding:2px 10px;font-size:.72rem;font-weight:700;}
.risk-safe{background:#F0FDF4;color:#14532D;border-radius:6px;padding:2px 10px;font-size:.72rem;font-weight:700;}
.abc-a{background:#FEF9C3;color:#854D0E;border:1px solid #FDE047;display:inline-block;padding:1px 6px;border-radius:4px;font-size:.65rem;font-weight:700;margin-left:4px;}
.abc-b{background:#DBEAFE;color:#1E40AF;border:1px solid #93C5FD;display:inline-block;padding:1px 6px;border-radius:4px;font-size:.65rem;font-weight:700;margin-left:4px;}
.abc-c{background:#F1F5F9;color:#475569;border:1px solid #CBD5E1;display:inline-block;padding:1px 6px;border-radius:4px;font-size:.65rem;font-weight:700;margin-left:4px;}
.legend-strip{display:flex;gap:.6rem;flex-wrap:wrap;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:.6rem 1rem;margin-bottom:1rem;}
.legend-item{display:flex;align-items:center;gap:5px;font-size:.75rem;color:#374151;}
.legend-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;}
.threshold-note{font-size:.78rem;color:#64748B;margin-top:.3rem;margin-bottom:.6rem;}
.sb-row{display:flex;justify-content:space-between;align-items:center;font-size:.78rem;color:#374151;margin-bottom:3px;}
.sb-val{font-weight:600;color:#0F172A;}
.st-key-nav_home button{font-size:1.75rem;font-weight:700;color:#1B3A6B;padding:0;}
.st-key-nav_home button p{font-size:1.75rem;font-weight:700;}
.st-key-nav_home button:hover{color:#0D7C6E;}
.nav-sub{font-size:.72rem;color:#94A3B8;margin-top:-12px;}
.st-key-nav_insights button,.st-key-nav_planning button,.st-key-nav_procure button,.st-key-nav_copilot button{color:#475569;font-weight:600;white-space:nowrap;}
.st-key-nav_insights button p,.st-key-nav_planning button p,.st-key-nav_procure button p,.st-key-nav_copilot button p{font-size:1.2rem;font-weight:600;}
.st-key-nav_insights button:hover,.st-key-nav_planning button:hover,.st-key-nav_procure button:hover,.st-key-nav_copilot button:hover{color:#1B3A6B;}
.nav-line{border-bottom:1px solid #E2E8F0;margin:.2rem 0 1rem 0;}
div[class*="st-key-kpi_"] button{background:#fff !important;border:2px solid #E2E8F0 !important;border-radius:12px !important;box-shadow:0 1px 3px rgba(0,0,0,.06) !important;width:100% !important;height:5.8rem !important;min-height:5.8rem !important;padding:.5rem .4rem !important;}
div[class*="st-key-kpi_"] button:hover{filter:brightness(.96);}
div[class*="st-key-kpi_"] button p{font-size:.7rem !important;color:#64748B !important;line-height:1.5 !important;text-align:center !important;font-weight:600 !important;}
div[class*="st-key-kpi_"] button p strong{display:block;font-size:1.45rem !important;font-weight:700 !important;line-height:1.3 !important;}
div.st-key-kpi_total button{background:#F8FAFC !important;border-color:#1B3A6B !important;}
div.st-key-kpi_total button p{color:#1B3A6B !important;}
div.st-key-kpi_normal button{background:#DCFCE7 !important;border-color:#22C55E !important;}
div.st-key-kpi_normal button p{color:#14532D !important;}
div.st-key-kpi_reorder button{background:#FEF3C7 !important;border-color:#F59E0B !important;}
div.st-key-kpi_reorder button p{color:#92400E !important;}
div.st-key-kpi_crit button{background:#ED1C24 !important;border-color:#B01018 !important;}
div.st-key-kpi_crit button p{color:#FFE4E4 !important;}
div.st-key-kpi_crit button p strong{color:#FFFFFF !important;}
div.st-key-kpi_over button{background:#DBEAFE !important;border-color:#3B82F6 !important;}
div.st-key-kpi_over button p{color:#1E40AF !important;}
div.st-key-kpi_openpo button{background:#FFEDD5 !important;border-color:#FB923C !important;}
div.st-key-kpi_openpo button p{color:#9A3412 !important;}
div.st-key-kpi_value button{background:linear-gradient(135deg,#1B3A6B 0%,#2563EB 100%) !important;border-color:#1B3A6B !important;}
div.st-key-kpi_value button p{color:#DBEAFE !important;}
div.st-key-kpi_value button p strong{color:#FFFFFF !important;font-size:1.02rem !important;}
div.st-key-kpi_fcrit button{background:#ED1C24 !important;border-color:#B01018 !important;}
div.st-key-kpi_fcrit button p{color:#FFE4E4 !important;}
div.st-key-kpi_fcrit button p strong{color:#FFFFFF !important;}
div.st-key-kpi_fhigh button{background:#FEE2E2 !important;border-color:#EF4444 !important;}
div.st-key-kpi_fhigh button p{color:#991B1B !important;}
div.st-key-kpi_fmed button{background:#FEF3C7 !important;border-color:#F59E0B !important;}
div.st-key-kpi_fmed button p{color:#92400E !important;}
div.st-key-kpi_flow button{background:#DBEAFE !important;border-color:#3B82F6 !important;}
div.st-key-kpi_flow button p{color:#1E40AF !important;}
div.st-key-kpi_fsafe button{background:#DCFCE7 !important;border-color:#22C55E !important;}
div.st-key-kpi_fsafe button p{color:#14532D !important;}
.st-key-howworks_btn button{color:#64748B;font-size:.78rem;}
.st-key-jump_full button{color:#1B3A6B;font-size:.78rem;font-weight:600;}
div[data-testid="stColumn"]:has(div[class*="st-key-det_"]){position:relative;}
div[class*="st-key-det_"]{position:absolute;inset:0;z-index:3;width:100% !important;height:100% !important;}
div[class*="st-key-det_"] > div,div[class*="st-key-det_"] .stButton{width:100% !important;height:100% !important;}
div[class*="st-key-det_"] button{width:100% !important;height:100% !important;opacity:0 !important;cursor:pointer !important;border:none !important;background:#1B3A6B !important;min-height:0 !important;padding:0 !important;margin:0 !important;border-radius:12px !important;}
div[class*="st-key-det_"] button:hover{opacity:.07 !important;}
.back-to-top{position:fixed;bottom:28px;right:28px;width:46px;height:46px;border-radius:50%;background:#1B3A6B;color:#fff !important;display:flex;align-items:center;justify-content:center;font-size:1.25rem;text-decoration:none !important;box-shadow:0 4px 12px rgba(0,0,0,.3);z-index:9999;}
.back-to-top:hover{background:#0D7C6E;}
</style>""", unsafe_allow_html=True)




# ── CONSTANTS ─────────────────────────────────────────────────
# Color maps used everywhere: STATUS_* = current stock status,
# RISK_* = 90-day projected risk, CAT_* = material category.
STATUS_COLORS={"NORMAL":"#22C55E","REORDER":"#F59E0B","CRITICAL":"#EF4444","STOCKOUT":"#ED1C24","OVERSTOCK":"#3B82F6"}
STATUS_BG={"NORMAL":"#F0FDF4","REORDER":"#FFFBEB","CRITICAL":"#FEF2F2","STOCKOUT":"#ED1C24","OVERSTOCK":"#EFF6FF"}
STATUS_BORDER={"NORMAL":"#22C55E","REORDER":"#F59E0B","CRITICAL":"#EF4444","STOCKOUT":"#ED1C24","OVERSTOCK":"#3B82F6"}
RISK_COLORS={"CRITICAL":"#ED1C24","HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#3B82F6","SAFE":"#22C55E"}
RISK_BG={"CRITICAL":"#ED1C24","HIGH":"#FEF2F2","MEDIUM":"#FFFBEB","LOW":"#EFF6FF","SAFE":"#F0FDF4"}
RISK_BORDER={"CRITICAL":"#B01018","HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#3B82F6","SAFE":"#22C55E"}
RISK_HTML={
    "CRITICAL":'<span class="risk-crit">CRITICAL</span>',
    "HIGH":    '<span class="risk-high">HIGH RISK</span>',
    "MEDIUM":  '<span class="risk-med">MEDIUM RISK</span>',
    "LOW":     '<span class="risk-low">LOW RISK</span>',
    "SAFE":    '<span class="risk-safe">SAFE</span>',
}
CAT_COLORS={"Metal":"#1B3A6B","Mechanical":"#0D7C6E","Electrical":"#D97706","Sealing":"#7C3AED"}
CAT_BG={"Metal":"#EFF6FF","Mechanical":"#F0FDF4","Electrical":"#FFFBEB","Sealing":"#F5F3FF"}

# ── HELPERS ───────────────────────────────────────────────────
def badge_html(s):
    # colored status pill, e.g. NORMAL / REORDER / STOCKOUT
    c=STATUS_COLORS.get(s,"#64748B"); bg=c+"22"
    return f'<span class="badge" style="background:{bg};color:{c};border:1px solid {c};">{s}</span>'
def abc_badge(c): return f'<span class="abc-{c.lower()}">{c}</span>'   # small A/B/C tag
def fmt_inr(v): return f"₹{v:,.0f}"                                    # 344999 -> ₹344,999

def compute_abc(mdf):
    # ABC classification by annual spend: A = top 70%, B = next 20%, C = rest
    df=mdf.copy(); df["av"]=df["annual_demand"]*df["unit_cost"]
    df=df.sort_values("av",ascending=False).reset_index(drop=True)
    t=df["av"].sum(); df["cp"]=df["av"].cumsum()/t*100
    df["abc"]=df["cp"].apply(lambda x:"A" if x<=70 else "B" if x<=90 else "C")
    return df.set_index("material_id")["abc"].to_dict()

def bar_color_for_month(year,month,cy,cm,cutoff):
    # chart bar colors: amber = current month, gray = old history, navy = recent 12M
    try: ts=pd.Timestamp(year=int(year),month=int(month),day=1)
    except: return "#CBD5E1"
    if int(year)==cy and int(month)==cm: return "#D97706"
    elif ts<cutoff: return "#CBD5E1"
    else: return "#1B3A6B"

@st.cache_resource(show_spinner=False)
def load_all_models():
    """
    cache_resource — loads pkl files ONCE and keeps in memory.
    Not reloaded on every rerun. Only reloads when app restarts.
    """
    mdir = os.getenv("MODELS_DIR", "models"); b = {}
    for name, fname in [("lead_time","lead_time_model.pkl"),
                         ("demand_forecast","demand_forecast_models.pkl")]:
        p = os.path.join(mdir, fname)
        if os.path.exists(p):
            try:
                with open(p,"rb") as f: b[name] = pickle.load(f)
            except: pass
    return b

@st.cache_data(ttl=30, show_spinner=False)
def cached_load():
    """Reloads CSVs at most once every 30 seconds."""
    return load_data()

@st.cache_data(ttl=30, show_spinner=False)
def cached_static_snapshot(_data):
    """
    Static snapshot cached — 15-material loop runs once per 30s.
    Underscore prefix tells Streamlit not to hash the DataFrame arg.
    """
    snap = get_static_snapshot(_data)
    snap["abc"] = snap["material_id"].map(compute_abc(_data["materials"]))
    return snap

@st.cache_data(ttl=30, show_spinner=False)
def cached_monthly(_data):
    """Monthly consumption cached — CSV scan runs once per 30s."""
    return get_monthly_consumption(_data)

@st.cache_data(ttl=300, show_spinner=False)
def cached_dynamic_snapshot(_data, _fm, _fs, _flf, _lt_m, _lt_s, _lt_l):
    """
    Dynamic snapshot cached for 5 minutes.
    _flf = fc_last_features from pkl — instant prediction, no CSV scan.
    Both Planning & Forecast and Procurement Plan share this cache result.
    """
    dyn = get_dynamic_snapshot(_data, _fm, _fs, _flf, _lt_m, _lt_s, _lt_l)
    dyn["abc"] = dyn["material_id"].map(compute_abc(_data["materials"]))
    return dyn

@st.cache_data(ttl=30, show_spinner=False)
def cached_running_stock(_data):
    """Running stock history cached — scans all PO + sales rows."""
    return get_running_stock(_data)

def clear_cache(): st.cache_data.clear()

# ── GLOBAL VARS ───────────────────────────────────────────────
# Loaded once per rerun (all cached): CSV data, today's date,
# 12-month cutoff, ML models, static snapshot and monthly consumption.
data      = cached_load()
today     = pd.Timestamp.today().normalize()
cutoff    = today - pd.DateOffset(months=12)
cy        = today.year
cm        = today.month
sales     = data["sales"]
total_rows= len(sales)
ml_bundle = load_all_models()
fc_available = "demand_forecast" in ml_bundle

# Operational Dashboard + Inventory Insights always use STATIC snapshot
# Planning & Forecast builds its own DYNAMIC snapshot using ML models
abc_map  = compute_abc(data["materials"])
snapshot = cached_static_snapshot(data)
monthly  = cached_monthly(data)
mat_options = snapshot["material_name"].tolist()
mat_ids     = snapshot["material_id"].tolist()

def get_forecast(mid,n=3):
    # Rolling n-month demand forecast for one material using the saved Ridge model.
    # Feeds each prediction back in as lag_1 so month 2 and 3 build on month 1.
    if not fc_available: return None
    fm=ml_bundle["demand_forecast"]["models"]; fs=ml_bundle["demand_forecast"]["scalers"]
    mat_m=monthly[monthly["material_id"]==mid].dropna(subset=["lag_1","lag_2","lag_3"]).copy()
    if mid not in fm or len(mat_m)<3: return None
    model=fm[mid]; scaler=fs[mid]
    avail=[c for c in ["month_index","month","lag_1","lag_2","lag_3","rolling_3m_avg"] if c in mat_m.columns]
    last=mat_m.iloc[-1]
    l1=float(last["total_consumed"]); l2=float(last.get("lag_1",l1)); l3=float(last.get("lag_2",l1))
    r3=float(last.get("rolling_3m_avg",l1))
    li=int(last["month_index"]); lm=int(last.get("month",last.get("month_of_year",6)))
    fc=[]
    for i in range(n):
        mo=((lm+i)%12)+1
        row={"month_index":li+i+1,"month":mo,"lag_1":l1,"lag_2":l2,"lag_3":l3,"rolling_3m_avg":r3}
        X=scaler.transform(pd.DataFrame([row])[avail])
        pr=max(0,float(model.predict(X)[0]))
        fc.append(pr); l3,l2,l1=l2,l1,pr; r3=(r3*2+pr)/3
    return fc

# ── TOP NAVIGATION ────────────────────────────────────────────
# Brand on the left (click -> main dashboard) + 3 page links, on every page
HOME_VIEW = "Operational Dashboard"
NAV_LINKS = {
    "nav_insights": "Inventory Insights",
    "nav_planning": "Planning & Forecast",
    "nav_procure":  "Procurement Plan",
    "nav_copilot":  "AI Copilot",
}
if "view" not in st.session_state:
    st.session_state.view = HOME_VIEW

def go_to(v):
    changed = st.session_state.view != v or st.session_state.get("detail_mid")
    st.session_state.view = v
    st.session_state.detail_mid = None
    if changed:
        st.rerun()

st.markdown('<div id="page-top"></div>', unsafe_allow_html=True)
nav_cols = st.columns([2.6, 1.25, 1.25, 1.15, 1.0], vertical_alignment="center")
with nav_cols[0]:
    if st.button("🏭 InventIP", key="nav_home", type="tertiary", help="Back to main dashboard"):
        go_to(HOME_VIEW)
    st.markdown('<div class="nav-sub">Inventory Intelligence Platform</div>', unsafe_allow_html=True)
for col, (nav_key, nav_label) in zip(nav_cols[1:], NAV_LINKS.items()):
    with col:
        if st.button(nav_label, key=nav_key, type="tertiary"):
            go_to(nav_label)

active_key = [k for k, v in NAV_LINKS.items() if v == st.session_state.view]
if active_key:
    st.markdown(f"<style>.st-key-{active_key[0]} button{{color:#1B3A6B!important;font-weight:700!important;border-bottom:2.5px solid #1B3A6B!important;border-radius:0!important;}}</style>", unsafe_allow_html=True)
st.markdown('<div class="nav-line"></div>', unsafe_allow_html=True)

# Floating back-to-top arrow — visible on every page
st.markdown('<a href="#page-top" class="back-to-top" title="Back to top">⬆</a>', unsafe_allow_html=True)

view = st.session_state.view

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏭 InventIP")
    st.markdown('<div style="font-size:.75rem;color:#94A3B8;margin-bottom:1rem;">Inventory Intelligence Platform</div>',unsafe_allow_html=True)
    st.markdown("---")
    hr=len(sales[sales["date"]<cutoff])
    rr=len(sales[(sales["date"]>=cutoff)&(sales["date"]<today)])
    cr=len(sales[sales["date"]>=today])
    st.markdown("**Data Zones**")
    for lbl,val in [("🔵 Historical",hr),("🟢 Recent 12M",rr),("🟡 Current",cr)]:
        st.markdown(f'<div class="sb-row"><span>{lbl}</span><span class="sb-val">{val:,} rows</span></div>',unsafe_allow_html=True)
    st.markdown("---")
    if fc_available: st.success("✅ ML Models Loaded")
    else: st.warning("⚠️ Run model.py to enable ML")

# ══════════════════════════════════════════════════════════════
# VIEW 1b — MATERIAL DETAIL PAGE (opened from a health-grid card)
# ══════════════════════════════════════════════════════════════
if view=="Operational Dashboard" and st.session_state.get("detail_mid"):
    mid  = st.session_state.detail_mid
    mrow = snapshot[snapshot["material_id"]==mid]
    if len(mrow)==0:
        st.session_state.detail_mid=None; st.rerun()
    mrow = mrow.iloc[0]

    st.button("← Back to Dashboard", key="back_dash", type="tertiary",
              on_click=lambda: st.session_state.update(detail_mid=None, scroll_to="health-grid"))
    bg  = STATUS_BG.get(mrow["status"],"#fff")
    bdr = STATUS_BORDER.get(mrow["status"],"#E2E8F0")
    st.markdown(f'<div class="page-title">{mrow["material_name"]} {abc_badge(mrow.get("abc","C"))}</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">{mrow["category"]} &nbsp;|&nbsp; {mid} &nbsp;|&nbsp; {badge_html(mrow["status"])}</div>',unsafe_allow_html=True)

    hd = st.columns(5)
    header_tiles=[
        (f"{mrow['current_stock']} {mrow['uom']}","Current Stock"),
        (str(mrow['reorder_point']),"Reorder Point"),
        (str(mrow['safety_stock']),"Safety Stock"),
        (f"{mrow['days_stock_remaining']}","Days Remaining"),
        (fmt_inr(mrow['current_stock']*mrow['unit_cost']),"Stock Value"),
    ]
    for col,(v,l) in zip(hd,header_tiles):
        with col:
            st.markdown(f'<div class="kpi-card" style="background:{bg};border-color:{bdr};"><div class="kpi-value" style="font-size:1.25rem;">{v}</div><div class="kpi-label">{l}</div></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)

    dt1,dt2,dt3,dt4 = st.tabs(["📊 Monthly Consumption","📦 Purchase Orders","🚚 Supplier Performance","🏭 Usage in Products"])

    # ── Monthly consumption (same look as Inventory Insights) ─
    with dt1:
        mm=monthly[monthly["material_id"]==mid].copy()
        mm=mm.dropna(subset=["year","month"]).copy()
        mm=mm[mm.apply(lambda r:pd.Timestamp(year=int(r["year"]),month=int(r["month"]),day=1)>=cutoff,axis=1)].copy()
        if len(mm)==0:
            st.info("No consumption history in the current window.")
        else:
            xl2=[f"{int(r['year'])}-{int(r['month']):02d}" for _,r in mm.iterrows()]
            bc2=[bar_color_for_month(int(r["year"]),int(r["month"]),cy,cm,cutoff) for _,r in mm.iterrows()]
            fig_mc=go.Figure()
            fig_mc.add_trace(go.Bar(x=xl2,y=mm["total_consumed"],marker_color=bc2,name="Consumption"))
            fig_mc.add_trace(go.Scatter(x=xl2,y=mm["rolling_3m_avg"],name="3M Avg",line=dict(color="#EF4444",width=2,dash="dot"),mode="lines"))
            fig_mc.update_layout(height=320,paper_bgcolor="white",plot_bgcolor="#F8FAFC",legend=dict(orientation="h",yanchor="bottom",y=1.02),xaxis_title="Month",yaxis_title="Units",font=dict(family="Inter",size=12),margin=dict(l=10,r=10,t=40,b=20))
            st.plotly_chart(fig_mc,use_container_width=True)
            st.caption("🟦 Recent &nbsp;|&nbsp; 🟨 Current month &nbsp;|&nbsp; 🔴 dashed = 3M rolling avg")
            c1,c2,c3=st.columns(3)
            with c1: st.metric("Total Consumed",f"{mm['total_consumed'].sum():,.0f}")
            with c2: st.metric("Peak Month",f"{mm['total_consumed'].max():,.0f}")
            with c3: st.metric("Monthly Avg",f"{mm['total_consumed'].mean():,.0f}")

    # ── Purchase orders for this material ─────────────────────
    with dt2:
        pos_m=data["purchase_orders"].copy()
        pos_m=pos_m[pos_m["material_id"]==mid].copy()
        if len(pos_m)==0:
            st.info("No purchase orders for this material.")
        else:
            sups_df=data["suppliers"]
            pos_m["delivery_variance_days"]=(pos_m["actual_delivery_date"]-pos_m["expected_delivery_date"]).dt.days
            def poc2(r):
                if r["po_status"]=="Planned": return "#3B82F6"
                if r["po_status"] in ["Open","Confirmed"]: return "#F59E0B"
                if pd.isna(r.get("delivery_variance_days")): return "#F59E0B"
                return "#22C55E" if r["delivery_variance_days"]<=0 else "#EF4444"
            pos_m["color"]=pos_m.apply(poc2,axis=1)
            pos_m["end"]=pos_m.apply(lambda r:r["actual_delivery_date"] if pd.notna(r.get("actual_delivery_date")) else r["expected_delivery_date"],axis=1)
            fig_po2=go.Figure()
            for _,p in pos_m.sort_values("po_date").iterrows():
                sn=sups_df[sups_df["supplier_id"]==p["supplier_id"]]["supplier_name"].values
                sl=sn[0] if len(sn)>0 else p["supplier_id"]
                fig_po2.add_trace(go.Scatter(x=[p["po_date"],p["end"]],y=[p["po_id"],p["po_id"]],mode="lines+markers",line=dict(color=p["color"],width=8),marker=dict(size=8,color=p["color"]),showlegend=False,hovertemplate=f"<b>{p['po_id']}</b><br>Supplier: {sl}<br>Qty: {p['quantity_ordered']}<br>Status: {p['po_status']}<extra></extra>"))
            for lbl,clr in [("On Time","#22C55E"),("Delayed","#EF4444"),("Open/Pending","#F59E0B"),("Planned","#3B82F6")]:
                fig_po2.add_trace(go.Scatter(x=[None],y=[None],mode="lines",line=dict(color=clr,width=6),name=lbl,showlegend=True))
            fig_po2.update_layout(height=max(280,80+24*len(pos_m)),paper_bgcolor="white",plot_bgcolor="#F8FAFC",legend=dict(orientation="h",yanchor="bottom",y=1.02),xaxis_title="Date",font=dict(family="Inter",size=11),margin=dict(l=10,r=10,t=40,b=20))
            st.plotly_chart(fig_po2,use_container_width=True)
            tbl=pos_m.sort_values("po_date",ascending=False)[["po_id","po_date","quantity_ordered","unit_price","po_status","expected_delivery_date","actual_delivery_date","delivery_variance_days"]].copy()
            tbl.columns=["PO","Order Date","Qty","Unit Price","Status","Expected","Actual","Variance (days)"]
            st.dataframe(tbl,use_container_width=True,hide_index=True)

    # ── Suppliers who can deliver this material ───────────────
    with dt3:
        smap=data["supplier_map"]; sups_df=data["suppliers"]
        sm_m=smap[smap["material_id"]==mid].merge(sups_df,on="supplier_id",how="left")
        if len(sm_m)==0:
            st.info("No suppliers mapped to this material.")
        else:
            pos_all=data["purchase_orders"]
            pom=pos_all[(pos_all["material_id"]==mid)&(pos_all["po_status"]=="Delivered")].copy()
            pom["var"]=(pom["actual_delivery_date"]-pom["expected_delivery_date"]).dt.days
            if len(pom)>0:
                stats=pom.groupby("supplier_id").agg(orders=("po_id","count"),on_time=("var",lambda s:(s<=0).mean()*100),avg_var=("var","mean")).reset_index()
                sm_m=sm_m.merge(stats,on="supplier_id",how="left")
            else:
                sm_m["orders"]=0; sm_m["on_time"]=np.nan; sm_m["avg_var"]=np.nan
            sb=sm_m.dropna(subset=["on_time"])
            if len(sb)>0:
                cols_b=["#22C55E" if v>=80 else "#F59E0B" if v>=60 else "#EF4444" for v in sb["on_time"]]
                fig_s=go.Figure(go.Bar(x=sb["supplier_name"],y=sb["on_time"],marker_color=cols_b,text=[f"{v:.0f}%" for v in sb["on_time"]],textposition="outside"))
                fig_s.update_layout(height=280,paper_bgcolor="white",plot_bgcolor="#F8FAFC",yaxis=dict(range=[0,115],title="On-Time %"),xaxis_title="Supplier",font=dict(family="Inter",size=12),margin=dict(l=10,r=10,t=20,b=40))
                st.plotly_chart(fig_s,use_container_width=True)
            d=sm_m[["supplier_name","country","supplier_rating","lead_time_days","unit_price","preferred","orders","on_time","avg_var"]].copy()
            d["unit_price"]=d["unit_price"].apply(fmt_inr)
            d["on_time"]=d["on_time"].apply(lambda v:"—" if pd.isna(v) else f"{v:.0f}%")
            d["avg_var"]=d["avg_var"].apply(lambda v:"—" if pd.isna(v) else f"{v:+.1f}d")
            d["orders"]=d["orders"].fillna(0).astype(int)
            d["preferred"]=d["preferred"].apply(lambda x:"⭐ Preferred" if x else "")
            d.columns=["Supplier","Country","Rating","Lead Time (d)","Unit Price","Preferred","Delivered POs","On-Time %","Avg Variance"]
            st.dataframe(d,use_container_width=True,hide_index=True)

    # ── Usage of this material across the 3 products ──────────
    with dt4:
        mb=data["bom"][data["bom"]["material_id"]==mid].copy()
        if len(mb)==0:
            st.info("This material is not used in any product BOM.")
        else:
            pm={"PRD001":"Family Sedan Kit","PRD002":"SUV Drive Kit","PRD003":"Hatchback Brake Kit"}
            mb["pname"]=mb["product_id"].map(pm)
            fig_bm=go.Figure(go.Bar(x=mb["pname"],y=mb["effective_qty"],marker_color=["#1B3A6B","#0D7C6E","#D97706"][:len(mb)],text=[f"{v:.2f}" for v in mb["effective_qty"]],textposition="outside"))
            fig_bm.update_layout(height=280,paper_bgcolor="white",plot_bgcolor="#F8FAFC",xaxis_title="Product",yaxis_title="Effective Qty per Unit Built",font=dict(family="Inter",size=12),margin=dict(l=10,r=10,t=20,b=20))
            st.plotly_chart(fig_bm,use_container_width=True)
            d3=mb[["pname","qty_per_unit","scrap_factor","effective_qty"]].copy()
            d3.columns=["Product","Qty per Unit","Scrap Factor","Effective Qty"]
            st.dataframe(d3,use_container_width=True,hide_index=True)
            st.caption(f"Used in **{len(mb)} of 3** products. Effective Qty = Qty per Unit × (1 + scrap factor).")

    if st.session_state.get("scroll_to"):
        components.html(f"<script>setTimeout(function(){{var el=parent.document.getElementById('{st.session_state.scroll_to}');if(el)el.scrollIntoView({{behavior:'smooth',block:'start'}});}},400);</script>",height=0)
        st.session_state.scroll_to=None

# ══════════════════════════════════════════════════════════════
# VIEW 1 — OPERATIONAL DASHBOARD
# ══════════════════════════════════════════════════════════════
elif view=="Operational Dashboard":
    st.markdown('<div class="page-title">Operational Dashboard</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">{today.strftime("%A, %d %B %Y")} — Current inventory status</div>',unsafe_allow_html=True)

    total_mats = len(snapshot)
    normal_c   = len(snapshot[snapshot["status"] == "NORMAL"])
    reorder_c  = len(snapshot[snapshot["status"] == "REORDER"])
    crit_c     = len(snapshot[snapshot["status"].isin(["CRITICAL","STOCKOUT"])])
    over_c     = len(snapshot[snapshot["status"] == "OVERSTOCK"])
    open_po_c  = len(get_open_pos(data))

    # Total stock value = current_stock x unit_cost per material
    stock_value     = float((snapshot["current_stock"] * snapshot["unit_cost"]).sum())
    stock_value_str = fmt_inr(stock_value)

    # 7 clickable KPI cards — click jumps to the section and filters the
    # health grid + days-remaining chart; clicking the active card clears it
    if "kpi_filter" not in st.session_state: st.session_state.kpi_filter = "TOTAL"
    if "show_howto" not in st.session_state: st.session_state.show_howto = False

    def kpi_click(code, anchor):
        if code == st.session_state.kpi_filter and code != "TOTAL":
            st.session_state.kpi_filter = "TOTAL"
        else:
            st.session_state.kpi_filter = code
        st.session_state.scroll_to = anchor

    KPI_CARDS = [
        ("kpi_total",   "TOTAL",   str(total_mats), "TOTAL MATERIALS",     "health-grid"),
        ("kpi_normal",  "NORMAL",  str(normal_c),   "NORMAL",              "health-grid"),
        ("kpi_reorder", "REORDER", str(reorder_c),  "REORDER",             "health-grid"),
        ("kpi_crit",    "CRIT",    str(crit_c),     "CRITICAL + STOCKOUT", "health-grid"),
        ("kpi_over",    "OVER",    str(over_c),     "OVERSTOCK",           "health-grid"),
        ("kpi_openpo",  "OPENPO",  str(open_po_c),  "OPEN PURCHASE ORDERS",            "open-pos"),
        ("kpi_value",   "VALUE",   stock_value_str, "CURRENT STOCK VALUE", "stock-value"),
    ]
    KPI_STATUS    = {"NORMAL":["NORMAL"],"REORDER":["REORDER"],"CRIT":["CRITICAL","STOCKOUT"],"OVER":["OVERSTOCK"]}
    FILTER_LABELS = {"NORMAL":"Normal","REORDER":"Reorder","CRIT":"Critical + Stockout","OVER":"Overstock"}
    sel_statuses  = KPI_STATUS.get(st.session_state.kpi_filter)

    # value colors use Streamlit markdown color tags so they always render
    KPI_MD_COLOR = {"kpi_normal":"green","kpi_reorder":"orange","kpi_over":"blue","kpi_openpo":"orange"}
    cols_k = st.columns(7)
    for col,(key,code,val,lbl,anchor) in zip(cols_k, KPI_CARDS):
        mc  = KPI_MD_COLOR.get(key)
        big = f":{mc}[**{val}**]" if mc else f"**{val}**"
        with col:
            st.button(f"{big}  \n{lbl}", key=key, on_click=kpi_click, args=(code, anchor), width="stretch")
    active_card = [k for k,c,_,_,_ in KPI_CARDS if c == st.session_state.kpi_filter]
    if active_card:
        st.markdown(f"<style>.st-key-{active_card[0]} button{{outline:2.5px solid #1B3A6B;outline-offset:1.5px;}}</style>", unsafe_allow_html=True)

    def toggle_howto():
        st.session_state.show_howto = not st.session_state.show_howto

    st.button(("📖 Hide guide" if st.session_state.show_howto else "📖 How this dashboard works"),
              key="howworks_btn", type="tertiary", on_click=toggle_howto)
    st.markdown("<br>",unsafe_allow_html=True)

    # LEGEND — toggled by the 'How this dashboard works' button
    legend_html = """
    <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:1rem 1.2rem;margin-bottom:1rem;">
      <div style="font-size:.8rem;font-weight:700;color:#1B3A6B;margin-bottom:.6rem;">How to Read This Dashboard</div>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:.5rem;margin-bottom:.8rem;">
        <div style="background:#F0FDF4;border:1.5px solid #22C55E;border-radius:8px;padding:.6rem .8rem;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;"><div style="width:10px;height:10px;border-radius:50%;background:#22C55E;"></div><span style="font-size:.78rem;font-weight:700;color:#14532D;">NORMAL</span></div>
          <div style="font-size:.72rem;color:#374151;">Stock is healthy. No action needed.</div>
        </div>
        <div style="background:#FFFBEB;border:1.5px solid #F59E0B;border-radius:8px;padding:.6rem .8rem;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;"><div style="width:10px;height:10px;border-radius:50%;background:#F59E0B;"></div><span style="font-size:.78rem;font-weight:700;color:#92400E;">REORDER</span></div>
          <div style="font-size:.72rem;color:#374151;">Below reorder point. Raise a PO soon.</div>
        </div>
        <div style="background:#FEF2F2;border:1.5px solid #EF4444;border-radius:8px;padding:.6rem .8rem;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;"><div style="width:10px;height:10px;border-radius:50%;background:#EF4444;"></div><span style="font-size:.78rem;font-weight:700;color:#991B1B;">CRITICAL</span></div>
          <div style="font-size:.72rem;color:#374151;">Below safety stock. Order today.</div>
        </div>
        <div style="background:#ED1C24;border:1.5px solid #B01018;border-radius:8px;padding:.6rem .8rem;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;"><div style="width:10px;height:10px;border-radius:50%;background:#FFFFFF;"></div><span style="font-size:.78rem;font-weight:700;color:#FFFFFF;">STOCKOUT</span></div>
          <div style="font-size:.72rem;color:#FFE4E4;">No stock. Production stopped.</div>
        </div>
        <div style="background:#EFF6FF;border:1.5px solid #3B82F6;border-radius:8px;padding:.6rem .8rem;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;"><div style="width:10px;height:10px;border-radius:50%;background:#3B82F6;"></div><span style="font-size:.78rem;font-weight:700;color:#1E40AF;">OVERSTOCK</span></div>
          <div style="font-size:.72rem;color:#374151;">Too much stock. Delay next order.</div>
        </div>
      </div>
      <div style="border-top:1px solid #E2E8F0;padding-top:.6rem;display:flex;gap:1rem;flex-wrap:wrap;">
        <span style="font-size:.78rem;font-weight:700;color:#1B3A6B;margin-right:4px;">ABC:</span>
        <div style="display:flex;align-items:center;gap:6px;"><span class="abc-a">A</span><span style="font-size:.73rem;color:#374151;">High priority — 70% of spend. Monitor daily.</span></div>
        <div style="display:flex;align-items:center;gap:6px;"><span class="abc-b">B</span><span style="font-size:.73rem;color:#374151;">Medium priority. Review weekly.</span></div>
        <div style="display:flex;align-items:center;gap:6px;"><span class="abc-c">C</span><span style="font-size:.73rem;color:#374151;">Low priority. Standard rules.</span></div>
      </div>
    </div>"""
    if st.session_state.show_howto:
        st.markdown(legend_html,unsafe_allow_html=True)
        st.button("🔗 Full details — formulas & explanations", key="jump_full", type="tertiary",
                  on_click=lambda: st.session_state.update(scroll_to="howworks-full", open_full=True))

    with st.expander("📥 Enter Today's Sales",expanded=False):
        c1,c2,c3,c4=st.columns([2,2,2,1])
        with c1: s1=st.number_input("Family Sedan Kit",0,200,0,1,key="s1")
        with c2: s2=st.number_input("SUV Drive Kit",0,200,0,1,key="s2")
        with c3: s3=st.number_input("Hatchback Brake Kit",0,200,0,1,key="s3")
        with c4:
            ed=st.date_input("Date",value=today.date())
            if st.button("Save",type="primary",use_container_width=True):
                if s1+s2+s3==0: st.warning("Enter at least one unit.")
                else:
                    save_daily_sales(str(ed),{"PRD001":s1,"PRD002":s2,"PRD003":s3})
                    st.success("✅ Saved."); clear_cache(); st.rerun()

    st.markdown('<div id="health-grid"></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Inventory Health Grid — Current Status</div>',unsafe_allow_html=True)
    abc_filter=st.multiselect("Filter by ABC Class",["A","B","C"],default=["A","B","C"],key="abc_filt")
    grid_df=snapshot[snapshot["abc"].isin(abc_filter)].copy()
    if sel_statuses:
        grid_df=grid_df[grid_df["status"].isin(sel_statuses)].copy()
        st.caption(f"Filter: {FILTER_LABELS[st.session_state.kpi_filter]} — showing {len(grid_df)} of {len(snapshot)} materials. Click the highlighted card again to clear.")
    if len(grid_df)==0:
        st.info("No materials match this filter right now.")
    # one card per column so the invisible overlay button covers exactly
    # one card — clicking anywhere on a card opens its detail page
    GRID_COLS = 6
    grid_chunks = [grid_df.iloc[i:i+GRID_COLS] for i in range(0, len(grid_df), GRID_COLS)]
    for chunk in grid_chunks:
      cols_g = st.columns(GRID_COLS)
      for col,(_,row) in zip(cols_g, chunk.iterrows()):
        ac  = row.get("abc","C")
        bg  = STATUS_BG.get(row["status"],"#fff")
        bdr = STATUS_BORDER.get(row["status"],"#E2E8F0")
        clr = STATUS_COLORS.get(row["status"],"#64748B")
        txt = "#FFFFFF" if row["status"]=="STOCKOUT" else "#0F172A"
        mc  = "#FFE4E4" if row["status"]=="STOCKOUT" else "#64748B"
        stock_clr = "#FFFFFF" if row["status"]=="STOCKOUT" else clr
        with col:
            st.markdown(f"""<div class="mat-card" style="background:{bg};border-color:{bdr};">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.55rem;">{badge_html(row['status'])}{abc_badge(ac)}</div>
            <div class="mat-name" style="color:{txt};">{row['material_name']}</div>
            <div class="mat-cat" style="color:{mc};">{row['category']}</div>
            <div class="mat-stock" style="color:{stock_clr};">{row['current_stock']} <span style="font-size:.75rem;font-weight:600;">{row['uom']}</span></div>
            <div style="border-top:1px dashed {bdr};margin:.55rem 0 .4rem 0;"></div>
            <div class="mat-kv" style="color:{mc};"><span>Reorder Point</span><span style="font-weight:700;color:{txt};">{row['reorder_point']}</span></div>
            <div class="mat-kv" style="color:{mc};"><span>Safety Stock</span><span style="font-weight:700;color:{txt};">{row['safety_stock']}</span></div>
            <div class="mat-kv" style="color:{mc};"><span>Days Remaining</span><span style="font-weight:700;color:{txt};">{row['days_stock_remaining']}</span></div>
            </div>""",unsafe_allow_html=True)
            st.button("Open details", key=f"det_{row['material_id']}",
                      on_click=lambda m=row['material_id']: st.session_state.update(detail_mid=m, scroll_to="page-top"))

    st.markdown('<div id="days-bar"></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="margin-top:1rem;">⏱️ Days of Stock Remaining</div>',unsafe_allow_html=True)
    st.markdown('<div class="threshold-note"><b>Red line</b> = 10 days (Critical) &nbsp;|&nbsp; <b>Amber line</b> = 30 days (Warning) &nbsp;|&nbsp; <b>[A/B/C]</b> = ABC class</div>',unsafe_allow_html=True)
    cd=snapshot[snapshot["days_stock_remaining"].notna()].sort_values("days_stock_remaining").copy()
    if sel_statuses:
        cd=cd[cd["status"].isin(sel_statuses)].copy()
    if len(cd)==0:
        st.info("No materials match this filter right now.")
    else:
        cd["y_label"]=cd.apply(lambda r:f"{r['material_name']}  [{abc_map.get(r['material_id'],'C')}]",axis=1)
        fig_d=go.Figure(go.Bar(x=cd["days_stock_remaining"],y=cd["y_label"],orientation="h",
            marker_color=[STATUS_COLORS.get(s,"#64748B") for s in cd["status"]],
            text=[f"{d:.0f}d" for d in cd["days_stock_remaining"]],textposition="outside",
            hovertemplate="<b>%{y}</b><br>Days: %{x:.1f}<extra></extra>"))
        fig_d.add_vline(x=10,line_dash="solid",line_color="#EF4444",line_width=2,
            annotation_text="Critical (10d)",annotation_font_color="#EF4444",annotation_position="top right",annotation_font_size=11)
        fig_d.add_vline(x=30,line_dash="solid",line_color="#F59E0B",line_width=2,
            annotation_text="Warning (30d)",annotation_font_color="#92400E",annotation_position="top right",annotation_font_size=11)
        fig_d.update_layout(height=max(240,110+26*len(cd)),paper_bgcolor="white",plot_bgcolor="#F8FAFC",
            font=dict(family="Inter",size=12),margin=dict(l=10,r=90,t=30,b=20),
            xaxis=dict(title="Days of Stock Remaining",gridcolor="#F1F5F9"),yaxis=dict(gridcolor="#F1F5F9"))
        st.plotly_chart(fig_d,use_container_width=True)

    # ── OPEN PURCHASE ORDERS (below the days-remaining chart) ─
    st.markdown('<div id="open-pos"></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="margin-top:1rem;">📦 Open Purchase Orders</div>',unsafe_allow_html=True)
    open_pos_df=get_open_pos(data)
    if len(open_pos_df)==0:
        st.info("No open purchase orders right now.")
    else:
        for _,po in open_pos_df.iterrows():
            mat_row=snapshot[snapshot["material_id"]==po["material_id"]]
            days_rem=float(mat_row["days_stock_remaining"].values[0]) if len(mat_row)>0 else 999
            gap=(po["days_to_delivery"]-days_rem) if po["days_to_delivery"] is not None else None
            mat_name=mat_row["material_name"].values[0] if len(mat_row)>0 else po["material_id"]
            card_class="plan-card" if po["po_status"]=="Planned" else "amber-card"
            st.markdown(f'<div class="{card_class}">',unsafe_allow_html=True)
            c1,c2,c3=st.columns([2.5,2.5,1])
            with c1:
                st.markdown(f'**{mat_name}** — PO `{po["po_id"]}` — **{po["po_status"]}**')
                st.markdown(f'Supplier: {po["supplier_name"]} &nbsp;|&nbsp; Qty: {po["quantity_ordered"]} &nbsp;|&nbsp; Value: {fmt_inr(po["total_value"])}')
            with c2:
                if po["is_overdue"]:
                    st.markdown(f'⛔ **OVERDUE** — Expected: {po["expected_delivery_date"].strftime("%d %b %Y")}')
                else:
                    st.markdown(f'📅 Expected: {po["expected_delivery_date"].strftime("%d %b %Y")} &nbsp;|&nbsp; {po["days_to_delivery"]} days away')
                if gap and gap>0:
                    cls="gap-crit" if gap>7 else "gap-warn"
                    st.markdown(f'<span class="{cls}">{"⛔" if gap>7 else "⚠️"} Gap: {gap:.1f} days</span>',unsafe_allow_html=True)
            with c3:
                if po["po_status"] in ["Open","Planned"]:
                    if st.button("Confirm",key=f"conf_{po['po_id']}",use_container_width=True):
                        confirm_po(po["po_id"]); clear_cache(); st.rerun()
                if st.button("📥 Received",key=f"recv_{po['po_id']}",use_container_width=True):
                    st.session_state[f"rm_{po['po_id']}"]=True
            if st.session_state.get(f"rm_{po['po_id']}",False):
                rq=st.number_input("Units received",1,value=int(po["quantity_ordered"]),key=f"rq_{po['po_id']}")
                rd=st.date_input("Receipt date",value=datetime.today().date(),key=f"rd_{po['po_id']}")
                if st.button("✅ Confirm Receipt",key=f"cr_{po['po_id']}",type="primary"):
                    mark_received(po["po_id"],po["material_id"],rq,str(rd))
                    st.session_state[f"rm_{po['po_id']}"]=False
                    st.success(f"✅ {rq} units received."); clear_cache(); st.rerun()
            st.markdown("</div>",unsafe_allow_html=True)

    # ── CURRENT INVENTORY VALUE ───────────────────────────────
    st.markdown('<div id="stock-value"></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="margin-top:1rem;">💰 Current Inventory Value</div>',unsafe_allow_html=True)
    sv=snapshot.copy()
    sv["stock_value"]=sv["current_stock"]*sv["unit_cost"]
    sv=sv.sort_values("stock_value")
    total_units=int(sv["current_stock"].sum())
    top_v=sv.iloc[-1]
    a_share=(sv.loc[sv["abc"]=="A","stock_value"].sum()/stock_value*100) if stock_value>0 else 0
    vt=st.columns(4)
    value_tiles=[
        (stock_value_str,"Total Inventory Value"),
        (f"{total_units:,}","Units in Stock"),
        (f"{a_share:.0f}%","Value Held in A-Class Materials"),
        (top_v["material_name"],f"Highest Value — {fmt_inr(top_v['stock_value'])}"),
    ]
    for col,(v,l) in zip(vt,value_tiles):
        with col:
            st.markdown(f'<div class="kpi-card"><div class="kpi-value" style="font-size:1.25rem;color:#1B3A6B;">{v}</div><div class="kpi-label">{l}</div></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    fig_v=go.Figure(go.Bar(x=sv["stock_value"],y=sv["material_name"],orientation="h",
        marker_color="#1B3A6B",
        text=[fmt_inr(v) for v in sv["stock_value"]],textposition="outside",
        customdata=np.stack([sv["current_stock"],sv["unit_cost"],sv["category"]],axis=-1),
        hovertemplate="<b>%{y}</b><br>Value: ₹%{x:,.0f}<br>Stock: %{customdata[0]} units × ₹%{customdata[1]}<br>Category: %{customdata[2]}<extra></extra>"))
    fig_v.update_layout(height=460,paper_bgcolor="white",plot_bgcolor="#F8FAFC",
        font=dict(family="Inter",size=12),margin=dict(l=10,r=110,t=10,b=20),
        xaxis=dict(title="Stock Value (₹)",gridcolor="#F1F5F9"),yaxis=dict(gridcolor="#F1F5F9"))
    st.plotly_chart(fig_v,use_container_width=True)
    cat_v=sv.groupby("category")["stock_value"].sum().sort_values(ascending=False)
    cat_chips="".join([f'<div class="legend-item"><div class="legend-dot" style="background:{CAT_COLORS.get(c,"#64748B")};"></div>{c}: <b>{fmt_inr(v)}</b>&nbsp;({v/stock_value*100:.0f}%)</div>' for c,v in cat_v.items()])
    st.markdown(f'<div class="legend-strip">{cat_chips}</div>',unsafe_allow_html=True)

    # Smooth-scroll to the section chosen via a KPI card click
    if st.session_state.get("scroll_to"):
        components.html(f"<script>setTimeout(function(){{var el=parent.document.getElementById('{st.session_state.scroll_to}');if(el)el.scrollIntoView({{behavior:'smooth',block:'start'}});}},400);</script>",height=0)
        st.session_state.scroll_to=None

    # ── HOW THIS WORKS SECTION ────────────────────────────────
    st.markdown('<div id="howworks-full"></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    with st.expander("📖 How This Dashboard Works — Formulas & Explanations", expanded=st.session_state.pop("open_full", False)):
        st.markdown("""
        <div style="font-size:.82rem;color:#1B3A6B;font-weight:700;margin-bottom:1rem;font-size:1rem;">
        Understanding the Numbers on Your Dashboard
        </div>
        """, unsafe_allow_html=True)

        # STATUS EXPLANATIONS
        st.markdown("""
        <div style="font-weight:700;color:#1B3A6B;font-size:.9rem;margin-bottom:.6rem;">
        🔴 What Do the Status Labels Mean?
        </div>
        """, unsafe_allow_html=True)

        statuses = [
            ("NORMAL",  "#22C55E", "#F0FDF4",
             "Stock is comfortable.",
             "Current stock is above the Reorder Point. You have enough buffer to continue production without any immediate action. Keep monitoring."),
            ("REORDER", "#F59E0B", "#FFFBEB",
             "Time to place an order.",
             "Stock has fallen to or below the Reorder Point. This doesn't mean you've run out — it means if you don't order now, you might run out before the next delivery arrives. Raise a Purchase Order today."),
            ("CRITICAL", "#EF4444", "#FEF2F2",
             "Stock is dangerously low.",
             "Current stock is at or below the Safety Stock level — the emergency buffer you're supposed to always keep. This means demand variability or a delayed supplier could cause a stoppage. Order immediately."),
            ("STOCKOUT", "#FFFFFF", "#ED1C24",
             "No stock left.",
             "Current stock has hit zero. Production requiring this material is halted. Escalate urgently — contact supplier for emergency delivery and check if any stock is in transit."),
            ("OVERSTOCK","#3B82F6", "#EFF6FF",
             "Too much stock on hand.",
             "Stock is more than 2.5× the Reorder Point. You are holding excess inventory, which increases storage cost and ties up cash. Delay the next order or reduce order quantity."),
        ]
        cols_s = st.columns(5)
        for i, (lbl, clr, bg, short, long_) in enumerate(statuses):
            txt = "#FFFFFF" if lbl=="STOCKOUT" else "#0F172A"
            mc  = "#FFE4E4" if lbl=="STOCKOUT" else "#374151"
            with cols_s[i]:
                st.markdown(f"""
                <div style="background:{bg};border:2px solid {clr};border-radius:10px;padding:.9rem;min-height:200px;">
                  <div style="color:{clr};font-weight:700;font-size:.85rem;margin-bottom:4px;">{lbl}</div>
                  <div style="color:{txt};font-weight:600;font-size:.78rem;margin-bottom:6px;">{short}</div>
                  <div style="color:{mc};font-size:.72rem;line-height:1.5;">{long_}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ABC EXPLANATIONS
        st.markdown("""
        <div style="font-weight:700;color:#1B3A6B;font-size:.9rem;margin-bottom:.6rem;">
        🏷️ What Does ABC Classification Mean?
        </div>
        <div style="font-size:.78rem;color:#374151;margin-bottom:.8rem;">
        ABC is a way of ranking materials by how much of your money they represent. Not all 15 materials are equally important — A materials are expensive or critical, C materials are cheap or rarely used. This helps you decide how much attention to give each one.
        </div>
        """, unsafe_allow_html=True)

        abc_items = [
            ("A", "#854D0E", "#FEF9C3", "#FDE047",
             "Top priority — roughly 70% of total procurement spend",
             "These are your most expensive or high-volume materials. A stockout of an A-class material has the biggest financial and production impact. Monitor these daily, keep tighter safety stock, and always have a backup supplier ready."),
            ("B", "#1E40AF", "#DBEAFE", "#93C5FD",
             "Medium priority — roughly 20% of spend",
             "Important but not as critical as A. Review weekly. Standard safety stock rules apply. These materials are worth watching but don't need the same daily attention as A-class."),
            ("C", "#475569", "#F1F5F9", "#CBD5E1",
             "Low priority — roughly 10% of spend",
             "Cheap or low-volume materials. A stockout here has minimal financial impact. You can afford slightly lower safety stock and less frequent review cycles. Bulk ordering once a month is usually fine for C-class materials."),
        ]
        cols_a = st.columns(3)
        for i, (lbl, clr, bg, bdr, short, long_) in enumerate(abc_items):
            with cols_a[i]:
                st.markdown(f"""
                <div style="background:{bg};border:2px solid {bdr};border-radius:10px;padding:.9rem;min-height:160px;">
                  <div style="color:{clr};font-weight:700;font-size:1.1rem;margin-bottom:4px;">Class {lbl}</div>
                  <div style="color:{clr};font-weight:600;font-size:.78rem;margin-bottom:6px;">{short}</div>
                  <div style="color:#374151;font-size:.72rem;line-height:1.5;">{long_}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # FORMULA REFERENCE
        st.markdown("""
        <div style="font-weight:700;color:#1B3A6B;font-size:.9rem;margin-bottom:.6rem;">
        🔢 How Are These Numbers Calculated?
        </div>
        <div style="font-size:.78rem;color:#374151;margin-bottom:.8rem;">
        Every number on this dashboard comes from one of four formulas. No guesswork — pure math on your actual data.
        If ML models are loaded, the inputs become more accurate (forecast-based avg_daily and predicted lead time).
        If no ML is loaded, flat historical averages are used as fallback.
        </div>
        """, unsafe_allow_html=True)

        formulas = [
            ("Average Daily Consumption",
             "avg_daily = forecast_next_month ÷ 30",
             "How many units of this material are consumed on a typical day. If ML is loaded this uses the Model 4 demand forecast for next month divided by 30. Without ML it uses annual_demand ÷ 365.",
             "#0D7C6E"),
            ("Safety Stock (SS)",
             "SS = 1.65 × (avg_daily × 0.25) × √(lead_time_days)",
             "The emergency buffer you keep to absorb surprises — sudden demand spikes or a supplier delivering late. 1.65 is the Z-score for 95% service level. The larger your lead time and the more variable your demand, the bigger this buffer needs to be.",
             "#1B3A6B"),
            ("Reorder Point (ROP)",
             "ROP = (avg_daily × lead_time_days) + Safety Stock",
             "The stock level at which you should place a new order. Logic: you need enough stock to last through the entire lead time (while waiting for delivery) plus your safety buffer on top. When current stock drops to this number, the system raises a REORDER alert.",
             "#D97706"),
            ("Economic Order Quantity (EOQ)",
             "EOQ = √(2 × D × S ÷ H)",
             "The mathematically optimal quantity to order each time — the amount that minimises total cost (ordering cost + holding cost). D = actual 12-month consumption, S = cost per order, H = annual holding cost per unit. Too small and you pay too much in ordering fees. Too large and you pay too much in storage.",
             "#7C3AED"),
            ("Days of Stock Remaining",
             "Days = current_stock ÷ avg_daily",
             "A simple estimate of how many days the current stock will last at today's consumption rate. This is what drives the bar chart at the bottom of this dashboard. Below 10 days is red, below 30 days is amber.",
             "#EF4444"),
        ]

        for name, formula, explanation, clr in formulas:
            st.markdown(f"""
            <div style="background:#F8FAFC;border-left:4px solid {clr};border-radius:0 8px 8px 0;padding:.9rem 1.1rem;margin-bottom:.7rem;">
              <div style="font-weight:700;color:#0F172A;font-size:.83rem;margin-bottom:4px;">{name}</div>
              <div style="font-family:'Courier New',monospace;background:#EFF6FF;color:{clr};font-weight:600;font-size:.82rem;padding:5px 10px;border-radius:5px;margin-bottom:6px;display:inline-block;">{formula}</div>
              <div style="font-size:.75rem;color:#374151;line-height:1.6;">{explanation}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#FFFBEB;border:1px solid #FCD34D;border-radius:8px;padding:.8rem 1rem;font-size:.76rem;color:#78350F;margin-top:.4rem;">
        💡 <b>Key principle:</b> The Reorder Point is not the same as Safety Stock.
        ROP is when you order. Safety Stock is the floor you must never go below.
        When stock reaches ROP you have exactly enough time to receive the next delivery before hitting your safety buffer.
        If stock drops below Safety Stock, something has gone wrong — either demand spiked or the supplier was late.
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# VIEW 2 — INVENTORY INSIGHTS
# ══════════════════════════════════════════════════════════════
elif view=="Inventory Insights":
    st.markdown('<div class="page-title">Inventory Insights</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">Rolling 12-month window — cutoff: {cutoff.strftime("%d %b %Y")}</div>',unsafe_allow_html=True)
    sales_all=data["sales"]; bom=data["bom"]; pos=data["purchase_orders"]
    sups=data["suppliers"]; mats=data["materials"]
    current_s = sales_all[sales_all["date"] >= today]
    win=sales_all[sales_all["date"]>=cutoff].copy()

    tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(["Daily Sales","Monthly Consumption","Purchase Orders","Supplier Performance","BOM Criticality","Material Usage"])

    with tab1:
        # Tab 1 — Daily sales trend (7-day avg line per product) + monthly totals
        st.markdown('<div class="section-title">Daily Sales Trend</div>',unsafe_allow_html=True)
        pmap={"All Products":"ALL","Family Sedan Kit":"PRD001","SUV Drive Kit":"PRD002","Hatchback Brake Kit":"PRD003"}
        fc1,fc2=st.columns([2,2])
        with fc1: sp=st.selectbox("Product",list(pmap.keys()),key="ds_p")
        with fc2: dr=st.date_input("Date Range",value=(win["date"].min().date(),win["date"].max().date()),key="ds_r")
        pid=pmap[sp]
        ds=pd.Timestamp(dr[0]) if len(dr)==2 else win["date"].min()
        de=pd.Timestamp(dr[1]) if len(dr)==2 else win["date"].max()
        filt=win[(win["date"]>=ds)&(win["date"]<=de)]
        if pid!="ALL": filt=filt[filt["product_id"]==pid]
        cp={"PRD001":"#1B3A6B","PRD002":"#0D7C6E","PRD003":"#D97706"}
        fig_ls=go.Figure()
        for p,n in [("PRD001","Family Sedan Kit"),("PRD002","SUV Drive Kit"),("PRD003","Hatchback Brake Kit")]:
            if pid!="ALL" and p!=pid: continue
            pdf=filt[filt["product_id"]==p].groupby("date")["units_sold"].sum().reset_index()
            sm=pdf["units_sold"].rolling(7,min_periods=1).mean()
            fig_ls.add_trace(go.Scatter(x=pdf["date"],y=sm,name=n,line=dict(color=cp[p],width=2),mode="lines"))
        if len(current_s)>0:
            fig_ls.add_vrect(x0=current_s["date"].min(),x1=current_s["date"].max(),fillcolor="#F59E0B",opacity=.1,line_width=0,annotation_text="Current Month",annotation_position="top left",annotation_font_size=10)
        fig_ls.update_layout(height=300,paper_bgcolor="white",plot_bgcolor="#F8FAFC",legend=dict(orientation="h",yanchor="bottom",y=1.02),xaxis_title="Date",yaxis_title="Units (7d avg)",font=dict(family="Inter",size=12),margin=dict(l=10,r=10,t=40,b=20))
        st.plotly_chart(fig_ls,use_container_width=True)
        st.markdown('<div class="section-title">Monthly Total Units Sold</div>',unsafe_allow_html=True)
        ms=filt.copy(); ms["year"]=ms["date"].dt.year; ms["month"]=ms["date"].dt.month
        mg=ms.groupby(["year","month"])["units_sold"].sum().reset_index().sort_values(["year","month"])
        mc_=[bar_color_for_month(int(r["year"]),int(r["month"]),cy,cm,cutoff) for _,r in mg.iterrows()]
        xl=[f"{int(r['year'])}-{int(r['month']):02d}" for _,r in mg.iterrows()]
        fig_ms=go.Figure(go.Bar(x=xl,y=mg["units_sold"],marker_color=mc_,text=mg["units_sold"],textposition="outside"))
        fig_ms.update_layout(height=260,paper_bgcolor="white",plot_bgcolor="#F8FAFC",xaxis_title="Month",yaxis_title="Total Units",font=dict(family="Inter",size=12),margin=dict(l=10,r=10,t=10,b=60),xaxis_tickangle=-30)
        st.plotly_chart(fig_ms,use_container_width=True)
        st.caption("🟦 Recent history &nbsp;|&nbsp; 🟨 Current month")

    with tab2:
        # Tab 2 — Monthly consumption per material (bars + 3M rolling avg line)
        st.markdown('<div class="section-title">Monthly Material Consumption</div>',unsafe_allow_html=True)
        sm2=st.selectbox("Select Material",mat_options,key="mc_s")
        mi2=mat_ids[mat_options.index(sm2)]
        mm=monthly[monthly["material_id"]==mi2].copy()
        mm=mm[mm.apply(lambda r:pd.Timestamp(year=int(r["year"]),month=int(r["month"]),day=1)>=cutoff,axis=1)].copy()
        if len(mm)>0:
            xl2=[f"{int(r['year'])}-{int(r['month']):02d}" for _,r in mm.iterrows()]
            bc2=[bar_color_for_month(int(r["year"]),int(r["month"]),cy,cm,cutoff) for _,r in mm.iterrows()]
            fig_mc=go.Figure()
            fig_mc.add_trace(go.Bar(x=xl2,y=mm["total_consumed"],marker_color=bc2,name="Consumption"))
            fig_mc.add_trace(go.Scatter(x=xl2,y=mm["rolling_3m_avg"],name="3M Avg",line=dict(color="#EF4444",width=2,dash="dot"),mode="lines"))
            fig_mc.update_layout(height=320,paper_bgcolor="white",plot_bgcolor="#F8FAFC",legend=dict(orientation="h",yanchor="bottom",y=1.02),xaxis_title="Month",yaxis_title="Units",font=dict(family="Inter",size=12),margin=dict(l=10,r=10,t=40,b=20))
            st.plotly_chart(fig_mc,use_container_width=True)
            st.caption("🟦 Recent &nbsp;|&nbsp; 🟨 Current month &nbsp;|&nbsp; 🔴 dashed = 3M rolling avg")
            c1,c2,c3=st.columns(3)
            with c1: st.metric("Total",f"{mm['total_consumed'].sum():,.0f}")
            with c2: st.metric("Peak Month",f"{mm['total_consumed'].max():,.0f}")
            with c3: st.metric("Monthly Avg",f"{mm['total_consumed'].mean():,.0f}")

    with tab3:
        # Tab 3 — PO timeline: each line = one PO from order date to delivery
        # (green = on time, red = late, amber = open, blue = planned)
        st.markdown('<div class="section-title">Purchase Order Timeline</div>',unsafe_allow_html=True)
        pd2=pos.copy().merge(snapshot[["material_id","material_name"]],on="material_id",how="left")
        if "delivery_variance_days" not in pd2.columns:
            pd2["delivery_variance_days"]=(pd2["actual_delivery_date"]-pd2["expected_delivery_date"]).dt.days
        def poc(r):
            if r["po_status"]=="Planned": return "#3B82F6"
            if r["po_status"] in ["Open","Confirmed"]: return "#F59E0B"
            if pd.isna(r.get("delivery_variance_days")): return "#F59E0B"
            return "#22C55E" if r["delivery_variance_days"]<=0 else "#EF4444"
        pd2["color"]=pd2.apply(poc,axis=1)
        pd2["end"]=pd2.apply(lambda r:r["actual_delivery_date"] if pd.notna(r.get("actual_delivery_date")) else r["expected_delivery_date"],axis=1)
        pd2=pd2.sort_values("po_date").tail(40)
        fig_po=go.Figure()
        for _,p in pd2.iterrows():
            sn=sups[sups["supplier_id"]==p["supplier_id"]]["supplier_name"].values
            sl=sn[0] if len(sn)>0 else p["supplier_id"]
            fig_po.add_trace(go.Scatter(x=[p["po_date"],p["end"]],y=[p["material_name"],p["material_name"]],mode="lines+markers",line=dict(color=p["color"],width=8),marker=dict(size=8,color=p["color"]),showlegend=False,hovertemplate=f"<b>{p['po_id']}</b><br>Supplier: {sl}<br>Qty: {p['quantity_ordered']}<br>Status: {p['po_status']}<extra></extra>"))
        for lbl,clr in [("On Time","#22C55E"),("Delayed","#EF4444"),("Open/Pending","#F59E0B"),("Planned","#3B82F6")]:
            fig_po.add_trace(go.Scatter(x=[None],y=[None],mode="lines",line=dict(color=clr,width=6),name=lbl,showlegend=True))
        fig_po.update_layout(height=440,paper_bgcolor="white",plot_bgcolor="#F8FAFC",legend=dict(orientation="h",yanchor="bottom",y=1.02),xaxis_title="Date",font=dict(family="Inter",size=11),margin=dict(l=10,r=10,t=40,b=20))
        st.plotly_chart(fig_po,use_container_width=True)

    with tab4:
        # Tab 4 — Supplier scorecard: on-time delivery % chart + details table
        st.markdown('<div class="section-title">Supplier Performance</div>',unsafe_allow_html=True)
        sc=get_supplier_scorecard(data)
        if len(sc)>0:
            sc_c=["#22C55E" if v>=80 else "#F59E0B" if v>=60 else "#EF4444" for v in sc["on_time_pct"]]
            fig_sp=go.Figure(go.Bar(x=sc["supplier_name"],y=sc["on_time_pct"],marker_color=sc_c,text=[f"{v:.0f}%" for v in sc["on_time_pct"]],textposition="outside"))
            fig_sp.update_layout(height=320,paper_bgcolor="white",plot_bgcolor="#F8FAFC",yaxis=dict(range=[0,115],title="On-Time %"),xaxis_title="Supplier",font=dict(family="Inter",size=12),margin=dict(l=10,r=10,t=20,b=80))
            st.plotly_chart(fig_sp,use_container_width=True)
            d=sc[["supplier_name","country","supplier_rating","total_orders","on_time_pct","avg_variance"]].copy()
            d.columns=["Supplier","Country","Rating","Orders","On-Time %","Avg Variance (days)"]
            st.dataframe(d,use_container_width=True,hide_index=True)

    with tab5:
        # Tab 5 — BOM criticality bubble chart: which materials matter most
        # (x = products using it, y = qty per build, bubble size = unit cost)
        st.markdown('<div class="section-title">BOM Criticality</div>',unsafe_allow_html=True)

        bc=bom.groupby("material_id").agg(products_using=("product_id","nunique"),total_qty=("effective_qty","sum")).reset_index()
        bc=bc.merge(mats[["material_id","material_name","unit_cost","category"]],on="material_id")
        fig_bom=px.scatter(bc,x="products_using",y="total_qty",size="unit_cost",color="category",color_discrete_map=CAT_COLORS,text="material_name",size_max=55,labels={"products_using":"Products Using (out of 3)","total_qty":"Total Qty per BOM Build"})
        fig_bom.update_traces(textposition="top center",textfont_size=10)
        fig_bom.update_layout(height=440,paper_bgcolor="white",plot_bgcolor="#F8FAFC",font=dict(family="Inter",size=12),margin=dict(l=10,r=10,t=20,b=20))
        fig_bom.update_xaxes(tickvals=[1,2,3],ticktext=["1 product","2 products","3 products"],gridcolor="#F1F5F9")
        fig_bom.update_yaxes(gridcolor="#F1F5F9")
        st.plotly_chart(fig_bom,use_container_width=True)
        st.caption("Bubble size = unit cost &nbsp;|&nbsp; Top-right large bubbles = highest criticality &nbsp;|&nbsp; Bottom-left small bubbles = lowest risk")

    with tab6:
        # Tab 6 — Material ↔ product usage: how much of each material goes
        # into each of the 3 product kits (switch view by product / by material)
        st.markdown('<div class="section-title">Material Usage by Product</div>',unsafe_allow_html=True)
        vb=st.radio("View by",["By Product","By Material"],horizontal=True,key="bom_v")
        bf=bom.merge(mats[["material_id","material_name","unit_cost"]],on="material_id",how="left")
        pm={"PRD001":"Family Sedan Kit","PRD002":"SUV Drive Kit","PRD003":"Hatchback Brake Kit"}
        if vb=="By Product":
            ps=st.selectbox("Select Product",list(pm.values()),key="bp")
            pid2={v:k for k,v in pm.items()}[ps]
            pb2=bf[bf["product_id"]==pid2].copy(); pb2["tc"]=pb2["effective_qty"]*pb2["unit_cost"]
            fig_bp=go.Figure(go.Bar(x=pb2["material_name"],y=pb2["effective_qty"],marker_color="#1B3A6B",text=[f"{v:.2f}" for v in pb2["effective_qty"]],textposition="outside"))
            fig_bp.update_layout(height=280,paper_bgcolor="white",plot_bgcolor="#F8FAFC",xaxis_title="Material",yaxis_title="Effective Qty",xaxis_tickangle=-30,font=dict(family="Inter",size=11),margin=dict(l=10,r=10,t=20,b=80))
            st.plotly_chart(fig_bp,use_container_width=True)
            d2=pb2[["material_name","qty_per_unit","scrap_factor","effective_qty","unit_cost","tc"]].copy()
            d2.columns=["Material","Qty/Unit","Scrap","Eff Qty","Unit Cost","BOM Cost"]
            d2["Unit Cost"]=d2["Unit Cost"].apply(fmt_inr); d2["BOM Cost"]=d2["BOM Cost"].apply(fmt_inr)
            st.dataframe(d2,use_container_width=True,hide_index=True)
            st.metric("Total BOM Cost per Unit",fmt_inr(pb2["tc"].sum()))
        else:
            sm4=st.selectbox("Select Material",mat_options,key="bm")
            mi4=mat_ids[mat_options.index(sm4)]
            mb=bf[bf["material_id"]==mi4].copy(); mb["pname"]=mb["product_id"].map(pm)
            if len(mb)>0:
                fig_bm=go.Figure(go.Bar(x=mb["pname"],y=mb["effective_qty"],marker_color=["#1B3A6B","#0D7C6E","#D97706"][:len(mb)],text=[f"{v:.2f}" for v in mb["effective_qty"]],textposition="outside"))
                fig_bm.update_layout(height=260,paper_bgcolor="white",plot_bgcolor="#F8FAFC",xaxis_title="Product",yaxis_title="Eff Qty per Unit",font=dict(family="Inter",size=12),margin=dict(l=10,r=10,t=20,b=20))
                st.plotly_chart(fig_bm,use_container_width=True)
                d3=mb[["pname","qty_per_unit","scrap_factor","effective_qty"]].copy()
                d3.columns=["Product","Qty/Unit","Scrap","Eff Qty"]
                st.dataframe(d3,use_container_width=True,hide_index=True)


# ══════════════════════════════════════════════════════════════
# VIEW 3 — PLANNING & FORECAST
# ══════════════════════════════════════════════════════════════
elif view=="Planning & Forecast":
    st.markdown('<div class="page-title">Planning & Forecast</div>',unsafe_allow_html=True)
    st.markdown('<div class="page-sub">ML-powered 90-day forward view — projected breaches, procurement plan, and budget</div>',unsafe_allow_html=True)

    if not fc_available:
        st.warning("⚠️ Run `python model.py` to enable Planning & Forecast. Demand Forecast model not found.")
        st.stop()

    fm   = ml_bundle["demand_forecast"]["models"]
    fs   = ml_bundle["demand_forecast"]["scalers"]
    flf  = ml_bundle["demand_forecast"].get("last_features", {})
    lt_m = ml_bundle["lead_time"].get("model")  if "lead_time" in ml_bundle else None
    lt_s = ml_bundle["lead_time"].get("scaler") if "lead_time" in ml_bundle else None
    lt_l = ml_bundle["lead_time"].get("le")     if "lead_time" in ml_bundle else None

    # Build dynamic snapshot — ML-driven ROP, SS, avg_daily, EOQ
    dyn_snapshot = cached_dynamic_snapshot(data, fm, fs, flf, lt_m, lt_s, lt_l)

    mat_options = dyn_snapshot["material_name"].tolist()
    mat_ids     = dyn_snapshot["material_id"].tolist()
    mats = data["materials"]

    # Get future projections for all 15 materials
    projections = get_future_projections(dyn_snapshot, monthly, fm, fs)

    tab1,tab3,tab4_fc=st.tabs(["Future Health View","Procurement Budget","Demand & Threshold Intelligence"])

    # ── TAB 1: FUTURE HEALTH VIEW ─────────────────────────────
    with tab1:
        st.markdown('<div class="section-title">🔮 90-Day Forward Inventory Health</div>',unsafe_allow_html=True)
        st.caption("Shows projected status of each material 90 days from today based on ML demand forecast. Same layout as Operational Dashboard but showing future state.")

        if not projections:
            st.info("No breach projections found for any material in next 90 days. All materials are safe.")
        else:
            # Build the full projection list first (incl. safe materials)
            proj_mids = {p["material_id"] for p in projections}
            safe_projs = []
            for _, mat in snapshot.iterrows():
                if mat["material_id"] not in proj_mids:
                    safe_projs.append({
                        "material_id":     mat["material_id"],
                        "material_name":   mat["material_name"],
                        "category":        mat["category"],
                        "current_stock":   int(mat["current_stock"]),
                        "reorder_point":   int(mat["reorder_point"]),
                        "safety_stock":    int(mat["safety_stock"]),
                        "eoq":             int(mat["eoq"]),
                        "avg_daily":       float(mat["avg_daily_consumption"]),
                        "predicted_lead_time": int(mat["predicted_lead_time"]),
                        "days_to_breach":  None,
                        "days_to_stockout":None,
                        "breach_date":     None,
                        "stockout_date":   None,
                        "order_by_date":   None,
                        "order_by_days":   None,
                        "stockout_risk":   "SAFE",
                        "preferred_supplier_id": mat["preferred_supplier_id"],
                        "unit_price":      mat["unit_price"],
                        "rop_is_dynamic":  bool(mat.get("rop_is_dynamic", fc_available)),
                    })
            all_projs = projections + safe_projs

            # ── Clickable risk KPI cards (same behaviour as dashboard) ─
            crit_c = len([p for p in all_projs if p["stockout_risk"]=="CRITICAL"])
            high_c = len([p for p in all_projs if p["stockout_risk"]=="HIGH"])
            med_c  = len([p for p in all_projs if p["stockout_risk"]=="MEDIUM"])
            low_c  = len([p for p in all_projs if p["stockout_risk"]=="LOW"])
            safe_c = len([p for p in all_projs if p["stockout_risk"]=="SAFE"])

            if "fkpi_filter" not in st.session_state: st.session_state.fkpi_filter = "ALL"

            def fkpi_click(code):
                st.session_state.fkpi_filter = "ALL" if st.session_state.fkpi_filter == code else code

            FKPI = [
                ("kpi_fcrit","CRITICAL",crit_c,"CRITICAL RISK",None),
                ("kpi_fhigh","HIGH",high_c,"HIGH RISK","red"),
                ("kpi_fmed","MEDIUM",med_c,"MEDIUM RISK","orange"),
                ("kpi_flow","LOW",low_c,"LOW RISK","blue"),
                ("kpi_fsafe","SAFE",safe_c,"SAFE","green"),
            ]
            kcols = st.columns(5)
            for col,(key,code,val,lbl,mcolor) in zip(kcols, FKPI):
                big = f":{mcolor}[**{val}**]" if mcolor else f"**{val}**"
                with col:
                    st.button(f"{big}  \n{lbl}", key=key, on_click=fkpi_click, args=(code,), width="stretch")
            active_f = [k for k,c,_,_,_ in FKPI if c == st.session_state.fkpi_filter]
            if active_f:
                st.markdown(f"<style>.st-key-{active_f[0]} button{{outline:2.5px solid #1B3A6B;outline-offset:1.5px;}}</style>",unsafe_allow_html=True)
            sel_risk = None if st.session_state.fkpi_filter == "ALL" else st.session_state.fkpi_filter
            st.markdown("<br>",unsafe_allow_html=True)

            # ── Future health grid (above the chart) ─────────────
            st.markdown('<div class="section-title">📋 Future Status Cards — Projected 90 Days</div>',unsafe_allow_html=True)
            show_projs = [p for p in all_projs if sel_risk is None or p["stockout_risk"] == sel_risk]
            if sel_risk:
                st.caption(f"Filter: {sel_risk.title()} risk — showing {len(show_projs)} of {len(all_projs)} materials. Click the highlighted card again to clear.")
            if not show_projs:
                st.info("No materials at this risk level.")
            cols_f = st.columns(5)
            for i, p in enumerate(show_projs):
                ac   = abc_map.get(p["material_id"],"C")
                bg   = RISK_BG.get(p["stockout_risk"],"#fff")
                bdr  = RISK_BORDER.get(p["stockout_risk"],"#E2E8F0")
                clr  = RISK_COLORS.get(p["stockout_risk"],"#64748B")
                txt  = "#FFFFFF" if p["stockout_risk"]=="CRITICAL" else "#0F172A"
                mc   = "#FFE4E4" if p["stockout_risk"]=="CRITICAL" else "#64748B"
                stock_clr = "#FFFFFF" if p["stockout_risk"]=="CRITICAL" else clr
                rh   = RISK_HTML.get(p["stockout_risk"],"")

                # ROP breach label — clarify already-below case
                if p["days_to_breach"] is None:
                    breach_str = "No breach in 90 days"
                elif p["days_to_breach"] <= 1:
                    breach_str = "Already below ROP now"
                else:
                    breach_str = f"In {p['days_to_breach']} days ({p['breach_date']})"

                # Stockout label
                if p["days_to_stockout"] is None:
                    stockout_str = "Safe in 90-day window"
                elif p["days_to_stockout"] <= 1:
                    stockout_str = "Already at zero"
                else:
                    stockout_str = f"In {p['days_to_stockout']} days ({p['stockout_date']})"

                order_str = p["order_by_date"] or "Not needed"

                # Only avg_daily needed for clean card
                avg_d = round(p["avg_daily"], 2)

                with cols_f[i%5]:
                    ac_html = abc_badge(ac)
                    rh_html = rh
                    st.markdown(
                        f'''<div class="mat-card" style="background:{bg};border-color:{bdr};">
                        <div class="mat-name" style="color:{txt};">{p["material_name"]} {ac_html}</div>
                        <div class="mat-cat" style="color:{mc};">{p["category"]}</div>
                        <div class="mat-stock" style="color:{stock_clr};">{p["current_stock"]} <span style="font-size:.75rem;">units now</span></div>
                        <div class="mat-meta" style="color:{mc};">Avg Forecast: {avg_d} units/day</div>
                        <div class="mat-meta" style="color:{mc};">ROP Breach: {breach_str}</div>
                        <div class="mat-meta" style="color:{mc};">Stockout: {stockout_str}</div>
                        <div class="mat-meta" style="color:{mc};">Order by: {order_str}</div>
                        {rh_html}
                        </div>''',
                        unsafe_allow_html=True
                    )

            # ── Days to breach bar chart (below the grid) ────────
            st.markdown('<div class="section-title" style="margin-top:1rem;">⏱️ Days Until ROP Breach</div>',unsafe_allow_html=True)
            st.markdown('<div class="threshold-note"><b>Reading:</b> Shorter bar = more urgent. Color = risk level. Materials with no bar are safe beyond 90 days.</div>',unsafe_allow_html=True)
            proj_list = [p for p in projections if sel_risk is None or p["stockout_risk"] == sel_risk]
            if not proj_list:
                st.info("No projected ROP breaches for this filter — these materials stay safe beyond 90 days.")
            else:
                proj_df = pd.DataFrame(proj_list)
                bar_colors_f = [RISK_COLORS.get(r,"#64748B") for r in proj_df["stockout_risk"]]
                proj_df["y_label"] = proj_df.apply(
                    lambda r: f"{r['material_name']}  [{abc_map.get(r['material_id'],'C')}]", axis=1
                )
                fig_fb = go.Figure(go.Bar(
                    x=proj_df["days_to_breach"],
                    y=proj_df["y_label"],
                    orientation="h",
                    marker_color=bar_colors_f,
                    text=[f"{d}d" for d in proj_df["days_to_breach"]],
                    textposition="outside",
                    hovertemplate="<b>%{y}</b><br>Breach in: %{x} days<extra></extra>",
                ))
                fig_fb.add_vline(x=15,line_dash="solid",line_color="#EF4444",line_width=2,
                    annotation_text="HIGH risk (15d)",annotation_font_color="#EF4444",annotation_position="top right",annotation_font_size=11)
                fig_fb.add_vline(x=30,line_dash="solid",line_color="#F59E0B",line_width=2,
                    annotation_text="MEDIUM risk (30d)",annotation_font_color="#92400E",annotation_position="top right",annotation_font_size=11)
                fig_fb.update_layout(height=max(300,110+len(proj_df)*32),paper_bgcolor="white",plot_bgcolor="#F8FAFC",
                    font=dict(family="Inter",size=12),margin=dict(l=10,r=90,t=30,b=20),
                    xaxis=dict(title="Days Until ROP Breach",gridcolor="#F1F5F9"),
                    yaxis=dict(gridcolor="#F1F5F9"))
                st.plotly_chart(fig_fb,use_container_width=True)

    # ── TAB 4: DEMAND & THRESHOLD INTELLIGENCE ──────────────
    with tab4_fc:
        st.markdown('<div class="page-title" style="font-size:1.2rem;">📈 Demand & Threshold Intelligence</div>',unsafe_allow_html=True)
        st.markdown('<div class="page-sub">ML-driven demand forecast + what it calculates — Safety Stock, ROP, EOQ, Lead Time per material</div>',unsafe_allow_html=True)

        fc_mat_sel = st.selectbox("Select Material", mat_options, key="fc_mat")
        fc_mat_id  = mat_ids[mat_options.index(fc_mat_sel)]
        snap_row   = dyn_snapshot[dyn_snapshot["material_id"] == fc_mat_id].iloc[0]

        # ── Historical monthly actuals ────────────────────────
        hist_m = monthly[monthly["material_id"] == fc_mat_id].copy()
        if "month_of_year" in hist_m.columns and "month" not in hist_m.columns:
            hist_m = hist_m.rename(columns={"month_of_year": "month"})
        # Drop rows where year or month is NaN — causes 1970 epoch bug
        hist_m = hist_m.dropna(subset=["year","month"]).copy()
        hist_m["year"]  = hist_m["year"].astype(int)
        hist_m["month"] = hist_m["month"].astype(int)
        hist_m = hist_m[hist_m.apply(
            lambda r: pd.Timestamp(year=r["year"], month=r["month"], day=1) >= cutoff,
            axis=1
        )].copy()

        # ── Forecast next 3 months ────────────────────────────
        fc3_vals = get_forecast(fc_mat_id, n=3)

        # Find last actual month to correctly label forecast months
        if len(hist_m) > 0:
            last_yr = int(hist_m["year"].iloc[-1])
            last_mo = int(hist_m["month"].iloc[-1])
        else:
            last_yr = today.year
            last_mo = today.month

        fc_months = []
        for i in range(1, 4):
            total_mo = last_mo + i
            yr = last_yr + (total_mo - 1) // 12
            mo = ((total_mo - 1) % 12) + 1
            fc_months.append({
                "label": f"{yr}-{mo:02d} (F)",
                "value": round(fc3_vals[i-1]) if fc3_vals and len(fc3_vals) >= i else 0,
                "year": yr, "month": mo
            })

        # ── Forecast values ────────────────────────────────────
        m1v_raw = fc3_vals[0] if fc3_vals and len(fc3_vals)>0 else 0
        m2v_raw = fc3_vals[1] if fc3_vals and len(fc3_vals)>1 else 0
        m3v_raw = fc3_vals[2] if fc3_vals and len(fc3_vals)>2 else 0
        avg_d_fc_3m = round((m1v_raw + m2v_raw + m3v_raw) / 3 / 30, 2) if fc3_vals else 0
        avg_d_fc_m1 = round(m1v_raw / 30, 2) if m1v_raw else 0

        # ── Historical bar chart — same pattern as Inventory Insights ─
        # Build labels purely as strings from year/month integers
        # No color zones — single navy for all historical bars
        hist_m = hist_m.dropna(subset=["year","month"]).copy()
        hist_m["year"]  = hist_m["year"].astype(int)
        hist_m["month"] = hist_m["month"].astype(int)

        xl_hist = [f"{r['year']}-{r['month']:02d}" for _,r in hist_m.iterrows()]
        yv_hist = [round(v) for v in hist_m["total_consumed"].tolist()]
        bc_hist = ["#1B3A6B"] * len(xl_hist)   # single navy — no zone coloring

        fig_fc = go.Figure(go.Bar(
            x=xl_hist, y=yv_hist,
            marker_color=bc_hist,
            text=yv_hist, textposition="outside",
            hovertemplate="<b>%{x}</b><br>Units: %{y:,}<extra></extra>",
        ))
        fig_fc.update_layout(
            height=320, paper_bgcolor="white", plot_bgcolor="#F8FAFC",
            xaxis=dict(title="Month", tickangle=-30, gridcolor="#F1F5F9",
                       type="category"),
            yaxis=dict(title="Units Consumed", gridcolor="#F1F5F9"),
            font=dict(family="Inter", size=12),
            margin=dict(l=10, r=10, t=10, b=60),
        )
        st.plotly_chart(fig_fc, use_container_width=True)
        st.caption("Historical monthly consumption")

        # ── Forecast month metrics ────────────────────────────
        fc_lbls = [f["label"].replace(" (F)","") for f in fc_months]
        fc_cols = st.columns(3)
        with fc_cols[0]:
            st.metric(
                f"{fc_lbls[0] if fc_lbls else 'M+1'} Forecast",
                f"{round(m1v_raw):,} units",
                help="Predicted units consumed next month (Model 4)"
            )
        with fc_cols[1]:
            st.metric(
                f"{fc_lbls[1] if len(fc_lbls)>1 else 'M+2'} Forecast",
                f"{round(m2v_raw):,} units",
                help="Predicted units consumed month after next (Model 4)"
            )
        with fc_cols[2]:
            st.metric(
                f"{fc_lbls[2] if len(fc_lbls)>2 else 'M+3'} Forecast",
                f"{round(m3v_raw):,} units",
                help="Predicted units consumed 3 months from now (Model 4)"
            )
        # Avg daily on next row
        ad_cols = st.columns(2)
        with ad_cols[0]:
            st.metric(
                "Next Month Avg Daily",
                f"{avg_d_fc_m1} units/day",
                help=f"M+1 forecast ÷ 30 = {m1v_raw:.0f} ÷ 30"
            )
        with ad_cols[1]:
            st.metric(
                "3-Month Avg Daily",
                f"{avg_d_fc_3m} units/day",
                help="(M1+M2+M3) ÷ 3 ÷ 30 — this value drives Dynamic ROP and Safety Stock"
            )

        st.markdown("<br>",unsafe_allow_html=True)

        # ── ML-derived threshold cards ──────────────────────

        pred_lt    = int(snap_row["predicted_lead_time"])
        nominal_lt = int(snap_row["supplier_lead_time"])
        dyn_ss     = int(snap_row["safety_stock"]) if snap_row["safety_stock"] is not None else None
        dyn_rop    = int(snap_row["reorder_point"]) if snap_row["reorder_point"] is not None else None
        dyn_eoq    = int(snap_row["eoq"]) if snap_row["eoq"] is not None else None
        curr_stock = int(snap_row["current_stock"])
        days_rem   = round(snap_row["days_stock_remaining"], 1) if snap_row["days_stock_remaining"] is not None else None

        # Static equivalents for comparison
        static_avg  = round(data["materials"][data["materials"]["material_id"]==fc_mat_id]["annual_demand"].values[0] / 365, 2)
        static_sig  = static_avg * 0.25
        static_ss   = round(1.65 * static_sig * math.sqrt(nominal_lt))
        static_rop  = round(static_avg * nominal_lt + static_ss)
        gap_rop     = (dyn_rop - static_rop) if dyn_rop is not None else None
        gap_col     = "#F59E0B" if gap_rop and gap_rop > 0 else "#22C55E" if gap_rop and gap_rop < 0 else "#94A3B8"
        gap_num     = f"+{gap_rop}" if gap_rop and gap_rop > 0 else str(gap_rop) if gap_rop else "N/A"
        gap_desc    = "ML orders earlier" if gap_rop and gap_rop > 0 else "ML gives more buffer" if gap_rop and gap_rop < 0 else "Same as static"

        danger = (days_rem is not None and days_rem < pred_lt)

        # Model outputs
        r1 = st.columns(4)
        lt_col = "#F59E0B" if pred_lt > nominal_lt else "#22C55E"
        with r1[0]:
            st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value" style="color:{lt_col};">{pred_lt}d</div>
            <div class="kpi-label">Predicted Lead Time (Model 1)<br>
            <span style="font-size:.68rem;color:#94A3B8;">Nominal: {nominal_lt}d &nbsp;|&nbsp; {"Late trend" if pred_lt>nominal_lt else "On-time trend"}</span>
            </div></div>""", unsafe_allow_html=True)
        with r1[1]:
            st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value" style="color:#7C3AED;">{dyn_ss}</div>
            <div class="kpi-label">Dynamic Safety Stock<br>
            <span style="font-size:.68rem;color:#94A3B8;">1.65 × (avg_daily × 0.25) × √{pred_lt} &nbsp;|&nbsp; Static was {static_ss}</span>
            </div></div>""", unsafe_allow_html=True)
        with r1[2]:
            st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value" style="color:#1B3A6B;">{dyn_rop}</div>
            <div class="kpi-label">Dynamic ROP<br>
            <span style="font-size:.68rem;color:#94A3B8;">{avg_d_fc_3m} × {pred_lt} + {dyn_ss} &nbsp;|&nbsp; Static was {static_rop}</span>
            </div></div>""", unsafe_allow_html=True)
        with r1[3]:
            st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value" style="color:#0D7C6E;">{dyn_eoq}</div>
            <div class="kpi-label">Dynamic EOQ<br>
            <span style="font-size:.68rem;color:#94A3B8;">√(2 × D_12m × S / H) — rolling actual demand</span>
            </div></div>""", unsafe_allow_html=True)

        st.markdown("<br>",unsafe_allow_html=True)

        # Current position vs ML thresholds
        r2 = st.columns(4)
        if dyn_ss is not None and dyn_rop is not None:
            stock_col = "#EF4444" if curr_stock <= dyn_ss else "#F59E0B" if curr_stock <= dyn_rop else "#22C55E"
            stock_lbl = "Below SS — Critical" if curr_stock<=dyn_ss else "Below ROP — Reorder" if curr_stock<=dyn_rop else "Above ROP — Normal"
        else:
            stock_col = "#94A3B8"
            stock_lbl = "Run model.py for thresholds"
        days_col  = "#EF4444" if danger else "#22C55E"
        with r2[0]:
            st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value" style="color:{stock_col};">{curr_stock}</div>
            <div class="kpi-label">Current Stock (units)<br>
            <span style="font-size:.68rem;color:#94A3B8;">{stock_lbl}</span>
            </div></div>""", unsafe_allow_html=True)
        with r2[1]:
            dr_disp = f"{days_rem}d" if days_rem is not None else "N/A"
            days_col2 = "#EF4444" if danger else "#F59E0B" if days_rem and days_rem < pred_lt*1.5 else "#22C55E"
            day_note = "⛔ Less than lead time!" if danger else "⚠️ Close to lead time" if days_rem and days_rem < pred_lt*1.5 else "✅ Covers lead time"
            st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value" style="color:{days_col2};">{dr_disp}</div>
            <div class="kpi-label">Days Remaining<br>
            <span style="font-size:.68rem;color:#94A3B8;">stock ÷ 3m avg daily &nbsp;|&nbsp; {day_note}</span>
            </div></div>""", unsafe_allow_html=True)
        with r2[2]:
            st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value" style="color:{gap_col};font-size:1.4rem;">{gap_num} units</div>
            <div class="kpi-label">Dynamic vs Static ROP<br>
            <span style="font-size:.7rem;color:{gap_col};font-weight:600;">{gap_desc}</span><br>
            <span style="font-size:.68rem;color:#94A3B8;">Dyn: {dyn_rop if dyn_rop else "N/A"} &nbsp;|&nbsp; Static: {static_rop}</span>
            </div></div>""", unsafe_allow_html=True)
        with r2[3]:
            if dyn_ss is not None and dyn_rop is not None:
                risk_row = "CRITICAL" if curr_stock<=dyn_ss else "REORDER" if curr_stock<=dyn_rop else "NORMAL"
            else:
                risk_row = "UNKNOWN"
            risk_c = STATUS_COLORS.get(risk_row,"#94A3B8")
            risk_bg = STATUS_BG.get(risk_row,"#F8FAFC")
            st.markdown(f"""<div class="kpi-card" style="background:{risk_bg};">
            <div class="kpi-value" style="color:{risk_c};">{risk_row}</div>
            <div class="kpi-label">Current Status (ML-driven)<br>
            <span style="font-size:.68rem;color:#94A3B8;">{"Vs Dynamic ROP & SS" if risk_row!="UNKNOWN" else "Run model.py"}</span>
            </div></div>""", unsafe_allow_html=True)

        # ── Model performance (Model 2: Demand Forecast) ──────
        fc_metrics = ml_bundle.get("demand_forecast", {}).get("metrics", {})
        m_perf     = fc_metrics.get(fc_mat_id)
        if m_perf:
            all_r2 = [v["r2"] for v in fc_metrics.values()]
            st.markdown('<div class="section-title" style="margin-top:.8rem;">🎯 Model Performance — Demand Forecast (Ridge Regression)</div>',unsafe_allow_html=True)
            r2v  = m_perf["r2"]
            qual, qcolor = ("Excellent","#16A34A") if r2v>=0.85 else (("Good","#0D7C6E") if r2v>=0.6 else ("Fair","#D97706"))
            mp = st.columns(4)
            perf_tiles = [
                (f"{r2v:.3f}", "R² — this material", "#0D7C6E"),
                (f"±{m_perf['mae']:.1f} units", "Avg Forecast Error (MAE)", "#0D7C6E"),
                (f"{sum(all_r2)/len(all_r2):.3f}", "Avg R² — all 15 materials", "#1B3A6B"),
                (qual, "Model Quality", qcolor),
            ]
            for col,(v,l,c) in zip(mp, perf_tiles):
                with col:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-value" style="font-size:1.3rem;color:{c};">{v}</div><div class="kpi-label">{l}</div></div>',unsafe_allow_html=True)
            st.caption(
                f"**How to read this:** R² = how much of the month-to-month demand pattern the model explains "
                f"(1.0 is perfect). The forecast for this material is typically within **±{m_perf['mae']:.1f} units** of the "
                f"actual monthly consumption. Validated with leave-one-out cross-validation — every month is predicted "
                f"by a model trained only on the other months, so the score is honest, not memorized."
            )

    # ── TAB 3: PROCUREMENT BUDGET ─────────────────────────────
    # Estimates how much money is needed for POs over the next 3 months,
    # based on the ML demand forecast per material.
    with tab3:
        st.markdown('<div class="section-title">Procurement Budget — Next 3 Months</div>',unsafe_allow_html=True)
        br=[]
        for _,m in mats.iterrows():
            mb=m["material_id"]
            sr=data["supplier_map"][(data["supplier_map"]["material_id"]==mb)&(data["supplier_map"]["preferred"]==True)]
            up=float(sr["unit_price"].values[0]) if len(sr)>0 else m["unit_cost"]
            fcb=get_forecast(mb,n=3)
            for i in range(3):
                fv=fcb[i] if fcb else m["annual_demand"]/12
                br.append({"Material":m["material_name"],"Category":m["category"],"Month":f"Month +{i+1}","Forecast (units)":round(fv),"Estimated Cost":round(fv*up)})
        bdf=pd.DataFrame(br)
        mt=bdf.groupby("Month")["Estimated Cost"].sum().reset_index()
        fig4=go.Figure(go.Bar(x=mt["Month"],y=mt["Estimated Cost"],marker_color=["#1B3A6B","#0D7C6E","#D97706"],text=[fmt_inr(v) for v in mt["Estimated Cost"]],textposition="outside"))
        fig4.update_layout(height=280,paper_bgcolor="white",plot_bgcolor="#F8FAFC",yaxis_title="Cost (₹)",font=dict(family="Inter",size=12),margin=dict(l=10,r=10,t=30,b=20))
        st.plotly_chart(fig4,use_container_width=True)
        cb=bdf.groupby(["Month","Category"])["Estimated Cost"].sum().reset_index()
        fig5=px.bar(cb,x="Month",y="Estimated Cost",color="Category",color_discrete_map=CAT_COLORS,barmode="stack",height=280,labels={"Estimated Cost":"Cost (₹)"})
        fig5.update_layout(paper_bgcolor="white",plot_bgcolor="#F8FAFC",font=dict(family="Inter",size=12),margin=dict(l=10,r=10,t=20,b=20))
        st.plotly_chart(fig5,use_container_width=True)
        mat_budget=bdf.groupby(["Material","Category"]).agg({"Forecast (units)":"sum","Estimated Cost":"sum"}).reset_index().sort_values("Estimated Cost",ascending=False)
        mat_budget["Estimated Cost"]=mat_budget["Estimated Cost"].apply(fmt_inr)
        def cat_row_style(row):
            bg=CAT_BG.get(row["Category"],""); clr=CAT_COLORS.get(row["Category"],"#374151")
            return [f"background-color:{bg};color:{clr}" if c=="Category" else "" for c in row.index]
        st.markdown('<div class="section-title" style="margin-top:.5rem;">Material Cost Breakdown (3-Month Total)</div>',unsafe_allow_html=True)
        st.dataframe(mat_budget.style.apply(cat_row_style,axis=1),use_container_width=True,hide_index=True)


# ══════════════════════════════════════════════════════════════
# VIEW 4 — PROCUREMENT PLAN
# Action page: for each material that needs ordering it scores the eligible
# suppliers (rating / price / lead time), recommends the best one and lets
# the user raise a planned PO directly.
# ══════════════════════════════════════════════════════════════
elif view == "Procurement Plan":
    st.markdown('<div class="page-title">Procurement Plan</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Immediate reorder alerts and future breach recommendations</div>', unsafe_allow_html=True)

    if not fc_available:
        st.error("🔴 ML models not loaded. Run `python model.py` first.")
        st.markdown("""
        <div style="background:#FEF2F2;border:1.5px solid #EF4444;border-radius:10px;padding:1.2rem 1.4rem;margin-top:1rem;">
        <div style="font-size:.95rem;font-weight:700;color:#991B1B;margin-bottom:.5rem;">Procurement Plan requires ML models</div>
        <div style="font-size:.82rem;color:#7F1D1D;line-height:1.7;">
        Without ML models, ROP and Safety Stock cannot be calculated accurately.<br>
        Static fallback values are not shown here to avoid misleading decisions.<br><br>
        <b>To enable this view:</b><br>
        1. Open terminal in your project folder<br>
        2. Run: <code style="background:#FEE2E2;padding:2px 6px;border-radius:4px;">python model.py</code><br>
        3. Refresh this page
        </div>
        </div>""", unsafe_allow_html=True)
        st.stop()

    # ── IMMEDIATE ALERTS ──────────────────────────────────────
    # Build dynamic snapshot for procurement plan
    if fc_available:
        _fm2  = ml_bundle["demand_forecast"]["models"]
        _fs2  = ml_bundle["demand_forecast"]["scalers"]
        _flf2 = ml_bundle["demand_forecast"].get("last_features", {})
        _lm2  = ml_bundle["lead_time"].get("model")  if "lead_time" in ml_bundle else None
        _ls2  = ml_bundle["lead_time"].get("scaler") if "lead_time" in ml_bundle else None
        _ll2  = ml_bundle["lead_time"].get("le")     if "lead_time" in ml_bundle else None
        proc_snapshot = cached_dynamic_snapshot(data, _fm2, _fs2, _flf2, _lm2, _ls2, _ll2)
    else:
        proc_snapshot = snapshot

    current_alerts = get_alerts(proc_snapshot, data)
    hidden_imm2    = st.session_state.get("hidden_imm", set())
    visible_alerts = [a for a in current_alerts if a["material_id"] not in hidden_imm2]
    rop_note       = "" if fc_available else " &nbsp;<span style='font-size:.72rem;color:#92400E;'>(Static ROP)</span>"

    if visible_alerts:
        st.markdown(f'<div class="section-title">🚨 Immediate — {len(visible_alerts)} material(s) already below Reorder Point</div>', unsafe_allow_html=True)
        for a in visible_alerts:
            ac = abc_map.get(a["material_id"], "C")
            st.markdown('<div class="alert-card">', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2.5, 2.5, 1])
            with c1:
                st.markdown(f'**{a["material_name"]}** {badge_html(a["status"])} {abc_badge(ac)}', unsafe_allow_html=True)
                st.markdown(f'Stock: **{a["current_stock"]}** &nbsp;|&nbsp; ROP: **{a["reorder_point"]}**{rop_note} &nbsp;|&nbsp; Days: **{a["days_remaining"]}**', unsafe_allow_html=True)
            with c2:
                st.markdown(f'**Supplier:** {a["recommended_supplier_name"]}')
                st.markdown(f'Order **{a["order_quantity"]} units** at {fmt_inr(a["recommended_unit_price"])}/unit')
                st.markdown(f'**Total: {fmt_inr(a["total_order_cost"])}** &nbsp;|&nbsp; Delivery: {a["expected_delivery_date"]}')
                gap = a["delivery_gap_days"]
                if gap > 7: st.markdown(f'<span class="gap-crit">⛔ {gap:.1f}-day gap</span>', unsafe_allow_html=True)
                elif gap > 0: st.markdown(f'<span class="gap-warn">⚠️ {gap:.1f}-day gap</span>', unsafe_allow_html=True)
            with c3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("✅ Approve PO", key=f"app2_{a['material_id']}", type="primary", use_container_width=True):
                    po_id, dd = approve_po(a)
                    st.success(f"PO {po_id} raised. Delivery: {dd}")
                    clear_cache(); st.rerun()
                if st.button("🚫 Hide Today", key=f"hide2_imm_{a['material_id']}", use_container_width=True):
                    if "hidden_imm" not in st.session_state:
                        st.session_state["hidden_imm"] = set()
                    st.session_state["hidden_imm"].add(a["material_id"])
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.success("✅ No materials currently below reorder point.")

    st.markdown("---")

    # ── FUTURE BREACH RECOMMENDATIONS ────────────────────────
    if fc_available:
        fm2 = ml_bundle["demand_forecast"]["models"]
        fs2 = ml_bundle["demand_forecast"]["scalers"]
        projections2 = get_future_projections(proc_snapshot, monthly, fm2, fs2)

        planned_mids2 = set(
            data["purchase_orders"][
                data["purchase_orders"]["po_status"] == "Planned"
            ]["material_id"].tolist()
        )
        hidden_today2 = st.session_state.get("hidden_today", set())
        actionable2 = [
            p for p in projections2
            if p["stockout_risk"] in ["CRITICAL","HIGH","MEDIUM","LOW"]
            and p["material_id"] not in planned_mids2
            and (
                p["stockout_risk"] == "CRITICAL"
                or p["material_id"] not in hidden_today2
            )
        ]

        if actionable2:
            plan_act2 = [p for p in actionable2 if p["stockout_risk"] in ["LOW","MEDIUM"]]
            if plan_act2:
                if st.button(f"🚀 Raise All Planned POs — {len(plan_act2)} materials", type="primary", use_container_width=True):
                    raised = []
                    for p in plan_act2:
                        res = raise_planned_po(p, data["suppliers"], data["supplier_map"])
                        raised.append(f"{p['material_name']} → {res['po_id']}")
                    st.success("✅ Raised:\n" + "\n".join(raised))
                    clear_cache(); st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

            st.markdown('<div class="section-title">📋 Future Procurement Recommendations</div>', unsafe_allow_html=True)
            pm_names = {"PRD001":"Family Sedan Kit","PRD002":"SUV Drive Kit","PRD003":"Hatchback Brake Kit"}
            for i2, p in enumerate(actionable2):
                ac  = abc_map.get(p["material_id"], "C")
                rh  = RISK_HTML.get(p["stockout_risk"], "")
                bom_rows = data["bom"][data["bom"]["material_id"] == p["material_id"]]
                affected = " | ".join([pm_names.get(r["product_id"], r["product_id"]) for _, r in bom_rows.iterrows()])

                eligible = data["supplier_map"][data["supplier_map"]["material_id"] == p["material_id"]].copy()
                eligible = eligible.merge(data["suppliers"][["supplier_id","supplier_rating"]], on="supplier_id", how="left")
                eligible = eligible[eligible["supplier_rating"] >= 0.60]
                if len(eligible) == 0:
                    eligible = data["supplier_map"][data["supplier_map"]["material_id"] == p["material_id"]].copy()
                    eligible = eligible.merge(data["suppliers"][["supplier_id","supplier_rating"]], on="supplier_id", how="left")
                max_price = eligible["unit_price"].max()
                max_lt    = eligible["lead_time_days"].max()
                days_left = p["days_to_breach"] or 90
                if days_left < 15:
                    eligible["score"] = 0.4*eligible["supplier_rating"] + 0.1*(1-eligible["unit_price"]/max_price) + 0.5*(1-eligible["lead_time_days"]/max_lt)
                    reason = "Fastest supplier — breach window critical"
                elif days_left < 30:
                    eligible["score"] = 0.4*eligible["supplier_rating"] + 0.2*(1-eligible["unit_price"]/max_price) + 0.4*(1-eligible["lead_time_days"]/max_lt)
                    reason = "Balanced speed and cost"
                else:
                    eligible["score"] = 0.4*eligible["supplier_rating"] + 0.4*(1-eligible["unit_price"]/max_price) + 0.2*(1-eligible["lead_time_days"]/max_lt)
                    reason = "Most cost-effective supplier"

                best_b   = eligible.sort_values("score", ascending=False).iloc[0]
                sname    = data["suppliers"][data["suppliers"]["supplier_id"] == best_b["supplier_id"]]["supplier_name"].values
                sname    = sname[0] if len(sname) > 0 else best_b["supplier_id"]
                unit_p   = float(best_b["unit_price"])
                dyn_cost = p["eoq"] * unit_p

                if p["days_to_breach"] is None:
                    b_lbl = "No breach in 90 days"
                elif p["days_to_breach"] <= 1:
                    b_lbl = "Already below ROP"
                else:
                    b_lbl = f"{p['days_to_breach']} days ({p['breach_date']})"

                so_lbl = (f"{p['days_to_stockout']} days ({p['stockout_date']})"
                           if p["days_to_stockout"] else "Safe in 90-day window")

                is_dyn  = p.get("rop_is_dynamic", fc_available)
                rop_lbl = "Dynamic ROP" if is_dyn else "Static ROP"
                ss_lbl  = "Dynamic SS"  if is_dyn else "Static SS"

                st.markdown('<div class="plan-card">', unsafe_allow_html=True)
                c1, c2, c3 = st.columns([2.5, 3, 1.5])
                with c1:
                    st.markdown(f'**{p["material_name"]}** {abc_badge(ac)} {rh}', unsafe_allow_html=True)
                    st.markdown(f'Current Stock: **{p["current_stock"]}** &nbsp;|&nbsp; {rop_lbl}: **{p["reorder_point"]}** &nbsp;|&nbsp; {ss_lbl}: **{p["safety_stock"]}**')
                    st.markdown(f'📅 ROP Breach: **{b_lbl}**')
                    st.markdown(f'☠️ Stockout: **{so_lbl}**')
                    st.markdown(f'🗓️ Order by: **{p["order_by_date"] or "Now"}**')
                    if affected: st.markdown(f'⚙️ Production affected: **{affected}**')
                with c2:
                    st.markdown(f'🏭 **Supplier:** {sname}')
                    st.markdown(f'*{reason}*')
                    st.markdown(f'Order Qty (Dynamic EOQ): **{p["eoq"]} units** &nbsp;|&nbsp; Lead time: **{int(best_b["lead_time_days"])} days**')
                    st.markdown(f'Total Order Cost: **{fmt_inr(dyn_cost)}**')
                    if p["days_to_breach"] and p["days_to_breach"] < p["predicted_lead_time"]:
                        st.markdown(f'<span class="gap-crit">⛔ Lead time ({p["predicted_lead_time"]}d) exceeds ROP breach ({p["days_to_breach"]}d) — order immediately</span>', unsafe_allow_html=True)
                with c3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("📋 Raise Planned PO", key=f"pp2_{i2}_{p['material_id']}", type="primary", use_container_width=True):
                        res = raise_planned_po(p, data["suppliers"], data["supplier_map"])
                        st.success(f"✅ {res['po_id']} raised — {res['supplier_name']} — {res['quantity']} units — {fmt_inr(res['total_cost'])}")
                        clear_cache(); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.success("✅ No future breaches detected in next 90 days.")
    else:
        st.warning("⚠️ Run `python model.py` to see future breach recommendations.")

# ══════════════════════════════════════════════════════════════
# VIEW 5 — AI COPILOT (Groq LLM + tools over app.py analytics)
# ══════════════════════════════════════════════════════════════
elif view == "AI Copilot":
    from agents.llm import groq_ready

    st.markdown('<div class="page-title">🤖 AI Copilot</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Ask anything about inventory, suppliers, forecasts and purchase orders</div>', unsafe_allow_html=True)

    if not groq_ready():
        st.warning("⚠️ **GROQ_API_KEY not set** — the copilot needs a (free) Groq API key to run.")
        st.markdown(
            "1. Create a free key at [console.groq.com](https://console.groq.com/keys)\n"
            "2. Add this line to the `.env` file in the project root:"
        )
        st.code("GROQ_API_KEY=gsk_your_key_here", language="bash")
        st.markdown("3. Restart the app — this page becomes a chat.")
    else:
        from agents.chat import to_lc_history
        from agents.graph import ask_copilot

        if "copilot_msgs" not in st.session_state:
            st.session_state.copilot_msgs = []   # {"role","text","tools"}

        # Starter questions shown only on an empty chat
        if not st.session_state.copilot_msgs:
            SUGGESTIONS = [
                "Which materials need reordering?",
                "What is at risk of stockout this month?",
                "Which supplier is most reliable?",
                "What are the PO approval limits?",
            ]
            sug_cols = st.columns(len(SUGGESTIONS))
            for col, s in zip(sug_cols, SUGGESTIONS):
                with col:
                    if st.button(s, key=f"sug_{s[:12]}", use_container_width=True):
                        st.session_state.copilot_prefill = s

        def _meta_caption(agent, tools):
            parts = []
            if agent:
                parts.append(f"🧭 {agent} agent")
            if tools:
                parts.append("🔧 " + " · ".join(tools))
            return " — ".join(parts)

        def _stream_words(text, delay=0.015):
            # typewriter effect for st.write_stream — yields word by word
            import time as _time
            for word in text.split(" "):
                yield word + " "
                _time.sleep(delay)

        for m in st.session_state.copilot_msgs:
            with st.chat_message(m["role"]):
                meta = _meta_caption(m.get("agent"), m.get("tools"))
                if meta:
                    st.caption(meta)
                st.markdown(m["text"])

        typed    = st.chat_input("Ask about inventory, suppliers, forecasts…")
        question = typed or st.session_state.pop("copilot_prefill", None)

        if question:
            st.session_state.copilot_msgs.append({"role": "user", "text": question})
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                with st.spinner("Routing to the right agent…"):
                    try:
                        prior = [(m["role"], m["text"]) for m in st.session_state.copilot_msgs[:-1]]
                        res   = ask_copilot(question, to_lc_history(prior))
                    except Exception as e:
                        res = {"answer": f"⚠️ Copilot error: {e}", "agent": None, "tools_used": []}
                meta = _meta_caption(res.get("agent"), res["tools_used"])
                if meta:
                    st.caption(meta)
                st.write_stream(_stream_words(res["answer"]))
            st.session_state.copilot_msgs.append(
                {"role": "assistant", "text": res["answer"],
                 "agent": res.get("agent"), "tools": res["tools_used"]}
            )
