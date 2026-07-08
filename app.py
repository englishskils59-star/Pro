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
    export_followup_customers,
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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&display=swap');
:root {
    --primary:#1F4E79; --secondary:#2E75B6; --accent:#70AD47;
    --bg:#F5F7FA; --text:#1A1A2E; --card-bg:#FFFFFF; --border:#B8CCE4;
}
html,body,[class*="css"]{font-family:'Tajawal','Segoe UI',sans-serif!important;background-color:var(--bg)!important;color:var(--text)!important;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,var(--primary) 0%,var(--secondary) 100%)!important;}
[data-testid="stSidebar"] *{color:#FFFFFF!important;}
[data-testid="stSidebar"] .stRadio label{font-size:15px!important;padding:6px 0!important;}
[data-testid="metric-container"]{background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:16px 12px!important;box-shadow:0 2px 8px rgba(31,78,121,.08);}
[data-testid="metric-container"] [data-testid="stMetricLabel"]{font-size:13px!important;color:var(--secondary)!important;font-weight:600!important;}
[data-testid="metric-container"] [data-testid="stMetricValue"]{font-size:26px!important;color:var(--primary)!important;font-weight:700!important;}
h1{color:var(--primary)!important;font-weight:700!important;}
h2{color:var(--secondary)!important;}
h3{color:var(--primary)!important;}
.page-banner{background:linear-gradient(90deg,var(--primary) 0%,var(--secondary) 100%);color:#fff;padding:18px 28px;border-radius:12px;margin-bottom:24px;display:flex;align-items:center;gap:14px;}
.page-banner h1{color:#fff!important;margin:0!important;font-size:22px!important;}
.page-banner p{color:rgba(255,255,255,.85);margin:0!important;font-size:13px;}
.section-card{background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:20px 22px;margin-bottom:18px;box-shadow:0 2px 6px rgba(31,78,121,.06);}
hr{border-color:var(--border)!important;margin:18px 0!important;}
.stDownloadButton>button{background:var(--accent)!important;color:#fff!important;border:none!important;border-radius:8px!important;font-weight:600!important;padding:8px 20px!important;}
.stDownloadButton>button:hover{background:var(--primary)!important;}
.stButton>button{background:var(--secondary)!important;color:#fff!important;border:none!important;border-radius:8px!important;font-weight:600!important;}
[data-testid="stExpander"]{border:1px solid var(--border)!important;border-radius:8px!important;}
[data-testid="stFileUploader"]{border:2px dashed var(--secondary)!important;border-radius:10px!important;background:#EBF3FB!important;}
[data-baseweb="tab-list"]{border-bottom:2px solid var(--border)!important;}
[data-baseweb="tab"]{color:var(--secondary)!important;font-weight:600!important;}
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

def page_banner(icon, title, subtitle=""):
    st.markdown(f"""
    <div class="page-banner">
        <span style="font-size:32px">{icon}</span>
        <div><h1>{title}</h1>{'<p>'+subtitle+'</p>' if subtitle else ''}</div>
    </div>""", unsafe_allow_html=True)


def kpi_row(metrics: dict, cols_per_row: int = 4):
    items = list(metrics.items())
    rows  = [items[i:i+cols_per_row] for i in range(0, len(items), cols_per_row)]
    for row in rows:
        cols = st.columns(len(row))
        for col, (label, value) in zip(cols, row):
            with col:
                st.metric(label, fmt_number(value) if isinstance(value, (int, np.integer)) else value)


def no_data_warning():
    st.warning("⚠️ لا توجد بيانات. يرجى رفع ملف Excel من صفحة **Upload Center** أو تحميل البيانات المحفوظة.", icon="📂")


def section(title):
    st.markdown(f"<hr><h3>📌 {title}</h3>", unsafe_allow_html=True)


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
    <div style="text-align:center;padding:16px 0 24px">
        <div style="font-size:42px">📊</div>
        <div style="font-size:17px;font-weight:700;color:#fff;letter-spacing:.5px">WDI Analytics</div>
        <div style="font-size:11px;color:rgba(255,255,255,.7);margin-top:4px">Visit Analytics Engine v2.0</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio("Navigation", options=[
        "📂 Upload Center",
        "🧠 Customer Classification",
        "👥 Customer Analytics",
        "🏆 Sales Rep Performance",
        "🏢 Executive Dashboard",
        "⚙️ Settings",
    ], label_visibility="collapsed")

    st.markdown("---")

    if st.session_state["processing_done"]:
        classified_ = st.session_state.get("classified_df")
        journey_    = st.session_state.get("journey_df")
        meta = get_saved_metadata()

        # ── Global date filter (applies to all analytics pages) ──
        st.markdown("**📅 فلتر الفترة**")
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
                    f"<div style='background:rgba(255,192,0,.25);padding:6px 10px;border-radius:6px;font-size:12px'>"
                    f"🔎 الفلتر نشط: {str(_r[0])[:10]} → {str(_r[1])[:10]}</div>",
                    unsafe_allow_html=True)
        st.markdown("---")

        st.success("✅ البيانات محملة")
        st.markdown(f"""
        <div style="font-size:12px;color:rgba(255,255,255,.85)">
        📄 <b>{st.session_state.get('file_name','—')}</b><br>
        🗒️ {fmt_number(len(classified_)) if classified_ is not None else '0'} زيارة<br>
        👤 {fmt_number(classified_['Customer Name'].nunique()) if classified_ is not None else '0'} عميل<br>
        🧑‍💼 {fmt_number(classified_['Sales Rep Name'].nunique()) if classified_ is not None else '0'} مندوب<br>
        💾 آخر حفظ: {meta.get('last_saved','—')[:16] if meta.get('last_saved') else '—'}
        </div>""", unsafe_allow_html=True)

        if meta.get("override_count", 0) > 0:
            st.markdown(f"""
            <div style="margin-top:8px;background:rgba(112,173,71,.25);padding:6px 10px;border-radius:6px;font-size:12px">
            ✏️ {meta['override_count']} تصنيف يدوي محفوظ
            </div>""", unsafe_allow_html=True)
    else:
        st.info("📂 لا توجد بيانات")

    st.markdown("---")
    st.markdown(
        "<div style='font-size:10px;color:rgba(255,255,255,.4);text-align:center'>WDI Analytics v2.0<br>Fully Offline</div>",
        unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 1 — UPLOAD CENTER
# ═══════════════════════════════════════════════════════════════════

if page == "📂 Upload Center":
    page_banner("📂", "Upload Center", "رفع ملف Excel وتشغيل محرك التصنيف")

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
            col_df = pd.DataFrame({
                "العمود": REQUIRED_COLUMNS,
                "الحالة": ["✅ موجود" if c in present else "❌ ناقص" for c in REQUIRED_COLUMNS],
            })
            st.dataframe(col_df, use_container_width=True, hide_index=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if is_valid:
                if st.button("🚀 تشغيل التصنيف وحفظ البيانات", use_container_width=True):
                    uploaded.seek(0)
                    run_full_pipeline(raw_df, uploaded_file=uploaded)
                    st.success("✅ تم التصنيف والحفظ! يمكنك الآن التنقل بين الصفحات.")
                    st.balloons()
    else:
        st.markdown("""
        <div class="section-card" style="text-align:center;padding:48px">
            <div style="font-size:64px">📊</div>
            <h2 style="color:#1F4E79">WDI Visit Analytics Engine</h2>
            <p style="color:#555;max-width:500px;margin:0 auto 20px">
                ارفع ملف Excel لتصنيف الزيارات وتحليل أداء المندوبين تلقائياً — بدون إنترنت.
            </p>
        </div>""", unsafe_allow_html=True)

        with st.expander("📋 الأعمدة المطلوبة"):
            st.dataframe(pd.DataFrame({"الأعمدة المطلوبة": REQUIRED_COLUMNS}),
                         use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 2 — CUSTOMER CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════

elif page == "🧠 Customer Classification":
    page_banner("🧠", "تصنيف العملاء التلقائي", "محرك تصنيف بالكلمات المفتاحية — بدون AI")

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

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            reps_list = ["الكل"] + sorted(classified_df["Sales Rep Name"].dropna().unique().tolist())
            sel_rep = st.selectbox("المندوب", reps_list, key="cls_rep")
        with fc2:
            statuses_list = ["الكل"] + sorted(classified_df["Display Status"].dropna().unique().tolist())
            sel_status = st.selectbox("الحالة", statuses_list, key="cls_status")
        with fc3:
            min_conf = st.slider("أقل نسبة ثقة", 0, 100, 0, 5, key="cls_conf")

        filtered = classified_df.copy()
        if sel_rep    != "الكل": filtered = filtered[filtered["Sales Rep Name"] == sel_rep]
        if sel_status != "الكل": filtered = filtered[filtered["Display Status"]  == sel_status]
        filtered = filtered[filtered["Confidence Score"] >= min_conf]

        visit_counts = classified_df.groupby("Customer Name").size().reset_index(name="Visit Count")
        filtered = filtered.merge(visit_counts, on="Customer Name", how="left")

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
            show_cols = ["Visit Date","Customer Name","Sales Rep Name","Display Status",
                         "Visit Count","Confidence Score","Override Source",
                         "Matched Keywords","Classification Reason","Governorate"]
            show_cols = [c for c in show_cols if c in filtered.columns]
            st.info(f"📋 **{fmt_number(len(filtered))}** زيارة")
            st.dataframe(filtered[show_cols].reset_index(drop=True),
                         use_container_width=True, height=500)

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

elif page == "👥 Customer Analytics":
    page_banner("👥", "تحليلات العملاء", "تحليل شرائح العملاء وأنماط الزيارات")

    if not st.session_state["processing_done"]:
        no_data_warning(); st.stop()

    view = get_view()
    analytics  = view["analytics"]
    journey_df = view["journey"]
    kpis = analytics["kpi"]

    kpi_row({k:v for k,v in list(kpis.items())[:4]}, cols_per_row=4)
    kpi_row({k:v for k,v in list(kpis.items())[4:]}, cols_per_row=5)
    st.markdown("<br>", unsafe_allow_html=True)

    ch1, ch2 = st.columns(2)
    with ch1:
        if analytics.get("fig_status_pie"): st.plotly_chart(analytics["fig_status_pie"], use_container_width=True)
    with ch2:
        if analytics.get("fig_gov"):        st.plotly_chart(analytics["fig_gov"],        use_container_width=True)

    section("أكثر 20 عميلاً زيارةً")
    top20 = analytics.get("top_20", pd.DataFrame())
    if not top20.empty:
        st.dataframe(top20, use_container_width=True, height=380)
        fig_top = go.Figure(go.Bar(
            y=top20["Customer Name"], x=top20["Visit Count"],
            orientation="h", marker_color="#2E75B6",
            text=top20["Visit Count"], textposition="outside",
        ))
        fig_top.update_layout(title="Top 20", template="plotly_white",
                              paper_bgcolor="#F5F7FA", yaxis=dict(autorange="reversed"),
                              margin=dict(l=20,r=40,t=50,b=20), height=520)
        st.plotly_chart(fig_top, use_container_width=True)

    section("العملاء الذين لم تتم زيارتهم")
    nv_tabs = st.tabs(["30 يوم","60 يوم","90 يوم","180 يوم"])
    for tab_obj, days, key in zip(nv_tabs,[30,60,90,180],
                                   ["not_visited_30","not_visited_60","not_visited_90","not_visited_180"]):
        with tab_obj:
            df_nv = analytics.get(key, pd.DataFrame())
            if df_nv.empty:
                st.info(f"لا يوجد عملاء لم يُزاروا منذ {days} يوماً")
            else:
                st.warning(f"⚠️ {len(df_nv)} عميل لم يُزار منذ {days}+ يوم")
                st.dataframe(df_nv, use_container_width=True, height=320)
                xlsx_nv = export_followup_customers(journey_df, days_threshold=days)
                st.download_button(f"⬇️ تصدير قائمة {days} يوم",
                                   data=xlsx_nv, file_name=f"Followup_{days}_Days.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    section("توزيع المحافظات والمناطق")
    bd1, bd2 = st.columns(2)
    with bd1:
        gov_df = analytics.get("gov_dist_df", pd.DataFrame())
        if not gov_df.empty:
            st.markdown("**عملاء حسب المحافظة**")
            st.dataframe(gov_df, use_container_width=True, hide_index=True)
    with bd2:
        dist_df = analytics.get("district_dist_df", pd.DataFrame())
        if not dist_df.empty:
            st.markdown("**عملاء حسب المنطقة (أعلى 20)**")
            st.dataframe(dist_df.head(20), use_container_width=True, hide_index=True)

    section("تصدير")
    journey_clean = journey_df.drop(columns=["_journey"], errors="ignore")
    st.download_button("⬇️ Customer Summary.xlsx",
                       data=export_customer_summary(journey_clean),
                       file_name="Customer_Summary.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════════════════════════
# PAGE 4 — SALES REP PERFORMANCE
# ═══════════════════════════════════════════════════════════════════

elif page == "🏆 Sales Rep Performance":
    page_banner("🏆", "أداء المندوبين", "KPIs وتحليل مقارن وتريند شهري")

    if not st.session_state["processing_done"]:
        no_data_warning(); st.stop()

    view = get_view()
    rep_kpi_df  = view["rep_kpi"]
    rep_figures = view["rep_figs"]
    classified  = view["classified"]

    if rep_kpi_df is None or rep_kpi_df.empty:
        st.warning("لا توجد بيانات مندوبين"); st.stop()

    kpi_row({
        "عدد المندوبين":       len(rep_kpi_df),
        "إجمالي الزيارات":    int(rep_kpi_df["Total Visits"].sum()),
        # nunique on the full data — summing per-rep counts double-counts
        # customers visited by more than one rep
        "إجمالي العملاء":     int(classified["Customer Name"].nunique()),
        "متوسط التحويل":      f"{rep_kpi_df['Conversion Rate (%)'].mean():.1f}%",
    })
    st.markdown("<br>", unsafe_allow_html=True)

    section("جدول KPIs")
    st.info(f"🥇 أفضل مندوب: **{rep_kpi_df.iloc[0]['Sales Rep Name']}** — {fmt_number(rep_kpi_df.iloc[0]['Total Visits'])} زيارة")
    if "True Conversions" in rep_kpi_df.columns:
        best_conv = rep_kpi_df.sort_values("True Conversions", ascending=False).iloc[0]
        if best_conv["True Conversions"] > 0:
            st.success(f"⭐ أكثر مندوب تحويلاً لعملاء حاليين: **{best_conv['Sales Rep Name']}** — {int(best_conv['True Conversions'])} عميل تحوّل فعلياً")
    st.dataframe(rep_kpi_df.reset_index(drop=True), use_container_width=True, height=420)

    section("المخططات")
    for _, fig in rep_figures:
        st.plotly_chart(fig, use_container_width=True)

    # Monthly trend with filters
    section("الزيارات الشهرية لكل مندوب")
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
                             markers=True, template="plotly_white",
                             title="الزيارات الشهرية لكل مندوب", text="Visits")
            fig_ml.update_traces(textposition="top center")
            fig_ml.update_layout(paper_bgcolor="#F5F7FA", legend=dict(orientation="h",y=-0.3),
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

elif page == "🏢 Executive Dashboard":
    page_banner("🏢", "لوحة التحكم التنفيذية", "KPIs وتريند ورؤية استراتيجية")

    if not st.session_state["processing_done"]:
        no_data_warning(); st.stop()

    view = get_view()
    exec_data  = view["exec"]
    journey_df = view["journey"]
    rep_kpi_df = view["rep_kpi"]
    kpis = exec_data.get("kpis", {})
    kpi_items = list(kpis.items())

    c1,c2,c3,c4 = st.columns(4)
    for col,(label,val) in zip([c1,c2,c3,c4], kpi_items[:4]):
        with col: st.metric(label, fmt_number(val))
    if len(kpi_items) > 4:
        c5,c6,c7,c8 = st.columns(4)
        for col,(label,val) in zip([c5,c6,c7,c8], kpi_items[4:8]):
            with col: st.metric(label, fmt_number(val))

    st.markdown("<br>", unsafe_allow_html=True)
    section("تريند الزيارات الشهري")
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

    section("أكثر 20 عميلاً زيارةً")
    top_c = exec_data.get("top_customers_df", pd.DataFrame())
    if not top_c.empty: st.dataframe(top_c, use_container_width=True, height=340)

    section("⏰ عملاء يحتاجون متابعة (30+ يوم)")
    fu_df = exec_data.get("followup_df", pd.DataFrame())
    if not fu_df.empty:
        st.error(f"🚨 {len(fu_df)} عميل يحتاج متابعة")
        st.dataframe(fu_df, use_container_width=True, height=320)

    # ── Funnel: customer transitions ──
    funnel = exec_data.get("funnel", {})
    section("🔄 تحوّلات العملاء (Funnel)")
    conv_df  = funnel.get("conversions", pd.DataFrame())
    churn_df = funnel.get("churn", pd.DataFrame())
    trans_df = funnel.get("transitions", pd.DataFrame())

    fk1, fk2, fk3, fk4 = st.columns(4)
    fk1.metric("إجمالي التحوّلات", fmt_number(len(trans_df)))
    fk2.metric("تحوّلوا إلى عميل حالي", fmt_number(len(conv_df)))
    avg_days = conv_df["Days To Convert"].mean() if ("Days To Convert" in conv_df.columns and not conv_df.empty) else None
    fk3.metric("متوسط أيام التحويل", f"{avg_days:.0f} يوم" if pd.notnull(avg_days) else "—")
    fk4.metric("عملاء متسربون", fmt_number(len(churn_df)))

    if not trans_df.empty:
        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown("**مصفوفة التحوّل (من ← إلى) — عدد التحوّلات**")
            st.dataframe(funnel.get("matrix", pd.DataFrame()), use_container_width=True)
        with fc2:
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
        st.dataframe(show_churn, use_container_width=True, height=320)
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


# ═══════════════════════════════════════════════════════════════════
# PAGE 6 — SETTINGS
# ═══════════════════════════════════════════════════════════════════

elif page == "⚙️ Settings":
    page_banner("⚙️", "الإعدادات", "إعداد مسار البيانات المشتركة وإدارة التخزين")

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
    section("📖 كيفية المشاركة على الشبكة")
    st.markdown("""
    **خطوات تشغيل البرنامج على أكثر من جهاز:**

    **1. على الجهاز الرئيسي (اللي شغّل البرنامج):**
    ```
    python -m streamlit run app.py --server.address 0.0.0.0
    ```

    **2. اعرف IP الجهاز الرئيسي:**
    ```
    ipconfig  →  ابحث عن IPv4 Address  →  مثلاً: 192.168.1.5
    ```

    **3. على أي جهاز تاني في نفس الشبكة:**
    ```
    افتح المتصفح واكتب:  http://192.168.1.5:8501
    ```

    **4. مسار الـ Shared Folder:**
    ```
    ضع مسار فولدر مشترك يقدر يوصله كل الأجهزة
    مثال Windows: \\\\SERVER\\WDI_Analytics\\data
    مثال mapped drive: Z:\\WDI_Data
    ```
    """)
