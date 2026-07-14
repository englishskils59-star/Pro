# app.py
# WDI Visit Analytics Engine — v2.0
# Persistent Storage + Override System + 6 Pages

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import io

from utils import (
    load_excel, validate_columns, clean_dataframe,
    basic_stats, fmt_number, fmt_pct, STATUS_COLORS, REQUIRED_COLUMNS,
    deduplicate_customer_names,
)
from classification_engine import (
    classify_dataframe, build_customer_journey,
    customers_not_visited, get_rules_dataframe,
    final_status_per_customer, set_custom_rules,
)
from dashboard import (
    customer_analytics_summary, sales_rep_kpi, executive_dashboard_data,
)
from export_manager import (
    export_customer_summary, export_sales_rep_kpi,
    export_executive_dashboard, export_classification_results,
    export_followup_customers, export_monthly_report,
)
from insights import (
    extract_promises, next_best_visits, competitor_mentions,
    weekday_productivity, note_quality, data_quality_summary,
    engine_agreement, unclassified_phrases, period_comparison,
    coverage_map, conversion_retention,
)
from storage_manager import (
    load_config, save_config, set_data_dir, get_data_dir,
    has_saved_data, get_saved_metadata, load_session, save_session,
    export_unclassified, import_overrides, clear_overrides, clear_all_data,
    storage_status, VALID_STATUSES, apply_saved_overrides, apply_name_merges,
    load_custom_rules, save_custom_rules, load_name_merges, save_name_merges,
)

# ═══════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="WDI Visit Analytics Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═══════════════════════════════════════════════════════════════════

from pathlib import Path as _Path

_FONT_CSS = ""
try:
    _FONT_CSS = (_Path(__file__).parent / "static" / "fonts" / "ibmplex.css").read_text(encoding="utf-8")
except Exception:
    pass  # fonts missing → falls back to Segoe UI

st.markdown(f"""
<style>
{_FONT_CSS}
:root {{
    --bg:#0F1417; --side:#0A0E11; --card:#161D24; --card2:#10171D;
    --border:#1D262F; --border2:#2A3540;
    --text:#E6EDF3; --muted:#8B98A5; --faint:#566573;
    --teal:#2DD4BF; --blue:#4C9AFF; --red:#F08080; --amber:#FFC000;
}}
html,body,[class*="css"],.stApp{{font-family:'IBM Plex Sans Arabic','Segoe UI',sans-serif!important;}}
.stApp,[data-testid="stAppViewContainer"]{{background:var(--bg)!important;color:var(--text)!important;}}
[data-testid="stHeader"]{{background:rgba(15,20,23,.85)!important;}}
.main .block-container{{direction:rtl;padding-top:2.2rem;max-width:1500px;}}
::-webkit-scrollbar{{width:10px;height:10px;}}
::-webkit-scrollbar-thumb{{background:var(--border2);border-radius:6px;}}
::-webkit-scrollbar-track{{background:transparent;}}

/* ── Sidebar ── */
[data-testid="stSidebar"]{{background:var(--side)!important;border-left:none;border-right:1px solid var(--border)!important;direction:rtl;}}
[data-testid="stSidebar"] *{{color:var(--text);}}
[data-testid="stSidebar"] [role="radiogroup"] label{{padding:7px 12px!important;border-radius:7px;margin:1px 0;transition:background .12s;width:100%;}}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{{background:#141C23;}}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){{background:var(--card2);}}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{{color:var(--teal)!important;font-weight:700;}}
[data-testid="stSidebar"] [role="radiogroup"] label p{{font-size:13px!important;color:var(--text);}}
[data-testid="stSidebar"] hr{{border-color:var(--border)!important;margin:12px 0!important;}}

/* ── Headings / text ── */
h1,h2,h3{{color:var(--text)!important;}}
hr{{border-color:var(--border)!important;margin:16px 0!important;}}
.page-head{{display:flex;align-items:center;gap:14px;margin:2px 0 20px;}}
.page-bar{{width:4px;height:38px;border-radius:2px;flex-shrink:0;}}
.page-head h1{{margin:0!important;font-size:22px!important;font-weight:700!important;}}
.page-en{{font-size:10.5px;letter-spacing:2px;color:var(--faint);margin-top:2px;}}
.sec-title{{font-size:14px;font-weight:700;color:var(--text);margin:24px 0 10px;}}
.sec-en{{font-weight:400;color:var(--faint);font-size:10.5px;letter-spacing:1px;}}

/* ── KPI cards ── */
.kpi-grid{{display:grid;gap:10px;margin:6px 0 14px;}}
.kpi-card{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:13px 14px;}}
.kpi-top{{display:flex;align-items:center;gap:6px;}}
.kpi-dot{{width:8px;height:8px;border-radius:2px;display:inline-block;flex-shrink:0;}}
.kpi-label{{font-size:10.5px;color:var(--muted);}}
.kpi-value{{font-size:24px;font-weight:700;color:var(--text);margin-top:6px;line-height:1.1;}}
[data-testid="stMetric"]{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:13px 16px!important;}}
[data-testid="stMetric"] [data-testid="stMetricLabel"] p{{font-size:11px!important;color:var(--muted)!important;}}
[data-testid="stMetric"] [data-testid="stMetricValue"]{{font-size:23px!important;color:var(--text)!important;font-weight:700!important;}}

/* ── Cards / tables ── */
.section-card{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px 18px;margin-bottom:16px;color:var(--muted);}}
.wdi-tablewrap{{overflow:auto;border:1px solid var(--border);border-radius:8px;margin-bottom:8px;}}
.wdi-table{{width:100%;border-collapse:collapse;font-size:12px;direction:rtl;}}
.wdi-table th{{position:sticky;top:0;background:var(--card2);color:var(--muted);padding:9px 13px;text-align:right;font-weight:600;border-bottom:1px solid var(--border2);white-space:nowrap;z-index:1;}}
.wdi-table td{{padding:8px 13px;color:#C6D0DA;border-bottom:1px solid #1A222B;}}
.wdi-badge{{border-radius:5px;padding:2px 9px;font-size:10.5px;font-weight:600;white-space:nowrap;display:inline-block;border:1px solid transparent;}}
.wdi-chip{{background:var(--card2);border:1px solid var(--border2);border-radius:20px;padding:5px 13px;font-size:11.5px;color:#C6D0DA;display:inline-block;margin:3px 2px;}}
.wdi-chip b{{color:var(--teal);}}

/* ── Buttons ── */
.stButton>button{{background:transparent!important;color:var(--text)!important;border:1px solid var(--border2)!important;border-radius:7px!important;font-weight:600!important;font-family:inherit!important;}}
.stButton>button:hover{{border-color:var(--teal)!important;color:var(--teal)!important;}}
.stDownloadButton>button{{background:transparent!important;color:var(--teal)!important;border:1px solid rgba(45,212,191,.4)!important;border-radius:7px!important;font-weight:600!important;}}
.stDownloadButton>button:hover{{background:rgba(45,212,191,.1)!important;}}

/* ── Widgets ── */
[data-testid="stExpander"]{{border:1px solid var(--border)!important;border-radius:9px!important;background:var(--card);}}
[data-testid="stFileUploader"] section{{border:2px dashed rgba(45,212,191,.4)!important;border-radius:12px!important;background:rgba(45,212,191,.04)!important;}}
[data-baseweb="tab-list"]{{border-bottom:1px solid var(--border)!important;gap:4px;}}
[data-baseweb="tab"]{{color:var(--muted)!important;font-weight:600!important;}}
[data-baseweb="tab"][aria-selected="true"]{{color:var(--teal)!important;}}
[data-baseweb="tab-highlight"]{{background-color:var(--teal)!important;}}
[data-testid="stDataFrame"]{{border:1px solid var(--border);border-radius:8px;}}
input[type="date"],select{{color-scheme:dark;}}
[data-testid="stAlert"]{{border-radius:9px;}}
code{{color:var(--teal)!important;}}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════

def _init_state():
    defaults = {
        "raw_df": None, "clean_df": None, "classified_df": None,
        "journey_df": None, "rep_kpi_df": None, "exec_data": None,
        "analytics_data": None, "rep_figures": None,
        "file_name": "", "processing_done": False,
        "storage_loaded": False,
        "date_range": None, "_view_cache": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# Load user-defined keyword rules (from the shared data folder)
# before any classification happens
set_custom_rules(load_custom_rules())


# ═══════════════════════════════════════════════════════════════════
# SHARED UI HELPERS
# ═══════════════════════════════════════════════════════════════════

import html as _html

# Per-page accent colors (from the approved design)
PAGE_ACCENT = {
    "upload": "#FFC000", "classify": "#FFC000", "analytics": "#4C9AFF",
    "reps": "#70AD47", "exec": "#2DD4BF", "action": "#F08080",
    "comp": "#C00000", "c360": "#4C9AFF", "quality": "#8B98A5", "settings": "#8B98A5",
}

# Status badge palette: (background, border, text) tuned for the dark theme
STATUS_BADGE = {
    "Current Customer":   ("rgba(112,173,71,.13)",  "rgba(112,173,71,.4)",  "#9CD07E"),
    "Potential Customer": ("rgba(76,154,255,.13)",  "rgba(76,154,255,.4)",  "#7FB3E8"),
    "Target Customer":    ("rgba(255,192,0,.12)",   "rgba(255,192,0,.4)",   "#FFC000"),
    "New Customer":       ("rgba(31,78,121,.4)",    "rgba(76,154,255,.35)", "#9CC4F5"),
    "Former Customer":    ("rgba(169,169,169,.12)", "rgba(169,169,169,.35)","#C0C7CE"),
    "Not Interested":     ("rgba(240,90,90,.12)",   "rgba(240,90,90,.4)",   "#F08080"),
    "No Meeting":         ("rgba(132,151,176,.12)", "rgba(132,151,176,.4)", "#A9B7C6"),
    "Unclassified":       ("rgba(217,217,217,.1)",  "rgba(217,217,217,.3)", "#B8C0C8"),
}

STATUS_AR = {
    "Current Customer": "عميل حالي", "Potential Customer": "محتمل",
    "Target Customer": "مستهدف", "New Customer": "جديد",
    "Former Customer": "سابق", "Not Interested": "غير مهتم",
    "No Meeting": "لم تتم المقابلة", "Unclassified": "غير مصنف",
}

# Arabic display names for DataFrame columns in custom tables
COL_AR = {
    "Customer Name": "العميل", "Sales Rep Name": "المندوب", "Governorate": "المحافظة",
    "District": "المنطقة", "Visit Count": "الزيارات", "Latest Status": "الحالة",
    "Display Status": "الحالة", "Days Since Last Visit": "منذ (يوم)",
    "Last Visit Date": "آخر زيارة", "First Visit Date": "أول زيارة",
    "Visit Date": "التاريخ", "Visit Notes": "الملاحظة", "Confidence Score": "الثقة",
    "Latest Confidence": "الثقة", "Transition Date": "تاريخ التحوّل",
    "Days To Convert": "أيام التحويل", "From Status": "من", "To Status": "إلى",
    "Override Source": "المصدر", "Matched Keywords": "الكلمات المطابقة",
}


def badge(status: str) -> str:
    bg, border, color = STATUS_BADGE.get(str(status), STATUS_BADGE["Unclassified"])
    label = STATUS_AR.get(str(status), str(status))
    return (f'<span class="wdi-badge" style="background:{bg};border-color:{border};'
            f'color:{color}">{_html.escape(label)}</span>')


def html_table(df: pd.DataFrame, badge_cols=(), color_cols=None, height: int = 360,
               index_col: bool = False, cond_colors=None):
    """Design-styled scrollable table with status badges and colored columns.
    cond_colors: {col: callable(value) -> css color} for per-value coloring."""
    if df is None or df.empty:
        st.info("لا توجد بيانات")
        return
    color_cols = color_cols or {}
    cond_colors = cond_colors or {}
    show = df.copy()
    for col in show.columns:
        if pd.api.types.is_datetime64_any_dtype(show[col]):
            show[col] = show[col].dt.strftime("%Y-%m-%d")

    ths = ""
    if index_col:
        ths += "<th>#</th>"
    ths += "".join(f"<th>{_html.escape(str(COL_AR.get(c, c)))}</th>" for c in show.columns)

    rows = []
    for n, (_, r) in enumerate(show.iterrows(), start=1):
        tds = f'<td style="color:#566573">{n}</td>' if index_col else ""
        for c in show.columns:
            v = r[c]
            v = "" if (v is None or (isinstance(v, float) and pd.isna(v)) or str(v) == "NaT") else v
            if c in badge_cols:
                tds += f"<td>{badge(v)}</td>"
            elif c in cond_colors:
                try:
                    _cc = cond_colors[c](v)
                except Exception:
                    _cc = "#C6D0DA"
                tds += (f'<td style="color:{_cc};font-weight:700">'
                        f'{_html.escape(str(v))}</td>')
            elif c in color_cols:
                tds += (f'<td style="color:{color_cols[c]};font-weight:700">'
                        f'{_html.escape(str(v))}</td>')
            else:
                tds += f"<td>{_html.escape(str(v))}</td>"
        rows.append(f"<tr>{tds}</tr>")

    st.markdown(
        f'<div class="wdi-tablewrap" style="max-height:{height}px">'
        f'<table class="wdi-table"><thead><tr>{ths}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True)


def matrix_table(df: pd.DataFrame, index_label: str = "", height: int = 320):
    """Design-styled matrix: zeros rendered as dim dots, values bold."""
    if df is None or df.empty:
        st.info("لا توجد بيانات")
        return
    ths = f"<th>{_html.escape(index_label)}</th>" + "".join(
        f'<th style="text-align:center">{_html.escape(STATUS_AR.get(str(c), str(c)))}</th>'
        for c in df.columns)
    rows = []
    for idx, r in df.iterrows():
        tds = (f'<td style="font-weight:600;color:#E6EDF3;white-space:nowrap">'
               f'{_html.escape(STATUS_AR.get(str(idx), str(idx)))}</td>')
        for c in df.columns:
            v = r[c]
            try:
                n = int(v)
            except (ValueError, TypeError):
                n = 0
            if n:
                tds += f'<td style="text-align:center;color:#E6EDF3;font-weight:700">{n}</td>'
            else:
                tds += '<td style="text-align:center;color:#2A3540">·</td>'
        rows.append(f"<tr>{tds}</tr>")
    st.markdown(
        f'<div class="wdi-tablewrap" style="max-height:{height}px">'
        f'<table class="wdi-table"><thead><tr>{ths}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True)


def stat_cards(items: list, cols: int = 4):
    """
    Design KPI cards. Each item: dict with
      label, value — required
      en (small EN caption), accent (dot color), color (value color), delta (text, color)
    """
    cards = ""
    for it in items:
        top = f'<span class="kpi-label">{_html.escape(str(it["label"]))}</span>'
        if it.get("accent"):
            top = f'<span class="kpi-dot" style="background:{it["accent"]}"></span>' + top
        vcolor = it.get("color", "#E6EDF3")
        card = (f'<div class="kpi-card"><div class="kpi-top">{top}</div>'
                f'<div class="kpi-value" style="color:{vcolor}">{_html.escape(str(it["value"]))}</div>')
        if it.get("delta"):
            dt, dc = it["delta"]
            card += f'<div style="font-size:10.5px;font-weight:600;color:{dc};margin-top:1px">{_html.escape(str(dt))}</div>'
        if it.get("en"):
            card += f'<div style="font-size:8.5px;color:#566573;letter-spacing:.8px;margin-top:3px">{_html.escape(str(it["en"]))}</div>'
        card += "</div>"
        cards += card
    st.markdown(
        f'<div class="kpi-grid" style="grid-template-columns:repeat({cols},1fr)">{cards}</div>',
        unsafe_allow_html=True)


def page_banner(title, en_subtitle="", accent="#2DD4BF", right_html=""):
    right = (f'<div style="text-align:left;font-size:11.5px;color:#8B98A5;line-height:1.8;'
             f'background:#10171D;border:1px solid #1D262F;border-radius:8px;padding:8px 14px">'
             f'{right_html}</div>') if right_html else ""
    st.markdown(f"""
    <div class="page-head" style="justify-content:space-between">
        <div style="display:flex;align-items:center;gap:14px">
            <div class="page-bar" style="background:{accent}"></div>
            <div><h1>{title}</h1><div class="page-en">{en_subtitle}</div></div>
        </div>
        {right}
    </div>""", unsafe_allow_html=True)


_KPI_ACCENTS = ["#2DD4BF", "#4C9AFF", "#70AD47", "#FFC000", "#F08080", "#A78BFA", "#8B98A5", "#2DD4BF", "#4C9AFF"]


def kpi_row(metrics: dict, cols_per_row: int = 4):
    items = list(metrics.items())
    cards = ""
    for i, (label, value) in enumerate(items):
        val = fmt_number(value) if isinstance(value, (int, np.integer)) else _html.escape(str(value))
        accent = _KPI_ACCENTS[i % len(_KPI_ACCENTS)]
        cards += (f'<div class="kpi-card"><div class="kpi-top">'
                  f'<span class="kpi-dot" style="background:{accent}"></span>'
                  f'<span class="kpi-label">{_html.escape(str(label))}</span></div>'
                  f'<div class="kpi-value">{val}</div></div>')
    ncols = min(len(items), cols_per_row)
    st.markdown(f'<div class="kpi-grid" style="grid-template-columns:repeat({ncols},1fr)">{cards}</div>',
                unsafe_allow_html=True)


def no_data_warning():
    st.warning("⚠️ لا توجد بيانات. يرجى رفع ملف Excel من صفحة **مركز الرفع** أو تحميل البيانات المحفوظة.", icon="📂")


def section(title, en=""):
    en_html = f' <span class="sec-en">{en}</span>' if en else ""
    st.markdown(f'<div class="sec-title">{title}{en_html}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PIPELINE
# ═══════════════════════════════════════════════════════════════════

def rebuild_dashboards():
    """Rebuild analytics/exec data from classified_df + journey_df."""
    classified = st.session_state["classified_df"]
    journey    = st.session_state["journey_df"]
    with st.spinner("📊 تحديث التحليلات..."):
        rep_kpi, rep_figs = sales_rep_kpi(classified, journey)
        st.session_state["rep_kpi_df"]  = rep_kpi
        st.session_state["rep_figures"] = rep_figs
        st.session_state["analytics_data"] = customer_analytics_summary(classified, journey)
        st.session_state["exec_data"]      = executive_dashboard_data(classified, journey, rep_kpi)
    st.session_state["_view_cache"] = None  # invalidate the date-filter cache


def get_view() -> dict:
    """
    All dashboards computed on the active date range (sidebar filter).
    Cached per range so switching pages doesn't recompute.
    Full data (no filter) reuses the master session objects.
    """
    rng = st.session_state.get("date_range")  # None or (Timestamp, Timestamp)
    cache = st.session_state.get("_view_cache")
    if cache is not None and cache.get("rng") == rng:
        return cache

    master = st.session_state["classified_df"]
    if rng is None:
        dfv     = master
        journey = st.session_state["journey_df"]
        rep_kpi  = st.session_state["rep_kpi_df"]
        rep_figs = st.session_state["rep_figures"]
        if rep_kpi is None or rep_figs is None:
            rep_kpi, rep_figs = sales_rep_kpi(dfv, journey)
        analytics = st.session_state["analytics_data"] or customer_analytics_summary(dfv, journey)
        exec_data = st.session_state["exec_data"] or executive_dashboard_data(dfv, journey, rep_kpi)
    else:
        with st.spinner("📅 تطبيق فلتر الفترة..."):
            d = pd.to_datetime(master["Visit Date"], errors="coerce")
            dfv = master[(d >= rng[0]) & (d <= rng[1])].copy()
            journey = build_customer_journey(dfv)
            rep_kpi, rep_figs = sales_rep_kpi(dfv, journey)
            analytics = customer_analytics_summary(dfv, journey)
            exec_data = executive_dashboard_data(dfv, journey, rep_kpi)

    cache = {"rng": rng, "classified": dfv, "journey": journey,
             "rep_kpi": rep_kpi, "rep_figs": rep_figs,
             "analytics": analytics, "exec": exec_data}
    st.session_state["_view_cache"] = cache
    return cache


def view_insights(view: dict) -> dict:
    """Lazily compute promises / visit priorities / competitors for the
    active view; results stick to the view cache until the filter changes."""
    if "promises" not in view:
        with st.spinner("🔎 استخراج الوعود والأولويات والمنافسين..."):
            view["promises"]    = extract_promises(view["classified"], view["journey"])
            view["nbv"]         = next_best_visits(view["journey"], view["classified"], view["promises"])
            view["competitors"] = competitor_mentions(view["classified"], view["journey"])
    return view


def _xlsx_download(df: pd.DataFrame, label: str, file_name: str, key: str):
    """Small helper: offer a DataFrame as a styled-enough Excel download."""
    out = io.BytesIO()
    export_df = df.copy()
    for col in export_df.columns:
        if pd.api.types.is_datetime64_any_dtype(export_df[col]):
            export_df[col] = export_df[col].dt.strftime("%Y-%m-%d")
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        export_df.to_excel(w, index=False)
    st.download_button(label, data=out.getvalue(), file_name=file_name, key=key,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def reclassify_and_save():
    """Re-run classification on the loaded data (after rule/merge changes),
    re-apply manual overrides, rebuild everything and persist."""
    master = st.session_state["classified_df"]
    with st.spinner("🧠 إعادة التصنيف..."):
        reclassified = classify_dataframe(master)
        reclassified, _ = apply_saved_overrides(reclassified)
        st.session_state["classified_df"] = reclassified
    with st.spinner("📖 إعادة بناء رحلة العميل..."):
        st.session_state["journey_df"] = build_customer_journey(reclassified)
    rebuild_dashboards()
    with st.spinner("💾 حفظ..."):
        save_session(
            classified_df=st.session_state["classified_df"],
            journey_df=st.session_state["journey_df"],
            rep_kpi_df=st.session_state["rep_kpi_df"],
            file_name=st.session_state.get("file_name", ""),
        )


def run_full_pipeline(raw_df: pd.DataFrame, uploaded_file=None):
    with st.spinner("🔄 تنظيف البيانات..."):
        clean = clean_dataframe(raw_df)
        clean = apply_name_merges(clean)
        st.session_state["clean_df"] = clean
    with st.spinner("🧠 تصنيف الزيارات..."):
        classified = classify_dataframe(clean)
        # Re-apply saved manual classifications (matched by visit key,
        # so they survive re-uploads of updated files)
        classified, n_overrides = apply_saved_overrides(classified)
        if n_overrides:
            st.info(f"✏️ تم تطبيق {n_overrides:,} تصنيف يدوي محفوظ على البيانات الجديدة")
        st.session_state["classified_df"] = classified
    with st.spinner("📖 بناء رحلة العميل..."):
        journey = build_customer_journey(classified)
        st.session_state["journey_df"] = journey
    with st.spinner("📊 حساب KPIs..."):
        rep_kpi, rep_figs = sales_rep_kpi(classified, journey)
        st.session_state["rep_kpi_df"]  = rep_kpi
        st.session_state["rep_figures"] = rep_figs
    with st.spinner("📈 تحليلات العملاء..."):
        st.session_state["analytics_data"] = customer_analytics_summary(classified, journey)
    with st.spinner("🏢 لوحة التحكم..."):
        st.session_state["exec_data"] = executive_dashboard_data(classified, journey, rep_kpi)

    st.session_state["processing_done"] = True

    # ── Auto-save ──
    with st.spinner("💾 حفظ البيانات..."):
        ok, msg = save_session(
            classified_df=classified,
            journey_df=journey,
            rep_kpi_df=rep_kpi,
            file_name=st.session_state.get("file_name", ""),
            uploaded_file=uploaded_file,
        )
        if ok:
            st.success(msg)
        else:
            st.warning(msg)


# ═══════════════════════════════════════════════════════════════════
# AUTO-LOAD SAVED DATA ON FIRST RUN
# ═══════════════════════════════════════════════════════════════════

if not st.session_state["processing_done"] and not st.session_state["storage_loaded"]:
    st.session_state["storage_loaded"] = True
    if has_saved_data():
        ok, data = load_session()
        if ok and data:
            st.session_state["classified_df"] = data["classified_df"]
            st.session_state["journey_df"]    = data["journey_df"]
            st.session_state["rep_kpi_df"]    = data["rep_kpi_df"]
            st.session_state["file_name"]     = data["metadata"].get("file_name", "")
            rebuild_dashboards()
            st.session_state["processing_done"] = True


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:11px;padding:14px 6px 16px">
        <div style="width:38px;height:38px;border-radius:9px;background:#2DD4BF;display:flex;align-items:center;justify-content:center;color:#0A0E11;font-weight:700;font-size:16px">W</div>
        <div>
            <div style="font-size:15px;font-weight:700;letter-spacing:.3px;color:#E6EDF3">WDI Analytics</div>
            <div style="font-size:10px;color:#566573;margin-top:2px">Visit Analytics Engine v2.0</div>
        </div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio("Navigation", options=[
        "مركز الرفع",
        "تصنيف العملاء",
        "تحليلات العملاء",
        "أداء المندوبين",
        "لوحة التحكم التنفيذية",
        "خطة المتابعة",
        "المنافسون",
        "عميل 360",
        "جودة البيانات والمحرك",
        "الإعدادات",
    ], label_visibility="collapsed")

    st.markdown("---")

    if st.session_state["processing_done"]:
        classified_ = st.session_state.get("classified_df")
        journey_    = st.session_state.get("journey_df")
        meta = get_saved_metadata()

        # ── Global date filter (applies to all analytics pages) ──
        st.markdown('<div style="font-size:10px;color:#2DD4BF;font-weight:600;letter-spacing:1px;margin-bottom:4px">فلتر الفترة · DATE FILTER</div>', unsafe_allow_html=True)
        _dates = pd.to_datetime(classified_["Visit Date"], errors="coerce").dropna()
        if not _dates.empty:
            _dmin, _dmax = _dates.min().date(), _dates.max().date()
            if "flt_from" not in st.session_state:
                st.session_state["flt_from"] = _dmin
            if "flt_to" not in st.session_state:
                st.session_state["flt_to"] = _dmax
            st.date_input("من", key="flt_from")
            st.date_input("إلى", key="flt_to")
            fc1, fc2 = st.columns(2)
            with fc1:
                if st.button("✅ تطبيق", use_container_width=True, key="flt_apply"):
                    _f = pd.Timestamp(st.session_state["flt_from"])
                    _t = pd.Timestamp(st.session_state["flt_to"]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                    _d = pd.to_datetime(classified_["Visit Date"], errors="coerce")
                    if ((_d >= _f) & (_d <= _t)).any():
                        st.session_state["date_range"] = (_f, _t)
                        st.rerun()
                    else:
                        st.error("لا توجد زيارات في هذه الفترة")
            with fc2:
                if st.button("🔄 الكل", use_container_width=True, key="flt_reset"):
                    st.session_state["date_range"] = None
                    st.rerun()
            if st.session_state.get("date_range"):
                _r = st.session_state["date_range"]
                st.markdown(
                    f"<div style='background:rgba(45,212,191,.12);padding:5px 8px;border-radius:6px;font-size:10.5px;color:#2DD4BF'>"
                    f"الفلتر نشط: {str(_r[0])[:10]} ← {str(_r[1])[:10]}</div>",
                    unsafe_allow_html=True)
        st.markdown("---")

        _ov = f"""<div style="margin-top:8px;background:rgba(112,173,71,.15);border:1px solid rgba(112,173,71,.3);padding:5px 9px;border-radius:6px;font-size:11px;color:#9CD07E">✏ {meta.get('override_count',0)} تصنيف يدوي محفوظ</div>""" if meta.get("override_count", 0) > 0 else ""
        st.markdown(f"""
        <div style="background:#10171D;border:1px solid #1D262F;border-radius:9px;padding:12px 13px;font-size:11.5px;line-height:2;color:#8B98A5">
            <div style="font-size:10px;color:#2DD4BF;font-weight:600;letter-spacing:1px;margin-bottom:5px">البيانات المحملة · DATA</div>
            <div style="font-weight:600;color:#E6EDF3;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{st.session_state.get('file_name','—')}</div>
            <div>{fmt_number(len(classified_)) if classified_ is not None else '0'} زيارة · {fmt_number(classified_['Customer Name'].nunique()) if classified_ is not None else '0'} عميل</div>
            <div>{fmt_number(classified_['Sales Rep Name'].nunique()) if classified_ is not None else '0'} مندوب مبيعات</div>
            <div style="color:#566573;font-size:10.5px">آخر حفظ: {meta.get('last_saved','—')[:16] if meta.get('last_saved') else '—'}</div>
            {_ov}
        </div>""", unsafe_allow_html=True)
    else:
        st.info("📂 لا توجد بيانات")

    st.markdown("---")
    st.markdown(
        "<div style='font-size:9.5px;color:#3D4B58;text-align:center'>WDI Analytics v2.0 · Fully Offline</div>",
        unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 1 — UPLOAD CENTER
# ═══════════════════════════════════════════════════════════════════

if page == "مركز الرفع":
    page_banner("مركز الرفع", "UPLOAD CENTER — رفع ملف Excel وتشغيل محرك التصنيف", PAGE_ACCENT["upload"])

    # ── Show saved data status ──
    if has_saved_data():
        meta = get_saved_metadata()
        st.info(f"""
        💾 **توجد بيانات محفوظة** من جلسة سابقة:
        الملف: `{meta.get('file_name','—')}` |
        {fmt_number(meta.get('total_records',0))} زيارة |
        آخر حفظ: {meta.get('last_saved','—')[:16]}
        """)

    uploaded = st.file_uploader(
        "ارفع ملف Excel هنا",
        type=["xlsx","xls"],
        help="الصف الأول يجب أن يحتوي على أسماء الأعمدة",
    )

    if uploaded is not None:
        with st.spinner("جارٍ تحميل الملف..."):
            raw_df, err = load_excel(uploaded)

        if err:
            st.error(f"❌ {err}")
        else:
            st.session_state["raw_df"]   = raw_df
            st.session_state["file_name"] = uploaded.name
            st.session_state["processing_done"] = False

            is_valid, missing, present = validate_columns(raw_df)
            c1, c2 = st.columns([2, 1])

            with c1:
                if is_valid:
                    st.success("✅ كل الأعمدة المطلوبة موجودة")
                else:
                    st.error(f"❌ أعمدة ناقصة: {', '.join(missing)}")

            with c2:
                stats = basic_stats(raw_df)
                st.markdown(f"""
                <div class="section-card">
                <b>📋 ملخص الملف</b><br><br>
                📄 <b>{uploaded.name}</b><br>
                🗒️ {fmt_number(stats['total_records'])} زيارة<br>
                👥 {fmt_number(stats['unique_customers'])} عميل<br>
                🧑‍💼 {fmt_number(stats['unique_reps'])} مندوب<br>
                📅 من {str(stats['date_range_start'])[:10] if stats['date_range_start'] else '—'}<br>
                📅 إلى {str(stats['date_range_end'])[:10] if stats['date_range_end'] else '—'}
                </div>""", unsafe_allow_html=True)

            section("معاينة البيانات")
            st.dataframe(raw_df.head(50), use_container_width=True, height=350)

            section("التحقق من الأعمدة")
            checks = ""
            for c in REQUIRED_COLUMNS:
                ok_c = c in present
                mark, mcolor = ("✓", "#9CD07E") if ok_c else ("✕", "#F08080")
                checks += (f'<div style="display:flex;align-items:center;gap:8px;background:#10171D;'
                           f'border:1px solid #1D262F;border-radius:7px;padding:7px 11px;font-size:11.5px">'
                           f'<span style="color:{mcolor};font-weight:700">{mark}</span>'
                           f'<span style="color:#C6D0DA">{_html.escape(c)}</span></div>')
            st.markdown(f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;direction:rtl">{checks}</div>',
                        unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if is_valid:
                if st.button("🚀 تشغيل التصنيف وحفظ البيانات", use_container_width=True):
                    uploaded.seek(0)
                    run_full_pipeline(raw_df, uploaded_file=uploaded)
                    st.success("✅ تم التصنيف والحفظ! يمكنك الآن التنقل بين الصفحات.")
                    st.balloons()
    else:
        st.markdown("""
        <div class="section-card" style="text-align:center;padding:40px">
            <div style="width:54px;height:54px;margin:0 auto 14px;border-radius:12px;background:rgba(45,212,191,.12);border:1px solid rgba(45,212,191,.3);display:flex;align-items:center;justify-content:center;color:#2DD4BF;font-weight:700;font-size:22px">W</div>
            <div style="font-size:18px;font-weight:700;color:#E6EDF3">WDI Visit Analytics Engine</div>
            <div style="font-size:12.5px;color:#8B98A5;max-width:460px;margin:8px auto 0;line-height:1.9">
                ارفع ملف Excel لتصنيف الزيارات وتحليل أداء المندوبين تلقائياً — بدون إنترنت.
            </div>
        </div>""", unsafe_allow_html=True)

        with st.expander("📋 الأعمدة المطلوبة"):
            chips = "".join(f'<span class="wdi-chip">{_html.escape(c)}</span>' for c in REQUIRED_COLUMNS)
            st.markdown(f'<div style="direction:rtl">{chips}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 2 — CUSTOMER CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════

elif page == "تصنيف العملاء":
    page_banner("تصنيف العملاء", "CLASSIFICATION — محرك تصنيف بالكلمات المفتاحية لكل زيارة", PAGE_ACCENT["classify"])

    if not st.session_state["processing_done"]:
        no_data_warning()
        st.stop()

    view = get_view()
    classified_df = view["classified"]   # respects the sidebar date filter
    journey_df    = view["journey"]
    master_df     = st.session_state["classified_df"]  # full data — used by the override workflow

    kpi_row({
        "إجمالي الزيارات":   len(classified_df),
        "عملاء فريدون":      classified_df["Customer Name"].nunique(),
        "تم تصنيفهم":        int((classified_df["Suggested Status"] != "unclassified").sum()),
        "غير مصنف":          int((classified_df["Suggested Status"] == "unclassified").sum()),
    })

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 نتائج التصنيف",
        "🗺️ رحلة العميل",
        "✏️ تصنيف يدوي",
        "⚙️ قواعد الكلمات",
        "📥 تصدير",
        "🔗 توحيد الأسماء",
    ])

    # ── Tab 1: Results ──
    with tab1:
        section("نتائج التصنيف")

        view_mode = st.radio(
            "طريقة العرض",
            ["👤 موقف نهائي لكل عميل", "📋 كل الزيارات"],
            horizontal=True, key="cls_view_mode",
        )

        fc0, fc1, fc2, fc3 = st.columns(4)
        with fc0:
            cls_search = st.text_input("بحث باسم العميل…", key="cls_search")
        with fc1:
            reps_list = ["الكل"] + sorted(classified_df["Sales Rep Name"].dropna().unique().tolist())
            sel_rep = st.selectbox("المندوب", reps_list, key="cls_rep")
        with fc2:
            statuses_list = ["الكل"] + sorted(classified_df["Display Status"].dropna().unique().tolist())
            sel_status = st.selectbox("الحالة", statuses_list, key="cls_status",
                                      format_func=lambda s: STATUS_AR.get(s, s))
        with fc3:
            min_conf = st.slider("حد الثقة الأدنى", 0, 100, 0, 5, key="cls_conf")

        filtered = classified_df.copy()
        if cls_search.strip():
            filtered = filtered[filtered["Customer Name"].astype(str).str.contains(cls_search.strip(), na=False)]
        if sel_rep    != "الكل": filtered = filtered[filtered["Sales Rep Name"] == sel_rep]
        if sel_status != "الكل": filtered = filtered[filtered["Display Status"]  == sel_status]
        filtered = filtered[filtered["Confidence Score"] >= min_conf]

        visit_counts = classified_df.groupby("Customer Name").size().reset_index(name="Visit Count")
        filtered = filtered.merge(visit_counts, on="Customer Name", how="left")

        # ── Design charts: confidence histogram + filtered status donut ──
        chc1, chc2 = st.columns(2)
        with chc1:
            st.markdown("**توزيع مستوى الثقة** <span class='sec-en'>CONFIDENCE</span>", unsafe_allow_html=True)
            _conf = pd.to_numeric(filtered["Confidence Score"], errors="coerce").fillna(0)
            _buckets = pd.cut(_conf, bins=[-0.1, 20, 40, 60, 80, 100.1],
                              labels=["0-20", "20-40", "40-60", "60-80", "80-100"]).value_counts().sort_index()
            fig_conf = go.Figure(go.Bar(
                x=_buckets.index.astype(str), y=_buckets.values,
                marker=dict(color="#4C9AFF", cornerradius=4),
                text=_buckets.values, textposition="outside"))
            fig_conf.update_layout(template="wdi_dark", paper_bgcolor="rgba(0,0,0,0)",
                                   height=260, margin=dict(l=10, r=10, t=20, b=10),
                                   xaxis_title="", yaxis_title="")
            st.plotly_chart(fig_conf, use_container_width=True)
        with chc2:
            st.markdown("**توزيع الحالات في النتائج المفلترة**", unsafe_allow_html=True)
            _sc = filtered["Display Status"].value_counts()
            fig_fst = go.Figure(go.Pie(
                labels=[STATUS_AR.get(s, s) for s in _sc.index], values=_sc.values,
                hole=0.55, textinfo="percent",
                marker=dict(colors=[STATUS_COLORS.get(s, "#888") for s in _sc.index],
                            line=dict(color="#161D24", width=2))))
            fig_fst.update_layout(template="wdi_dark", paper_bgcolor="rgba(0,0,0,0)",
                                  height=260, margin=dict(l=10, r=10, t=20, b=10),
                                  legend=dict(orientation="v", x=1.02, y=0.5))
            st.plotly_chart(fig_fst, use_container_width=True)

        if view_mode == "👤 موقف نهائي لكل عميل":
            # Last REAL status per customer (No Meeting / Unclassified visits
            # don't overwrite the customer's previous classification)
            final_df = final_status_per_customer(filtered)
            date_range = classified_df.groupby("Customer Name")["Visit Date"].agg(
                First_Visit="min", Last_Visit="max"
            ).reset_index()
            final_df = final_df.merge(date_range, on="Customer Name", how="left")

            for dc in ["First_Visit","Last_Visit","Visit Date"]:
                if dc in final_df.columns:
                    final_df[dc] = pd.to_datetime(final_df[dc], errors="coerce").dt.strftime("%Y-%m-%d")

            show_cols = ["Customer Name","Sales Rep Name","Governorate","Display Status",
                         "Visit Count","First_Visit","Last_Visit","Confidence Score",
                         "Override Source","Matched Keywords"]
            show_cols = [c for c in show_cols if c in final_df.columns]

            # Status summary metrics
            sm = final_df["Display Status"].value_counts()
            sm_cols = st.columns(min(len(sm), 6))
            for col, (s, c) in zip(sm_cols, sm.items()):
                with col: st.metric(s, c)

            st.info(f"👤 **{len(final_df):,}** عميل فريد")
            st.dataframe(final_df[show_cols].reset_index(drop=True),
                         use_container_width=True, height=500)

            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="openpyxl") as w:
                final_df[show_cols].to_excel(w, index=False, sheet_name="الموقف النهائي")
            st.download_button("⬇️ تحميل الموقف النهائي Excel",
                               data=out.getvalue(),
                               file_name="Final_Customer_Status.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            # Design-styled visit log (first 300 rows for speed)
            st.info(f"📋 **{fmt_number(len(filtered))}** نتيجة — يعرض أول 300")
            _log = filtered.sort_values("Visit Date", ascending=False).head(300).copy()
            _log["Visit Date"] = pd.to_datetime(_log["Visit Date"], errors="coerce").dt.strftime("%Y-%m-%d")
            _log["Visit Notes"] = _log["Visit Notes"].astype(str).str.slice(0, 90)
            _log["Confidence Score"] = pd.to_numeric(_log["Confidence Score"], errors="coerce").fillna(0).round(0).astype(int)
            _log_cols = [c for c in ["Visit Date", "Customer Name", "Sales Rep Name",
                                     "Display Status", "Confidence Score", "Visit Notes"]
                         if c in _log.columns]
            html_table(_log[_log_cols].reset_index(drop=True),
                       badge_cols=("Display Status",),
                       cond_colors={"Confidence Score": lambda v: "#70AD47" if float(v) >= 70 else ("#FFC000" if float(v) >= 40 else "#F08080")},
                       height=480)
            _xlsx_download(filtered, "⬇ تصدير النتائج المفلترة Excel", "Classification_Filtered.xlsx", key="dl_clf")

    # ── Tab 2: Journey ──
    with tab2:
        section("رحلة العميل")
        search = st.text_input("🔍 ابحث عن عميل", key="journey_search")
        jdf = journey_df.copy()
        if search.strip():
            jdf = jdf[jdf["Customer Name"].str.contains(search.strip(), case=False, na=False)]

        show_j = ["Customer Name","Latest Status","Latest Confidence","Visit Count",
                  "First Visit Date","Last Visit Date","Days Since Last Visit",
                  "Governorate","Sales Rep Name"]
        show_j = [c for c in show_j if c in jdf.columns]
        st.dataframe(jdf[show_j].reset_index(drop=True), use_container_width=True, height=420)

        if not jdf.empty:
            st.markdown("---")
            sel_cust = st.selectbox("اختر عميلاً لعرض رحلته", jdf["Customer Name"].tolist(), key="jd_sel")
            if sel_cust:
                row = jdf[jdf["Customer Name"] == sel_cust].iloc[0]
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("زيارات", row["Visit Count"])
                c2.metric("الحالة",  row["Latest Status"])
                c3.metric("آخر زيارة", str(row.get("Days Since Last Visit","—")) + " يوم")
                c4.metric("ثقة", f"{row.get('Latest Confidence',0):.1f}%")
                st.code(row.get("Status History","—"), language=None)

                cust_v = classified_df[classified_df["Customer Name"] == sel_cust].copy()
                if "Visit Date" in cust_v.columns:
                    cust_v["Visit Date"] = pd.to_datetime(cust_v["Visit Date"], errors="coerce").dt.strftime("%Y-%m-%d")
                vcols = ["Visit Date","Sales Rep Name","Display Status","Confidence Score","Visit Notes","Matched Keywords","Override Source"]
                vcols = [c for c in vcols if c in cust_v.columns]
                st.dataframe(cust_v[vcols].reset_index(drop=True), use_container_width=True)

    # ── Tab 3: Manual Override ──
    with tab3:
        section("✏️ التصنيف اليدوي للزيارات غير المصنفة")

        unclass_count = int((master_df["Display Status"] == "Unclassified").sum())
        manual_count  = int((master_df.get("Override Source","") == "Manual").sum()) if "Override Source" in master_df.columns else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("غير مصنف",        unclass_count)
        m2.metric("تصنيف يدوي تم",   manual_count)
        m3.metric("القيم المسموحة",   len(VALID_STATUSES))

        st.markdown("---")

        # ── Step 1: Export ──
        st.markdown("#### 1️⃣ تصدير الزيارات الغير مصنفة")
        if unclass_count == 0:
            st.success("✅ لا توجد زيارات غير مصنفة!")
        else:
            st.info(f"يوجد **{unclass_count:,}** زيارة غير مصنفة — حمّل الملف وأضف التصنيف في عمود **Manual Status**")
            xlsx_unc = export_unclassified(master_df)
            st.download_button(
                f"⬇️ تحميل الزيارات الغير مصنفة ({unclass_count:,} زيارة)",
                data=xlsx_unc,
                file_name="Unclassified_Visits.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        st.markdown("---")

        # ── Step 2: Import ──
        st.markdown("#### 2️⃣ رفع الملف بعد التصنيف اليدوي")
        st.markdown(f"""
        **القيم المسموح بها في عمود Manual Status:**
        {' | '.join(['`'+s+'`' for s in VALID_STATUSES])}
        """)

        override_file = st.file_uploader(
            "ارفع الملف المعدّل هنا",
            type=["xlsx"],
            key="override_uploader",
        )

        if override_file is not None:
            st.warning("⚠️ سيتم تحديث التصنيف وإعادة حساب كل التقارير — هل أنت متأكد؟")
            col_confirm, col_cancel = st.columns(2)

            with col_confirm:
                if st.button("✅ تأكيد وتطبيق التصنيف", use_container_width=True):
                    updated_df, count_changed, errors = import_overrides(
                        override_file, master_df
                    )

                    if errors:
                        for err in errors:
                            st.warning(err)

                    if count_changed > 0:
                        # Update session state
                        st.session_state["classified_df"] = updated_df

                        with st.spinner("🔄 إعادة بناء رحلة العميل..."):
                            new_journey = build_customer_journey(updated_df)
                            st.session_state["journey_df"] = new_journey

                        # Rebuild all dashboards
                        rebuild_dashboards()

                        # Save to disk
                        with st.spinner("💾 حفظ التحديثات..."):
                            save_session(
                                classified_df=updated_df,
                                journey_df=st.session_state["journey_df"],
                                rep_kpi_df=st.session_state["rep_kpi_df"],
                                file_name=st.session_state.get("file_name",""),
                            )

                        st.success(f"✅ تم تحديث **{count_changed:,}** زيارة وحفظ البيانات — كل الصفحات تحدّثت!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ لم يتم تطبيق أي تغيير — تحقق من الملف")

            with col_cancel:
                if st.button("❌ إلغاء", use_container_width=True):
                    st.rerun()

        # ── Overrides history ──
        st.markdown("---")
        st.markdown("#### 📋 سجل التصنيفات اليدوية")
        if "Override Source" in master_df.columns:
            manual_df = master_df[master_df["Override Source"] == "Manual"]
            if not manual_df.empty:
                show_o = ["Visit Date","Customer Name","Sales Rep Name","Display Status","Governorate","Visit Notes"]
                show_o = [c for c in show_o if c in manual_df.columns]
                if "Visit Date" in manual_df.columns:
                    manual_df = manual_df.copy()
                    manual_df["Visit Date"] = pd.to_datetime(manual_df["Visit Date"], errors="coerce").dt.strftime("%Y-%m-%d")
                st.dataframe(manual_df[show_o].reset_index(drop=True),
                             use_container_width=True, height=300)

                if st.button("🗑️ حذف كل التصنيفات اليدوية", type="secondary"):
                    ok, msg = clear_overrides()
                    if ok:
                        st.success(msg + " — يرجى إعادة تحميل البيانات")
                    else:
                        st.error(msg)
            else:
                st.info("لا توجد تصنيفات يدوية حتى الآن")
        else:
            st.info("لا توجد تصنيفات يدوية حتى الآن")

    # ── Tab 4: Keyword Rules ──
    with tab4:
        section("قواعد الكلمات المفتاحية")

        # ── Custom rules editor ──
        _STATUS_AR = {
            "current": "عميل حالي", "potential": "عميل محتمل", "target": "عميل مستهدف",
            "new": "عميل جديد", "former": "عميل سابق",
            "not_interested": "غير مهتم", "no_meeting": "لم تتم المقابلة",
        }
        custom_rules = load_custom_rules()

        with st.expander(f"➕ إضافة / إدارة القواعد المخصصة ({len(custom_rules)} قاعدة مخصصة)", expanded=False):
            with st.form("add_rule_form", clear_on_submit=True):
                rc1, rc2, rc3 = st.columns([2, 1, 1])
                new_kw     = rc1.text_input("الكلمة / العبارة المفتاحية")
                new_status = rc2.selectbox("تُصنَّف كـ", list(_STATUS_AR.keys()),
                                           format_func=lambda k: _STATUS_AR[k])
                new_score  = rc3.number_input("الدرجة", min_value=10, max_value=100, value=60, step=10)
                if st.form_submit_button("➕ إضافة القاعدة", use_container_width=True):
                    if new_kw.strip():
                        custom_rules.append({"keyword": new_kw.strip(),
                                             "status": new_status, "score": int(new_score)})
                        ok, msg = save_custom_rules(custom_rules)
                        if ok:
                            set_custom_rules(custom_rules)
                            st.success(f"{msg} — اضغط (إعادة التصنيف) بالأسفل لتطبيقها على البيانات")
                        else:
                            st.error(msg)
                    else:
                        st.warning("اكتب الكلمة المفتاحية أولاً")

            if custom_rules:
                del_kws = st.multiselect(
                    "🗑️ اختر قواعد مخصصة للحذف",
                    [f"{r['keyword']} → {_STATUS_AR.get(r['status'], r['status'])} ({r['score']})"
                     for r in custom_rules],
                    key="del_rules",
                )
                if del_kws and st.button("🗑️ حذف المحدد", key="del_rules_btn"):
                    labels = [f"{r['keyword']} → {_STATUS_AR.get(r['status'], r['status'])} ({r['score']})"
                              for r in custom_rules]
                    remaining = [r for r, lbl in zip(custom_rules, labels) if lbl not in del_kws]
                    ok, msg = save_custom_rules(remaining)
                    if ok:
                        set_custom_rules(remaining)
                        st.success(f"{msg} — اضغط (إعادة التصنيف) لتطبيق التغيير")
                        st.rerun()
                    else:
                        st.error(msg)

            if st.button("🔁 إعادة التصنيف بالقواعد الحالية وحفظ النتائج", use_container_width=True, key="reclassify_btn"):
                reclassify_and_save()
                st.success("✅ تمت إعادة التصنيف والحفظ — كل الصفحات تحدّثت")
                st.rerun()

        t3c1, t3c2 = st.columns([1,1])

        with t3c1:
            rules_df = get_rules_dataframe()
            status_filter = ["الكل"] + sorted(rules_df["Status"].unique().tolist())
            sel_rs = st.selectbox("فلتر الحالة", status_filter, key="rules_filter")
            if sel_rs != "الكل":
                rules_df = rules_df[rules_df["Status"] == sel_rs]
            st.dataframe(rules_df.reset_index(drop=True), use_container_width=True,
                         height=400, hide_index=True)

        with t3c2:
            st.markdown("#### 📤 تصدير حسب الحالة")
            avail_statuses = ["الكل"] + sorted(classified_df["Display Status"].dropna().unique().tolist())
            sel_exp_status = st.selectbox("الحالة", avail_statuses, key="exp_status")
            sel_exp_rep    = st.selectbox("المندوب", ["الكل"]+sorted(classified_df["Sales Rep Name"].dropna().unique().tolist()), key="exp_rep")
            sel_exp_gov    = st.selectbox("المحافظة", ["الكل"]+sorted(classified_df["Governorate"].dropna().unique().tolist()), key="exp_gov")

            exp_df = classified_df.copy()
            if sel_exp_status != "الكل": exp_df = exp_df[exp_df["Display Status"] == sel_exp_status]
            if sel_exp_rep    != "الكل": exp_df = exp_df[exp_df["Sales Rep Name"] == sel_exp_rep]
            if sel_exp_gov    != "الكل": exp_df = exp_df[exp_df["Governorate"] == sel_exp_gov]

            m1,m2,m3 = st.columns(3)
            m1.metric("زيارات",  f"{len(exp_df):,}")
            m2.metric("عملاء",   f"{exp_df['Customer Name'].nunique():,}")
            m3.metric("مندوبين", f"{exp_df['Sales Rep Name'].nunique():,}")

            if not exp_df.empty:
                exp_cols = ["Visit Date","Customer Name","Sales Rep Name","Display Status",
                            "Governorate","District","Visit Notes","Matched Keywords","Classification Reason"]
                exp_cols = [c for c in exp_cols if c in exp_df.columns]
                exp_out  = exp_df[exp_cols].copy()
                if "Visit Date" in exp_out.columns:
                    exp_out["Visit Date"] = pd.to_datetime(exp_out["Visit Date"], errors="coerce").dt.strftime("%Y-%m-%d")

                out2 = io.BytesIO()
                with pd.ExcelWriter(out2, engine="openpyxl") as w:
                    exp_out.to_excel(w, index=False)
                st.download_button(
                    f"⬇️ تحميل ({sel_exp_status}) — {len(exp_out):,} زيارة",
                    data=out2.getvalue(),
                    file_name=f"Visits_{sel_exp_status.replace(' ','_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

    # ── Tab 5: Export ──
    with tab5:
        section("تصدير نتائج التصنيف")
        xlsx_cls = export_classification_results(classified_df)
        st.download_button("⬇️ تحميل Classification Results.xlsx",
                           data=xlsx_cls, file_name="Classification_Results.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)

    # ── Tab 6: Name Unification Review ──
    with tab6:
        section("🔗 مراجعة وتوحيد أسماء العملاء المتشابهة")
        st.markdown("""
        الأسماء تُقارن **داخل نفس المحافظة فقط** — الاسم المتشابه في محافظة مختلفة يُعتبر عميلاً آخر.
        لا يتم أي دمج تلقائي: كل مجموعة تحتاج **موافقتك** هنا، ويمكن التراجع عن أي دمج لاحقاً.
        """)

        tmp = deduplicate_customer_names(master_df)
        if "Governorate" not in tmp.columns:
            tmp["Governorate"] = ""
        grp = (tmp.groupby(["Customer Name Cleaned", "Governorate"]).agg(
                    Variants=("Customer Name", lambda x: sorted(set(x))),
                    Visits=("Customer Name", "count"),
               ).reset_index())
        cand = grp[(grp["Variants"].apply(len) > 1) & (grp["Customer Name Cleaned"] != "")]

        merges = load_name_merges()
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("مجموعات مقترحة للمراجعة", len(cand))
        mc2.metric("دمج معتمد", merges["Canonical"].nunique() if not merges.empty else 0)
        mc3.metric("أسماء موحّدة", len(merges))

        if cand.empty:
            st.success("✅ لا توجد أسماء متشابهة تحتاج مراجعة داخل نفس المحافظة")
        else:
            cand = cand.copy()
            cand["_label"] = cand.apply(
                lambda r: f"{r['Customer Name Cleaned']} — {r['Governorate'] or 'بدون محافظة'} ({len(r['Variants'])} اسم)",
                axis=1)
            sel_grp = st.selectbox("اختر مجموعة للمراجعة", cand["_label"].tolist(), key="merge_grp")
            row = cand[cand["_label"] == sel_grp].iloc[0]

            # Visit counts per variant
            variant_counts = (master_df[master_df["Customer Name"].isin(row["Variants"])]
                              .groupby("Customer Name").size().rename("عدد الزيارات").reset_index())
            st.dataframe(variant_counts, use_container_width=True, hide_index=True)

            canonical = st.radio("الاسم الموحّد (الذي ستُنسب إليه كل الزيارات)",
                                 row["Variants"], key="merge_canon")
            if st.button("✅ اعتماد الدمج", use_container_width=True, key="merge_apply"):
                new_rows = pd.DataFrame([
                    {"Governorate": row["Governorate"], "Variant": v, "Canonical": canonical}
                    for v in row["Variants"] if v != canonical
                ])
                combined = pd.concat([merges, new_rows], ignore_index=True)
                combined = combined.drop_duplicates(subset=["Governorate", "Variant"], keep="last")
                ok, msg = save_name_merges(combined)
                if ok:
                    st.session_state["classified_df"] = apply_name_merges(st.session_state["classified_df"])
                    st.session_state["journey_df"] = build_customer_journey(st.session_state["classified_df"])
                    rebuild_dashboards()
                    save_session(
                        classified_df=st.session_state["classified_df"],
                        journey_df=st.session_state["journey_df"],
                        rep_kpi_df=st.session_state["rep_kpi_df"],
                        file_name=st.session_state.get("file_name", ""),
                    )
                    st.success(f"✅ تم دمج {len(new_rows)} اسم في «{canonical}» وحفظ البيانات")
                    st.rerun()
                else:
                    st.error(msg)

        # ── Approved merges + undo ──
        if not merges.empty:
            st.markdown("---")
            st.markdown("#### 📋 عمليات الدمج المعتمدة")
            st.dataframe(merges.reset_index(drop=True), use_container_width=True, hide_index=True, height=260)
            undo_canons = st.multiselect("↩️ اختر أسماء موحّدة للتراجع عن دمجها",
                                         sorted(merges["Canonical"].unique().tolist()), key="undo_merges")
            if undo_canons and st.button("↩️ تراجع عن الدمج المحدد", key="undo_btn"):
                remaining = merges[~merges["Canonical"].isin(undo_canons)]
                ok, msg = save_name_merges(remaining)
                if ok:
                    st.session_state["classified_df"] = apply_name_merges(st.session_state["classified_df"])
                    st.session_state["journey_df"] = build_customer_journey(st.session_state["classified_df"])
                    rebuild_dashboards()
                    save_session(
                        classified_df=st.session_state["classified_df"],
                        journey_df=st.session_state["journey_df"],
                        rep_kpi_df=st.session_state["rep_kpi_df"],
                        file_name=st.session_state.get("file_name", ""),
                    )
                    st.success("✅ تم التراجع واستعادة الأسماء الأصلية")
                    st.rerun()
                else:
                    st.error(msg)


# ═══════════════════════════════════════════════════════════════════
# PAGE 3 — CUSTOMER ANALYTICS
# ═══════════════════════════════════════════════════════════════════

elif page == "تحليلات العملاء":
    page_banner("تحليلات العملاء", "CUSTOMER ANALYTICS — تحليل شرائح العملاء وأنماط الزيارات", PAGE_ACCENT["analytics"])

    if not st.session_state["processing_done"]:
        no_data_warning(); st.stop()

    view = get_view()
    analytics  = view["analytics"]
    journey_df = view["journey"]
    kpis = analytics["kpi"]

    _A_SPEC = [
        ("إجمالي الزيارات", "TOTAL VISITS",   "Total Visits",        "#2DD4BF"),
        ("عملاء فريدون",    "UNIQUE",         "Unique Customers",    "#4C9AFF"),
        ("عملاء متكررون",   "REPEATED",       "Repeated Customers",  "#4C9AFF"),
        ("جدد",             "NEW",            "New Customers",       "#8FB4D9"),
        ("حاليون",          "CURRENT",        "Current Customers",   "#70AD47"),
        ("محتملون",         "POTENTIAL",      "Potential Customers", "#2E75B6"),
        ("مستهدفون",        "TARGET",         "Target Customers",    "#FFC000"),
        ("سابقون",          "FORMER",         "Former Customers",    "#A9A9A9"),
        ("غير مهتمين",      "NOT INTERESTED", "Not Interested",      "#F08080"),
    ]
    stat_cards([{"label": ar, "en": en, "value": fmt_number(kpis.get(key, 0)), "accent": acc}
                for ar, en, key, acc in _A_SPEC], cols=5)

    ch1, ch2 = st.columns(2)
    with ch1:
        if analytics.get("fig_status_pie"): st.plotly_chart(analytics["fig_status_pie"], use_container_width=True)
    with ch2:
        if analytics.get("fig_gov"):        st.plotly_chart(analytics["fig_gov"],        use_container_width=True)

    section("أكثر 20 عميلاً زيارةً", "TOP 20")
    top20 = analytics.get("top_20", pd.DataFrame())
    if not top20.empty:
        t20l, t20r = st.columns(2)
        with t20r:
            html_table(top20.reset_index(drop=True), badge_cols=("Latest Status",),
                       color_cols={"Visit Count": "#2DD4BF"}, height=470, index_col=True)
        with t20l:
            fig_top = go.Figure(go.Bar(
                y=top20["Customer Name"].astype(str).str.slice(0, 22),
                x=top20["Visit Count"],
                orientation="h", marker=dict(color="#2DD4BF", cornerradius=4),
                text=top20["Visit Count"], textposition="outside",
            ))
            fig_top.update_layout(template="wdi_dark",
                                  paper_bgcolor="rgba(0,0,0,0)", yaxis=dict(autorange="reversed"),
                                  margin=dict(l=10,r=45,t=10,b=10), height=480,
                                  xaxis_title="", yaxis_title="")
            st.plotly_chart(fig_top, use_container_width=True)

    section("العملاء الذين لم تتم زيارتهم", "NOT VISITED")
    nv_tabs = st.tabs(["30 يوم","60 يوم","90 يوم","180 يوم"])
    for tab_obj, days, key in zip(nv_tabs,[30,60,90,180],
                                   ["not_visited_30","not_visited_60","not_visited_90","not_visited_180"]):
        with tab_obj:
            df_nv = analytics.get(key, pd.DataFrame())
            if df_nv.empty:
                st.info(f"لا يوجد عملاء لم يُزاروا منذ {days} يوماً")
            else:
                st.markdown(
                    f'<div style="background:rgba(255,192,0,.08);border:1px solid rgba(255,192,0,.25);'
                    f'border-radius:7px;padding:8px 13px;font-size:12px;color:#FFC000;margin-bottom:10px">'
                    f'⚠ {len(df_nv):,} عميل لم يُزار منذ {days}+ يوم</div>', unsafe_allow_html=True)
                html_table(df_nv.head(200).reset_index(drop=True), badge_cols=("Latest Status",),
                           color_cols={"Days Since Last Visit": "#FFC000"}, height=320, index_col=True)
                xlsx_nv = export_followup_customers(journey_df, days_threshold=days)
                st.download_button(f"⬇ تصدير قائمة {days} يوم Excel",
                                   data=xlsx_nv, file_name=f"Followup_{days}_Days.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    section("توزيع المحافظات والمناطق")
    bd1, bd2 = st.columns(2)
    with bd1:
        gov_df = analytics.get("gov_dist_df", pd.DataFrame())
        if not gov_df.empty:
            st.markdown("**عملاء حسب المحافظة**")
            html_table(gov_df.rename(columns={"Unique Customers": "عملاء فريدون"}),
                       color_cols={"عملاء فريدون": "#4C9AFF"}, height=340)
    with bd2:
        dist_df = analytics.get("district_dist_df", pd.DataFrame())
        if not dist_df.empty:
            st.markdown("**عملاء حسب المنطقة (أعلى 20)**")
            html_table(dist_df.head(20).rename(columns={"Unique Customers": "عملاء فريدون"}),
                       color_cols={"عملاء فريدون": "#4C9AFF"}, height=340)

    section("🗺️ خريطة التغطية")
    cmap = coverage_map(view["classified"], journey_df)
    if cmap["fig"] is not None:
        st.plotly_chart(cmap["fig"], use_container_width=True)
        if cmap["unmatched"]:
            st.caption("⚠️ محافظات لم يتم التعرف على موقعها: " + "، ".join(cmap["unmatched"]))
        with st.expander("📋 جدول التغطية بالمحافظات"):
            html_table(cmap["table"], color_cols={"العملاء": "#4C9AFF", "الحاليون": "#9CD07E"}, height=280)
    else:
        st.info("لا توجد بيانات محافظات كافية لرسم الخريطة")

    section("تصدير")
    journey_clean = journey_df.drop(columns=["_journey"], errors="ignore")
    st.download_button("⬇️ Customer Summary.xlsx",
                       data=export_customer_summary(journey_clean),
                       file_name="Customer_Summary.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════════════════════════
# PAGE 4 — SALES REP PERFORMANCE
# ═══════════════════════════════════════════════════════════════════

elif page == "أداء المندوبين":
    page_banner("أداء المندوبين", "REP PERFORMANCE — الإنتاجية والتحويلات لكل مندوب مبيعات", PAGE_ACCENT["reps"])

    if not st.session_state["processing_done"]:
        no_data_warning(); st.stop()

    view = get_view()
    rep_kpi_df  = view["rep_kpi"]
    rep_figures = view["rep_figs"]
    classified  = view["classified"]

    if rep_kpi_df is None or rep_kpi_df.empty:
        st.warning("لا توجد بيانات مندوبين"); st.stop()

    # ── Full ranking table (design order: table first) ──
    section("ترتيب المندوبين — كل المقاييس", "FULL RANKING")
    _rank_cols = ["Rank", "Sales Rep Name", "Total Visits", "Unique Customers",
                  "Current Customers", "True Conversions", "Visits Per Day",
                  "Conversion Rate (%)"]
    _rank_df = rep_kpi_df[[c for c in _rank_cols if c in rep_kpi_df.columns]].reset_index(drop=True)
    _rank_df = _rank_df.rename(columns={
        "Rank": "#", "Total Visits": "إجمالي الزيارات", "Unique Customers": "عملاء فريدون",
        "Current Customers": "حاليون", "True Conversions": "تحويلات حقيقية",
        "Visits Per Day": "زيارات/يوم", "Conversion Rate (%)": "معدل التحويل %",
    })
    html_table(_rank_df,
               color_cols={"إجمالي الزيارات": "#2DD4BF", "تحويلات حقيقية": "#4C9AFF",
                           "حاليون": "#9CD07E"},
               cond_colors={"معدل التحويل %": lambda v: "#70AD47" if float(v) >= 50 else ("#FFC000" if float(v) >= 25 else "#F08080")},
               height=440)

    # ── Two charts side by side ──
    rc1, rc2 = st.columns(2)
    for col, (title_f, fig) in zip([rc1, rc2], rep_figures[:2]):
        with col:
            section(title_f)
            st.plotly_chart(fig, use_container_width=True)

    # ── Weekday productivity matrix (design style: dots for zeros) ──
    section("إنتاجية أيام الأسبوع", "WEEKDAY PRODUCTIVITY")
    wp = weekday_productivity(classified)
    if not wp["pivot"].empty:
        _wd = wp["pivot"].copy()
        _active = (_wd > 0).sum(axis=1).replace(0, 1)
        _wd["متوسط/يوم عمل"] = (_wd.sum(axis=1) / _active).round(1)
        _wd = _wd.sort_values("متوسط/يوم عمل", ascending=False)
        _wd_show = _wd.reset_index().rename(columns={"Sales Rep Name": "المندوب"})
        _wd_show["المندوب"] = _wd_show["المندوب"].replace("", "(بدون اسم)")
        html_table(_wd_show,
                   cond_colors={c: (lambda v: "#E6EDF3" if str(v) not in ("0", "0.0") else "#2A3540")
                                for c in _wd_show.columns if c not in ("المندوب",)},
                   height=380)
    if not wp["stats"].empty:
        with st.expander("📋 تفاصيل أيام العمل والفجوات"):
            html_table(wp["stats"], color_cols={"متوسط زيارات/يوم عمل": "#2DD4BF"}, height=340)

    # ── Note quality (design places it on this page) ──
    section("جودة الملاحظات لكل مندوب", "NOTE QUALITY")
    nq = note_quality(classified)
    if not nq.empty:
        html_table(nq,
                   cond_colors={"ملاحظات فارغة %": lambda v: "#F08080" if float(v) >= 30 else ("#FFC000" if float(v) >= 10 else "#70AD47")},
                   height=320)
        st.caption("الملاحظات المنسوخة = ملاحظات متطابقة حرفياً لنفس المندوب (مؤشر تسجيل شكلي)")

    # Monthly trend with filters (إضافي — ليس ضمن التصميم)
    section("الزيارات الشهرية لكل مندوب", "MONTHLY TREND")
    if "Visit Date" in classified.columns:
        df_m = classified.copy()
        df_m["Visit Date"] = pd.to_datetime(df_m["Visit Date"], errors="coerce")

        fl1,fl2,fl3,fl4 = st.columns(4)
        years_avail  = sorted(df_m["Visit Date"].dt.year.dropna().unique().astype(int).tolist())
        months_map   = {1:"يناير",2:"فبراير",3:"مارس",4:"أبريل",5:"مايو",6:"يونيو",
                        7:"يوليو",8:"أغسطس",9:"سبتمبر",10:"أكتوبر",11:"نوفمبر",12:"ديسمبر"}
        months_avail = sorted(df_m["Visit Date"].dt.month.dropna().unique().astype(int).tolist())
        days_avail   = sorted(df_m["Visit Date"].dt.day.dropna().unique().astype(int).tolist())
        reps_avail   = sorted(df_m["Sales Rep Name"].dropna().unique().tolist())

        with fl1: sel_y = st.multiselect("السنة",    years_avail,  default=years_avail,  key="rt_y")
        with fl2: sel_m = st.multiselect("الشهر",    months_avail, default=months_avail,
                                          format_func=lambda x: f"{months_map[x]} ({x})", key="rt_m")
        with fl3: sel_d = st.multiselect("اليوم",    days_avail,   default=days_avail,   key="rt_d")
        with fl4: sel_r = st.multiselect("المندوب",  reps_avail,   default=reps_avail,   key="rt_r")

        mask = (df_m["Visit Date"].dt.year.isin(sel_y)  &
                df_m["Visit Date"].dt.month.isin(sel_m) &
                df_m["Visit Date"].dt.day.isin(sel_d)   &
                df_m["Sales Rep Name"].isin(sel_r))
        df_mf = df_m[mask].copy()

        if df_mf.empty:
            st.warning("لا توجد بيانات بهذه الفلاتر")
        else:
            st.info(f"📊 زيارات: **{len(df_mf):,}** | عملاء: **{df_mf['Customer Name'].nunique():,}**")
            df_mf["Month_Period"] = df_mf["Visit Date"].dt.to_period("M").astype(str)
            monthly_rep = df_mf.groupby(["Month_Period","Sales Rep Name"]).size().reset_index(name="Visits")

            fig_ml = px.line(monthly_rep, x="Month_Period", y="Visits", color="Sales Rep Name",
                             markers=True, template="wdi_dark",
                             title="الزيارات الشهرية لكل مندوب", text="Visits")
            fig_ml.update_traces(textposition="top center")
            fig_ml.update_layout(paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h",y=-0.3),
                                 xaxis_tickangle=-45, margin=dict(l=20,r=20,t=50,b=100))
            st.plotly_chart(fig_ml, use_container_width=True)

            with st.expander("📋 الجدول التفصيلي"):
                pivot = monthly_rep.pivot_table(index="Month_Period", columns="Sales Rep Name",
                                                values="Visits", fill_value=0).reset_index()
                pivot["الإجمالي"] = pivot.iloc[:,1:].sum(axis=1)
                st.dataframe(pivot, use_container_width=True, hide_index=True)

    section("تصدير")
    st.download_button("⬇️ Sales Rep KPI.xlsx",
                       data=export_sales_rep_kpi(rep_kpi_df),
                       file_name="Sales_Rep_KPI.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════════════════════════
# PAGE 5 — EXECUTIVE DASHBOARD
# ═══════════════════════════════════════════════════════════════════

elif page == "لوحة التحكم التنفيذية":

    if not st.session_state["processing_done"]:
        page_banner("لوحة التحكم التنفيذية", "EXECUTIVE DASHBOARD", PAGE_ACCENT["exec"])
        no_data_warning(); st.stop()

    view = get_view()
    exec_data  = view["exec"]
    journey_df = view["journey"]
    rep_kpi_df = view["rep_kpi"]
    kpis = exec_data.get("kpis", {})

    rng = st.session_state.get("date_range")
    period_label = f"{str(rng[0])[:10]} ← {str(rng[1])[:10]}" if rng else "كل البيانات"
    page_banner("لوحة التحكم التنفيذية", "EXECUTIVE DASHBOARD", PAGE_ACCENT["exec"],
                right_html=(f"<div>الفترة: <span style='color:#E6EDF3'>{period_label}</span></div>"
                            f"<div>{fmt_number(len(view['classified']))} زيارة · "
                            f"{fmt_number(journey_df['Customer Name'].nunique() if not journey_df.empty else 0)} عميل</div>"))

    # ── KPI cards (design: 8 Arabic cards with accents) ──
    _KPI_SPEC = [
        ("إجمالي الزيارات", "TOTAL VISITS",   "Total Visits",        "#2DD4BF"),
        ("عملاء فريدون",    "UNIQUE",         "Unique Customers",    "#4C9AFF"),
        ("حاليون",          "CURRENT",        "Current Customers",   "#70AD47"),
        ("مستهدفون",        "TARGET",         "Target Customers",    "#FFC000"),
        ("محتملون",         "POTENTIAL",      "Potential Customers", "#2E75B6"),
        ("جدد",             "NEW",            "New Customers",       "#8FB4D9"),
        ("سابقون",          "FORMER",         "Former Customers",    "#A9A9A9"),
        ("غير مهتمين",      "NOT INTERESTED", "Not Interested",      "#F08080"),
    ]
    stat_cards([{"label": ar, "en": en, "value": fmt_number(kpis.get(key, 0)), "accent": acc}
                for ar, en, key, acc in _KPI_SPEC], cols=4)

    # ── Month-over-month comparison ──
    funnel_pre = exec_data.get("funnel", {})
    cmp = period_comparison(view["classified"], funnel_pre.get("transitions", pd.DataFrame()))
    if cmp["metrics"]:
        section(f"مقارنة شهرية — {cmp['cur_label']} مقابل {cmp['prev_label']}", "MONTH OVER MONTH")
        _cmp_items = []
        for label, cur, prev in cmp["metrics"]:
            d = int(cur - prev)
            dt = ("▲ +" if d > 0 else "▼ " if d < 0 else "— ") + fmt_number(abs(d))
            dc = "#70AD47" if d > 0 else "#F08080" if d < 0 else "#566573"
            _cmp_items.append({"label": label, "value": fmt_number(cur), "delta": (dt, dc)})
        stat_cards(_cmp_items, cols=7)

    section("تريند الزيارات الشهري", "MONTHLY VISIT TREND")
    if exec_data.get("fig_trend"): st.plotly_chart(exec_data["fig_trend"], use_container_width=True)

    cl, cr = st.columns(2)
    with cl:
        section("توزيع حالات العملاء")
        if exec_data.get("fig_status_pie"): st.plotly_chart(exec_data["fig_status_pie"], use_container_width=True)
    with cr:
        section("ترتيب المندوبين")
        if exec_data.get("fig_rep_ranking"): st.plotly_chart(exec_data["fig_rep_ranking"], use_container_width=True)

    cg, cd = st.columns(2)
    with cg:
        section("توزيع المحافظات")
        if exec_data.get("fig_gov"): st.plotly_chart(exec_data["fig_gov"], use_container_width=True)
    with cd:
        section("توزيع المناطق")
        if exec_data.get("fig_district"): st.plotly_chart(exec_data["fig_district"], use_container_width=True)

    section("أكثر 20 عميلاً زيارةً", "TOP 20 CUSTOMERS")
    top_c = exec_data.get("top_customers_df", pd.DataFrame())
    if not top_c.empty:
        html_table(top_c.reset_index(drop=True), badge_cols=("Latest Status",),
                   color_cols={"Visit Count": "#2DD4BF"}, height=350, index_col=True)

    # ── Funnel: customer transitions ──
    funnel = exec_data.get("funnel", {})
    section("تحوّلات العملاء", "CUSTOMER FUNNEL")
    conv_df  = funnel.get("conversions", pd.DataFrame())
    churn_df = funnel.get("churn", pd.DataFrame())
    trans_df = funnel.get("transitions", pd.DataFrame())

    ret = conversion_retention(conv_df, journey_df)
    avg_days = conv_df["Days To Convert"].mean() if ("Days To Convert" in conv_df.columns and not conv_df.empty) else None

    stat_cards([
        {"label": "إجمالي التحوّلات",      "value": fmt_number(len(trans_df))},
        {"label": "تحوّلوا إلى عميل حالي", "value": fmt_number(len(conv_df)),  "color": "#70AD47"},
        {"label": "متوسط أيام التحويل",    "value": f"{avg_days:.0f} يوم" if pd.notnull(avg_days) else "—"},
        {"label": "معدل بقاء المحوّلين",   "value": f"{ret['retention_pct']}%" if ret["retention_pct"] is not None else "—", "color": "#2DD4BF"},
        {"label": "عملاء متسربون",         "value": fmt_number(len(churn_df)), "color": "#F08080"},
    ], cols=5)

    if not ret["lost_after_conversion"].empty:
        with st.expander(f"⚠️ عملاء تحوّلوا لحاليين ثم فُقدوا ({len(ret['lost_after_conversion'])})"):
            st.dataframe(ret["lost_after_conversion"], use_container_width=True)

    if not trans_df.empty:
        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown("**مصفوفة التحوّل (من ← إلى)**")
            _mx = funnel.get("matrix", pd.DataFrame())
            if not _mx.empty:
                matrix_table(_mx, index_label="من ↓ / إلى ←", height=300)
        with fc2:
            st.markdown("**تحويلات لعميل حالي على يد كل مندوب**")
            if funnel.get("fig_rep_conversions") is not None:
                st.plotly_chart(funnel["fig_rep_conversions"], use_container_width=True)

        if not conv_df.empty:
            with st.expander(f"👀 تفاصيل العملاء المتحوّلين إلى (حالي) — {len(conv_df):,} عميل"):
                show_conv = conv_df.copy()
                for dc in ["Transition Date", "First Visit Date"]:
                    if dc in show_conv.columns:
                        show_conv[dc] = pd.to_datetime(show_conv[dc], errors="coerce").dt.strftime("%Y-%m-%d")
                st.dataframe(show_conv, use_container_width=True, height=320)

    # ── Churn: rescue list ──
    section("📉 عملاء متسربون (كانوا حاليين وتوقفوا)")
    if churn_df.empty:
        st.success("✅ لا يوجد عملاء متسربون")
    else:
        st.error(f"🚨 {len(churn_df)} عميل كان يتعامل معنا وآخر حالته الآن (سابق / غير مهتم) — قائمة إنقاذ")
        show_churn = churn_df.copy()
        if "Last Visit Date" in show_churn.columns:
            show_churn["Last Visit Date"] = pd.to_datetime(show_churn["Last Visit Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        html_table(show_churn.reset_index(drop=True), badge_cols=("Latest Status",),
                   color_cols={"Days Since Last Visit": "#F08080"}, height=320)
        out_churn = io.BytesIO()
        with pd.ExcelWriter(out_churn, engine="openpyxl") as w:
            show_churn.to_excel(w, index=False, sheet_name="Churned Customers")
        st.download_button("⬇️ تصدير قائمة المتسربين Excel",
                           data=out_churn.getvalue(),
                           file_name="Churned_Customers.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    section("تصدير")
    e1,e2 = st.columns(2)
    with e1:
        summary_dict = {"kpis":kpis,"monthly":exec_data.get("monthly_df",pd.DataFrame()),
                        "status_dist":exec_data.get("status_dist_df",pd.DataFrame()),
                        "gov_dist":exec_data.get("gov_dist_df",pd.DataFrame()),
                        "top_customers":exec_data.get("top_customers_df",pd.DataFrame())}
        st.download_button("⬇️ Executive Dashboard.xlsx",
                           data=export_executive_dashboard(summary_dict),
                           file_name="Executive_Dashboard.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    with e2:
        journey_clean = journey_df.drop(columns=["_journey"],errors="ignore")
        if not journey_clean.empty:
            st.download_button("⬇️ Customer Summary.xlsx",
                               data=export_customer_summary(journey_clean),
                               file_name="Customer_Summary.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)

    # ── Comprehensive monthly report ──
    with st.expander("📑 التقرير الشهري الشامل (كل الأقسام في ملف واحد)"):
        st.markdown("ملف Excel واحد جاهز للاجتماع: مقارنة شهرية، التحويلات، المتسربون، الوعود المستحقة، أولويات الزيارة، المنافسون، وترتيب المندوبين.")
        if st.button("⚙️ تجهيز التقرير", key="gen_monthly_report"):
            with st.spinner("📑 تجهيز التقرير الشامل..."):
                vi = view_insights(view)
                promises_df = vi["promises"]
                due = promises_df[promises_df["حالة الوعد"] == "🔥 مستحق الآن"] if not promises_df.empty else pd.DataFrame()
                report_bytes = export_monthly_report(cmp, {
                    "التحويلات لعميل حالي": funnel_pre.get("conversions", pd.DataFrame()),
                    "العملاء المتسربون":    funnel_pre.get("churn", pd.DataFrame()),
                    "الوعود المستحقة":      due,
                    "أولويات الزيارة":      vi["nbv"].head(150),
                    "المنافسون":            vi["competitors"]["by_competitor"],
                    "ترتيب المندوبين":      rep_kpi_df,
                })
                st.session_state["_monthly_report"] = report_bytes
        if st.session_state.get("_monthly_report"):
            st.download_button("⬇️ تحميل التقرير الشهري الشامل.xlsx",
                               data=st.session_state["_monthly_report"],
                               file_name="WDI_Monthly_Report.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE — ACTION CENTER (خطة المتابعة)
# ═══════════════════════════════════════════════════════════════════

elif page == "خطة المتابعة":
    page_banner("خطة المتابعة", "ACTION CENTER — أولويات الزيارة والوعود المستحقة", PAGE_ACCENT["action"])

    if not st.session_state["processing_done"]:
        no_data_warning(); st.stop()

    view = view_insights(get_view())
    nbv_df      = view["nbv"]
    promises_df = view["promises"]

    due_now   = promises_df[promises_df["حالة الوعد"] == "🔥 مستحق الآن"] if not promises_df.empty else pd.DataFrame()
    followed  = promises_df[promises_df["حالة الوعد"] == "🔁 تمت متابعته"] if not promises_df.empty else pd.DataFrame()
    hot       = nbv_df[nbv_df["أولوية الزيارة"] >= 50] if not nbv_df.empty else pd.DataFrame()

    stat_cards([
        {"label": "أولويات عاجلة",     "value": fmt_number(len(hot)),         "color": "#F08080"},
        {"label": "وعود مسجّلة",       "value": fmt_number(len(promises_df))},
        {"label": "وعود مستحقة الآن",  "value": fmt_number(len(due_now)),     "color": "#FFC000"},
        {"label": "وعود تمت متابعتها", "value": fmt_number(len(followed)),    "color": "#70AD47"},
    ], cols=4)

    # ── Filters ──
    pf1, pf2 = st.columns(2)
    with pf1:
        reps_all = ["الكل"] + sorted([r for r in nbv_df["Sales Rep Name"].dropna().unique() if r]) if not nbv_df.empty else ["الكل"]
        sel_rep_p = st.selectbox("المندوب", reps_all, key="ac_rep")
    with pf2:
        govs_all = ["الكل"] + sorted([g for g in nbv_df["Governorate"].dropna().unique() if g]) if not nbv_df.empty else ["الكل"]
        sel_gov_p = st.selectbox("المحافظة", govs_all, key="ac_gov")

    def _pfilter(df):
        if df.empty: return df
        out = df
        if sel_rep_p != "الكل" and "Sales Rep Name" in out.columns:
            out = out[out["Sales Rep Name"] == sel_rep_p]
        if sel_gov_p != "الكل" and "Governorate" in out.columns:
            out = out[out["Governorate"] == sel_gov_p]
        return out

    # ── Section 1: Next Best Visit ──
    section("أولويات الزيارة القادمة", "NEXT BEST VISITS")
    st.markdown("ترتيب ذكي: وعود مستحقة، محتملون قريبون من القرار، متسربون للإنقاذ، وعملاء حاليون في خطر.")
    nbv_f = _pfilter(nbv_df)
    top_n = st.slider("عدد العملاء المعروضين", 10, 200, 40, 10, key="ac_topn")
    show_nbv = nbv_f.head(top_n)
    _nbv_cols = [c for c in ["Customer Name", "أولوية الزيارة", "Latest Status",
                             "سبب الأولوية", "Sales Rep Name", "Governorate"]
                 if c in show_nbv.columns]
    html_table(show_nbv[_nbv_cols].reset_index(drop=True),
               badge_cols=("Latest Status",),
               color_cols={"أولوية الزيارة": "#F08080"}, height=460, index_col=True)
    if not show_nbv.empty:
        _xlsx_download(show_nbv, "⬇ تصدير خطة الزيارات Excel", "Visit_Priority_Plan.xlsx", key="dl_nbv")

    # ── Section 2: Promise tracker ──
    section("الوعود المسجّلة في الملاحظات", "PROMISES TRACKER")
    st.markdown("وعود مستخرجة تلقائياً من ملاحظات الزيارات (تجربة، بدء بعد الدورة، ميعاد متفق عليه...).")
    if promises_df.empty:
        st.info("لا توجد وعود مستخرجة من الملاحظات")
    else:
        pstates = ["الكل"] + promises_df["حالة الوعد"].unique().tolist()
        sel_pstate = st.selectbox("حالة الوعد", pstates, key="ac_pstate")
        prom_f = _pfilter(promises_df)
        if sel_pstate != "الكل":
            prom_f = prom_f[prom_f["حالة الوعد"] == sel_pstate]
        show_p = prom_f.copy()
        show_p["تاريخ الوعد"] = pd.to_datetime(show_p["تاريخ الوعد"], errors="coerce").dt.strftime("%Y-%m-%d")
        _p_cols = [c for c in ["Customer Name", "نوع الوعد", "تاريخ الوعد",
                               "حالة الوعد", "الحالة الحالية", "Sales Rep Name"]
                   if c in show_p.columns]

        def _pstate_color(v):
            s = str(v)
            return ("#F08080" if "مستحق" in s else
                    "#70AD47" if "تحول" in s else
                    "#4C9AFF" if "متابع" in s else "#FFC000")

        st.info(f"🤝 {len(show_p):,} وعد")
        html_table(show_p[_p_cols].reset_index(drop=True),
                   cond_colors={"حالة الوعد": _pstate_color}, height=420)
        if not show_p.empty:
            _xlsx_download(prom_f, "⬇ تصدير الوعود Excel", "Promise_Tracker.xlsx", key="dl_prom")


# ═══════════════════════════════════════════════════════════════════
# PAGE — COMPETITORS (المنافسون)
# ═══════════════════════════════════════════════════════════════════

elif page == "المنافسون":
    page_banner("المنافسون", "COMPETITORS — رصد ذِكر الموردين المنافسين في ملاحظات الزيارة", PAGE_ACCENT["comp"])

    if not st.session_state["processing_done"]:
        no_data_warning(); st.stop()

    view = view_insights(get_view())
    comp = view["competitors"]
    mentions = comp["mentions"]

    if mentions.empty:
        st.info("لا توجد إشارات لمنافسين في الملاحظات")
        st.stop()

    losing = comp["losing_to"]

    # ── Top row: losing-to table (left) | top competitors chart (right) ──
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        section("عملاء نخسرهم لمنافس", "LOSING TO")
        if losing.empty:
            st.success("لا يوجد")
        else:
            show_l = losing[["المنافس", "Customer Name", "الحالة الحالية", "Governorate"]].head(60).copy()
            show_l.columns = ["المنافس", "العميل", "الحالة", "المحافظة"]
            html_table(show_l, color_cols={"المنافس": "#F08080"}, height=390)
    with cc2:
        section("أكثر المنافسين ذِكراً", "TOP COMPETITORS")
        if comp["fig_competitors"] is not None:
            st.plotly_chart(comp["fig_competitors"], use_container_width=True)

    # ── Full-width matrix ──
    section("مصفوفة المنافسين حسب المحافظة", "TOP 10")
    if not comp["by_gov_matrix"].empty:
        matrix_table(comp["by_gov_matrix"], index_label="المحافظة", height=520)

    if not losing.empty:
        show_export = losing.copy()
        if "Visit Date" in show_export.columns:
            show_export["Visit Date"] = pd.to_datetime(show_export["Visit Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        _xlsx_download(show_export, "⬇ تصدير قائمة العملاء المهددين Excel", "Losing_To_Competitors.xlsx", key="dl_lose")


# ═══════════════════════════════════════════════════════════════════
# PAGE — CUSTOMER 360 (عميل 360)
# ═══════════════════════════════════════════════════════════════════

elif page == "عميل 360":
    page_banner("عميل 360", "CUSTOMER 360 — سجل الزيارات الكامل لعميل واحد", PAGE_ACCENT["c360"])

    if not st.session_state["processing_done"]:
        no_data_warning(); st.stop()

    view = view_insights(get_view())
    classified_df = view["classified"]
    journey_df    = view["journey"]

    search360 = st.text_input("🔍 ابحث باسم العميل", key="c360_search")
    names = journey_df["Customer Name"].tolist() if not journey_df.empty else []
    if search360.strip():
        norm_q = search360.strip()
        names = [n for n in names if norm_q in str(n)]
    if not names:
        st.warning("لا توجد نتائج — جرّب جزءاً من الاسم")
        st.stop()

    sel360 = st.selectbox("اختر العميل", names, key="c360_sel")
    jrow = journey_df[journey_df["Customer Name"] == sel360].iloc[0]
    cust_v = classified_df[classified_df["Customer Name"] == sel360].sort_values("Visit Date")

    # ── Header cards (design) ──
    _fv = str(pd.to_datetime(jrow.get("First Visit Date"), errors="coerce"))[:10]
    _lv = str(pd.to_datetime(jrow.get("Last Visit Date"), errors="coerce"))[:10]
    stat_cards([
        {"label": "الحالة الأخيرة", "value": STATUS_AR.get(jrow["Latest Status"], jrow["Latest Status"]),
         "color": STATUS_COLORS.get(jrow["Latest Status"], "#E6EDF3")},
        {"label": "عدد الزيارات", "value": fmt_number(int(jrow["Visit Count"])), "color": "#2DD4BF"},
        {"label": "أول زيارة", "value": _fv if _fv != "NaT" else "—"},
        {"label": "آخر زيارة", "value": _lv if _lv != "NaT" else "—"},
        {"label": "المحافظة", "value": jrow.get("Governorate") or "—"},
    ], cols=5)

    # ── Alerts for this customer ──
    promises_df = view["promises"]
    my_prom = promises_df[promises_df["Customer Name"] == sel360] if not promises_df.empty else pd.DataFrame()
    if not my_prom.empty:
        p = my_prom.iloc[0]
        st.warning(f"🤝 وعد نشط: **{p['نوع الوعد']}** منذ {int(p['أيام منذ الوعد'])} يوم — الحالة: {p['حالة الوعد']}")
    my_comp = view["competitors"]["mentions"]
    my_comp = my_comp[my_comp["Customer Name"] == sel360] if not my_comp.empty else pd.DataFrame()
    if not my_comp.empty:
        st.error("🥊 مرتبط بمنافس: " + "، ".join(sorted(my_comp["المنافس"].unique())))

    # ── Visit timeline (design-styled) ──
    section("الخط الزمني للزيارات", "VISIT TIMELINE")
    tl = cust_v.sort_values("Visit Date", ascending=False).copy()
    items = ""
    for _, r in tl.iterrows():
        status = str(r.get("Display Status", "Unclassified"))
        dot = STATUS_COLORS.get(status, "#8B98A5")
        date_s = str(pd.to_datetime(r.get("Visit Date"), errors="coerce"))[:10]
        conf = r.get("Confidence Score", 0)
        rep = _html.escape(str(r.get("Sales Rep Name", "") or "—"))
        note = _html.escape(str(r.get("Visit Notes", "") or ""))
        items += f"""
        <div style="display:flex;gap:14px;padding:12px 4px;border-bottom:1px solid #1A222B">
            <div style="min-width:86px;font-size:11px;color:#566573;padding-top:2px">{date_s}</div>
            <div style="width:9px;height:9px;border-radius:50%;background:{dot};margin-top:6px;flex-shrink:0"></div>
            <div style="flex:1">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px">
                    {badge(status)}
                    <span style="font-size:10.5px;color:#566573">ثقة {conf:.0f}% · {rep}</span>
                </div>
                <div style="font-size:12.5px;color:#C6D0DA;line-height:1.7">{note}</div>
            </div>
        </div>"""
    st.markdown(
        f'<div class="section-card" style="max-height:500px;overflow-y:auto;direction:rtl">{items}</div>',
        unsafe_allow_html=True)

    # ── All visits (export) ──
    vcols = ["Visit Date", "Sales Rep Name", "Display Status", "Confidence Score",
             "Visit Notes", "Matched Keywords", "Override Source"]
    vcols = [c for c in vcols if c in cust_v.columns]
    show_v = cust_v[vcols].copy()
    show_v["Visit Date"] = pd.to_datetime(show_v["Visit Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    _xlsx_download(show_v, "⬇️ تصدير ملف العميل Excel", f"Customer_360.xlsx", key="dl_c360")


# ═══════════════════════════════════════════════════════════════════
# PAGE — DATA & ENGINE QUALITY (جودة البيانات والمحرك)
# ═══════════════════════════════════════════════════════════════════

elif page == "جودة البيانات والمحرك":
    page_banner("جودة البيانات والمحرك", "DATA & ENGINE QUALITY — فحص اكتمال البيانات وتغطية المحرك", PAGE_ACCENT["quality"])

    if not st.session_state["processing_done"]:
        no_data_warning(); st.stop()

    master_df = st.session_state["classified_df"]

    # ── Data health (design: percent-based colored KPIs) ──
    dq = data_quality_summary(master_df)
    _pct = lambda n: f"{n / max(1, dq['total']) * 100:.1f}%"
    stat_cards([
        {"label": "إجمالي السجلات", "value": fmt_number(dq["total"])},
        {"label": "بلا مندوب",      "value": _pct(dq["no_rep"]),
         "color": "#FFC000" if dq["no_rep"] else "#70AD47"},
        {"label": "بلا محافظة",     "value": _pct(dq["no_gov"]),
         "color": "#FFC000" if dq["no_gov"] else "#70AD47"},
        {"label": "بلا ملاحظة",     "value": _pct(dq["no_note"]),
         "color": "#F08080" if dq["no_note"] else "#70AD47"},
        {"label": "تكرارات مطابقة", "value": fmt_number(dq["exact_dups"]),
         "color": "#F08080" if dq["exact_dups"] else "#70AD47"},
    ], cols=5)
    if dq["no_rep"] > dq["total"] * 0.1:
        st.warning(f"⚠️ **{dq['no_rep']:,}** زيارة ({dq['no_rep']/max(1,dq['total'])*100:.0f}%) بدون اسم مندوب — راجع ملف المصدر، هذه الزيارات لا تُحسب لأي مندوب في التقارير.")

    # ── Engine accuracy vs manual ──
    section("🎯 دقة المحرك مقابل التصنيف اليدوي")
    st.markdown("يُعاد تصنيف الزيارات المصنفة يدوياً بالمحرك الحالي وتُقارن النتيجة بقرار الموظف.")
    if st.button("▶️ تشغيل القياس", key="run_agreement"):
        with st.spinner("قياس التطابق..."):
            st.session_state["_agreement"] = engine_agreement(master_df)
    agr = st.session_state.get("_agreement")
    if agr and "engine_blind" not in agr:
        agr = None  # stale result from an older app version
    if agr and agr["n"]:
        a1, a2, a3 = st.columns(3)
        a1.metric("زيارات مصنفة يدوياً", fmt_number(agr["n"]))
        a2.metric("المحرك بلا رأي فيها", fmt_number(agr["engine_blind"]),
                  help="زيارات لا تطابق أي قاعدة كلمات — لهذا صُنفت يدوياً. كلما أضفت قواعد جديدة انخفض هذا الرقم")
        a3.metric("التطابق حيث للمحرك رأي",
                  f"{agr['agreement']}%" if agr["agreement"] is not None else "—",
                  help=f"مقارنة على {agr['n_opinion']} زيارة يستطيع المحرك تصنيفها")
        if not agr["confusion"].empty:
            st.markdown("**مصفوفة المقارنة (صفوف: قرار الموظف — أعمدة: قرار المحرك)**")
            st.dataframe(agr["confusion"], use_container_width=True)
        if not agr["samples"].empty:
            with st.expander(f"أمثلة على الاختلاف ({len(agr['samples'])})"):
                st.dataframe(agr["samples"], use_container_width=True, height=320)

    # ── Rule suggestions from unclassified ──
    section("💡 عبارات مرشحة لقواعد جديدة")
    st.markdown("أكثر العبارات تكراراً في الزيارات **غير المصنفة أو ضعيفة الثقة** — أضفها كقواعد من تبويب (قواعد الكلمات).")
    phrases = unclassified_phrases(master_df)
    if phrases.empty:
        st.success("✅ لا توجد عبارات متكررة غير مغطاة — المحرك يغطي البيانات الحالية جيداً")
    else:
        chips = "".join(
            f'<span class="wdi-chip">{_html.escape(str(r["العبارة"]))} <b>×{r["التكرار"]}</b></span>'
            for _, r in phrases.iterrows())
        st.markdown(f'<div class="section-card" style="direction:rtl">{chips}</div>',
                    unsafe_allow_html=True)

    # ── Completeness detail grid (design) ──
    section("إحصائيات الاكتمال", "COMPLETENESS")
    from classification_engine import ACTIVE_RULES as _RULES
    _details = [
        ("بلا تاريخ", fmt_number(dq["no_date"])),
        ("بلا مندوب (عدد)", fmt_number(dq["no_rep"])),
        ("بلا محافظة (عدد)", fmt_number(dq["no_gov"])),
        ("بلا ملاحظة (عدد)", fmt_number(dq["no_note"])),
        ("تكرارات مطابقة (عدد)", fmt_number(dq["exact_dups"])),
        ("إجمالي قواعد المحرك", fmt_number(len(_RULES))),
    ]
    _dcards = "".join(
        f'<div style="background:#10171D;border:1px solid #1D262F;border-radius:8px;'
        f'padding:11px 14px;display:flex;justify-content:space-between;align-items:center">'
        f'<span style="font-size:12px;color:#8B98A5">{lbl}</span>'
        f'<span style="font-size:15px;font-weight:700;color:#E6EDF3">{val}</span></div>'
        for lbl, val in _details)
    st.markdown(f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;direction:rtl">{_dcards}</div>',
                unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 6 — SETTINGS
# ═══════════════════════════════════════════════════════════════════

elif page == "الإعدادات":
    page_banner("الإعدادات", "SETTINGS — إعداد مسار البيانات المشتركة وإدارة التخزين", PAGE_ACCENT["settings"])

    status = storage_status()

    # ── Storage Path ──
    section("📁 مسار البيانات المشتركة")
    st.markdown("""
    ضع مسار الـ Shared Folder هنا — كل المستخدمين على الشبكة سيرون نفس البيانات.
    """)

    current_path = status["data_dir"]
    new_path = st.text_input(
        "مسار الفولدر المشترك",
        value=current_path,
        placeholder=r"مثال: \\SERVER\WDI_Analytics\data أو Z:\WDI_Data",
        help="يجب أن يكون الفولدر قابلاً للكتابة من كل الأجهزة",
    )

    col_save, col_test = st.columns(2)
    with col_save:
        if st.button("💾 حفظ المسار", use_container_width=True):
            ok, msg = set_data_dir(new_path)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    with col_test:
        if st.button("🔍 اختبار الوصول", use_container_width=True):
            from pathlib import Path
            try:
                p = Path(new_path)
                if p.exists() and p.is_dir():
                    test = p / ".test_access"
                    test.write_text("ok"); test.unlink()
                    st.success(f"✅ الفولدر موجود وقابل للكتابة")
                else:
                    st.error("❌ الفولدر غير موجود")
            except Exception as e:
                st.error(f"❌ لا يمكن الوصول: {e}")

    # ── Storage Status ──
    section("📊 حالة التخزين")
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("الفولدر موجود",  "✅" if status["dir_exists"]   else "❌")
    s2.metric("قابل للكتابة",  "✅" if status["dir_writable"] else "❌")
    s3.metric("توجد بيانات",   "✅" if status["has_data"]     else "❌")
    s4.metric("حجم البيانات",  f"{status['total_size_kb']} KB")

    meta = status["metadata"]
    if meta:
        st.markdown(f"""
        <div class="section-card">
        <b>📋 آخر بيانات محفوظة</b><br><br>
        📄 <b>الملف:</b> {meta.get('file_name','—')}<br>
        🗒️ <b>الزيارات:</b> {fmt_number(meta.get('total_records',0))}<br>
        👤 <b>العملاء:</b> {fmt_number(meta.get('unique_customers',0))}<br>
        🧑‍💼 <b>المندوبون:</b> {fmt_number(meta.get('unique_reps',0))}<br>
        ✏️ <b>تصنيفات يدوية:</b> {meta.get('override_count',0)}<br>
        💾 <b>آخر حفظ:</b> {meta.get('last_saved','—')}
        </div>""", unsafe_allow_html=True)

    # ── Manual Save ──
    section("💾 حفظ يدوي")
    if st.session_state["processing_done"]:
        if st.button("💾 حفظ البيانات الحالية الآن", use_container_width=True):
            ok, msg = save_session(
                classified_df=st.session_state["classified_df"],
                journey_df=st.session_state["journey_df"],
                rep_kpi_df=st.session_state["rep_kpi_df"],
                file_name=st.session_state.get("file_name",""),
            )
            if ok: st.success(msg)
            else:  st.error(msg)
    else:
        st.info("لا توجد بيانات محملة للحفظ")

    # ── Load Saved ──
    section("📂 تحميل البيانات المحفوظة")
    if has_saved_data():
        st.success("✅ توجد بيانات محفوظة جاهزة للتحميل")
        if st.button("📂 تحميل البيانات المحفوظة", use_container_width=True):
            ok, data = load_session()
            if ok and data:
                st.session_state["classified_df"] = data["classified_df"]
                st.session_state["journey_df"]    = data["journey_df"]
                st.session_state["rep_kpi_df"]    = data["rep_kpi_df"]
                st.session_state["file_name"]     = data["metadata"].get("file_name","")
                rebuild_dashboards()
                st.session_state["processing_done"] = True
                st.success("✅ تم تحميل البيانات بنجاح!")
                st.rerun()
            else:
                st.error(f"❌ فشل التحميل: {data.get('error','خطأ غير معروف')}")
    else:
        st.info("لا توجد بيانات محفوظة بعد")

    # ── Danger Zone ──
    section("⚠️ منطقة الخطر")
    with st.expander("🗑️ حذف البيانات"):
        st.warning("هذه العمليات لا يمكن التراجع عنها!")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if st.button("🗑️ حذف التصنيفات اليدوية فقط", use_container_width=True, type="secondary"):
                ok, msg = clear_overrides()
                st.success(msg) if ok else st.error(msg)
        with col_d2:
            if st.button("🗑️ حذف كل البيانات المحفوظة", use_container_width=True, type="secondary"):
                ok, msg = clear_all_data()
                if ok:
                    st.session_state["processing_done"] = False
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # ── How to Share ──
    section("📖 كيفية المشاركة على الشبكة", "NETWORK SHARING")
    _steps = [
        ("1 · على الجهاز الرئيسي", "python -m streamlit run app.py --server.address 0.0.0.0"),
        ("2 · اعرف IP الجهاز الرئيسي", "ipconfig → IPv4 Address → 192.168.1.5"),
        ("3 · على أي جهاز في نفس الشبكة", "http://192.168.1.5:8501"),
        ("4 · مسار الـ Shared Folder", r"\\SERVER\WDI_Analytics\data · Z:\WDI_Data"),
    ]
    _cards = "".join(
        f'''<div style="background:#10171D;border:1px solid #1D262F;border-radius:8px;padding:12px 14px">
            <div style="font-weight:700;color:#E6EDF3;margin-bottom:6px;font-size:12px">{t}</div>
            <code dir="ltr" style="display:block;background:#0A0E11;border-radius:6px;padding:8px 10px;font-size:11px;color:#2DD4BF;text-align:left;overflow-x:auto">{_html.escape(c)}</code>
        </div>''' for t, c in _steps)
    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;direction:rtl">{_cards}</div>',
        unsafe_allow_html=True)
