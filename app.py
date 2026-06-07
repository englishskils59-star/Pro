# app.py
# WDI Visit Analytics Engine
# Main Streamlit application — 5 pages, fully offline, Arabic RTL support.
#
# Run with:  streamlit run app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from utils import (
    load_excel, validate_columns, clean_dataframe,
    basic_stats, fmt_number, fmt_pct, STATUS_COLORS, REQUIRED_COLUMNS,
)
from classification_engine import (
    classify_dataframe, build_customer_journey,
    customers_not_visited, get_rules_dataframe,
)
from dashboard import (
    customer_analytics_summary, sales_rep_kpi, executive_dashboard_data,
)
from export_manager import (
    export_customer_summary, export_sales_rep_kpi,
    export_executive_dashboard, export_classification_results,
    export_followup_customers,
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
# GLOBAL CSS  (Arabic RTL + corporate branding)
# ═══════════════════════════════════════════════════════════════════

st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&display=swap');

/* ── Root variables ── */
:root {
    --primary:   #1F4E79;
    --secondary: #2E75B6;
    --accent:    #70AD47;
    --bg:        #F5F7FA;
    --text:      #1A1A2E;
    --card-bg:   #FFFFFF;
    --border:    #B8CCE4;
}

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Tajawal', 'Segoe UI', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--primary) 0%, var(--secondary) 100%) !important;
}
[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 15px !important;
    padding: 6px 0 !important;
}

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 12px !important;
    box-shadow: 0 2px 8px rgba(31,78,121,0.08);
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    font-size: 13px !important;
    color: var(--secondary) !important;
    font-weight: 600 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 26px !important;
    color: var(--primary) !important;
    font-weight: 700 !important;
}

/* ── Headers ── */
h1 { color: var(--primary) !important; font-weight: 700 !important; }
h2 { color: var(--secondary) !important; }
h3 { color: var(--primary) !important; }

/* ── Page title banner ── */
.page-banner {
    background: linear-gradient(90deg, var(--primary) 0%, var(--secondary) 100%);
    color: #fff;
    padding: 18px 28px;
    border-radius: 12px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 14px;
}
.page-banner h1 {
    color: #fff !important;
    margin: 0 !important;
    font-size: 22px !important;
}
.page-banner p {
    color: rgba(255,255,255,0.85);
    margin: 0 !important;
    font-size: 13px;
}

/* ── Section cards ── */
.section-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px 22px;
    margin-bottom: 18px;
    box-shadow: 0 2px 6px rgba(31,78,121,0.06);
}

/* ── Status badges ── */
.badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    color: #fff;
}

/* ── Tables — RTL friendly ── */
[data-testid="stDataFrame"] {
    direction: ltr;
}

/* ── Dividers ── */
hr {
    border-color: var(--border) !important;
    margin: 18px 0 !important;
}

/* ── Buttons ── */
.stDownloadButton > button {
    background: var(--accent) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 8px 20px !important;
}
.stDownloadButton > button:hover {
    background: var(--primary) !important;
}
.stButton > button {
    background: var(--secondary) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

/* ── Upload area ── */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--secondary) !important;
    border-radius: 10px !important;
    background: #EBF3FB !important;
}

/* ── Tabs ── */
[data-baseweb="tab-list"] {
    border-bottom: 2px solid var(--border) !important;
}
[data-baseweb="tab"] {
    color: var(--secondary) !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# SESSION STATE INITIALISATION
# ═══════════════════════════════════════════════════════════════════

def _init_state():
    defaults = {
        "raw_df":          None,
        "clean_df":        None,
        "classified_df":   None,
        "journey_df":      None,
        "rep_kpi_df":      None,
        "exec_data":       None,
        "analytics_data":  None,
        "rep_figures":     None,
        "file_name":       "",
        "processing_done": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ═══════════════════════════════════════════════════════════════════
# SHARED UI HELPERS
# ═══════════════════════════════════════════════════════════════════

def page_banner(icon: str, title: str, subtitle: str = ""):
    st.markdown(f"""
    <div class="page-banner">
        <span style="font-size:32px">{icon}</span>
        <div>
            <h1>{title}</h1>
            {'<p>' + subtitle + '</p>' if subtitle else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)


def kpi_row(metrics: dict, cols_per_row: int = 4):
    """Render a row of st.metric cards."""
    items = list(metrics.items())
    rows  = [items[i:i + cols_per_row] for i in range(0, len(items), cols_per_row)]
    for row in rows:
        cols = st.columns(len(row))
        for col, (label, value) in zip(cols, row):
            with col:
                st.metric(label, fmt_number(value) if isinstance(value, (int, np.integer)) else value)


def no_data_warning():
    st.warning(
        "⚠️ No data loaded yet. Please upload an Excel file on the **Upload Center** page first.",
        icon="📂",
    )


def section(title: str):
    st.markdown(f"<hr><h3>📌 {title}</h3>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# DATA PROCESSING PIPELINE
# ═══════════════════════════════════════════════════════════════════

def run_full_pipeline(raw_df: pd.DataFrame):
    """Clean → Classify → Journey → KPIs → Executive data."""
    with st.spinner("🔄 Cleaning data..."):
        clean = clean_dataframe(raw_df)
        st.session_state["clean_df"] = clean

    with st.spinner("🧠 Running classification engine..."):
        classified = classify_dataframe(clean)
        st.session_state["classified_df"] = classified

    with st.spinner("📖 Building customer journey history..."):
        journey = build_customer_journey(classified)
        st.session_state["journey_df"] = journey

    with st.spinner("📊 Computing sales rep KPIs..."):
        rep_kpi, rep_figs = sales_rep_kpi(classified, journey)
        st.session_state["rep_kpi_df"]  = rep_kpi
        st.session_state["rep_figures"] = rep_figs

    with st.spinner("📈 Building analytics summaries..."):
        analytics = customer_analytics_summary(classified, journey)
        st.session_state["analytics_data"] = analytics

    with st.spinner("🏢 Preparing executive dashboard..."):
        exec_data = executive_dashboard_data(classified, journey, rep_kpi)
        st.session_state["exec_data"] = exec_data

    st.session_state["processing_done"] = True


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:16px 0 24px">
        <div style="font-size:42px">📊</div>
        <div style="font-size:17px; font-weight:700; color:#fff; letter-spacing:0.5px">WDI Analytics</div>
        <div style="font-size:11px; color:rgba(255,255,255,0.7); margin-top:4px">Visit Analytics Engine</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navigation",
        options=[
            "📂 Upload Center",
            "🧠 Customer Classification",
            "👥 Customer Analytics",
            "🏆 Sales Rep Performance",
            "🏢 Executive Dashboard",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    if st.session_state["processing_done"]:
        st.success("✅ Data Loaded")
        if st.session_state["clean_df"] is not None:
            df_ = st.session_state["clean_df"]
            st.markdown(f"""
            <div style="font-size:12px; color:rgba(255,255,255,0.8)">
            📄 <b>{st.session_state['file_name']}</b><br>
            🗒️ {fmt_number(len(df_))} records<br>
            👤 {fmt_number(df_['Customer Name'].nunique())} customers<br>
            🧑‍💼 {fmt_number(df_['Sales Rep Name'].nunique())} reps
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📂 No data loaded")

    st.markdown("---")
    st.markdown(
        "<div style='font-size:10px; color:rgba(255,255,255,0.5); text-align:center'>"
        "WDI Visit Analytics Engine<br>v1.0 — Fully Offline</div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════
# PAGE 1 — UPLOAD CENTER
# ═══════════════════════════════════════════════════════════════════

if page == "📂 Upload Center":
    page_banner("📂", "Upload Center", "Upload your Excel visit report and validate the data")

    # ── Upload widget ──
    uploaded = st.file_uploader(
        "Drop your Excel file here or click to browse",
        type=["xlsx", "xls"],
        help="Supports .xlsx and .xls files. First row must be column headers.",
    )

    if uploaded is not None:
        with st.spinner("Loading file..."):
            raw_df, err = load_excel(uploaded)

        if err:
            st.error(f"❌ {err}")
        else:
            st.session_state["raw_df"]   = raw_df
            st.session_state["file_name"] = uploaded.name
            st.session_state["processing_done"] = False  # reset if new file

            # ── Column validation ──
            is_valid, missing, present = validate_columns(raw_df)

            col1, col2 = st.columns([2, 1])
            with col1:
                if is_valid:
                    st.success("✅ All required columns found!")
                else:
                    st.error(f"❌ Missing columns: {', '.join(missing)}")
                    st.info("Please check your Excel file and ensure all required columns are present.")

            with col2:
                stats = basic_stats(raw_df)
                st.markdown(f"""
                <div class="section-card">
                    <b>📋 File Summary</b><br><br>
                    📄 <b>File:</b> {uploaded.name}<br>
                    🗒️ <b>Records:</b> {fmt_number(stats['total_records'])}<br>
                    👥 <b>Unique Customers:</b> {fmt_number(stats['unique_customers'])}<br>
                    🧑‍💼 <b>Sales Reps:</b> {fmt_number(stats['unique_reps'])}<br>
                    🗺️ <b>Governorates:</b> {fmt_number(stats['governorates'])}<br>
                    📅 <b>From:</b> {str(stats['date_range_start'])[:10] if stats['date_range_start'] else '—'}<br>
                    📅 <b>To:</b> {str(stats['date_range_end'])[:10] if stats['date_range_end'] else '—'}
                </div>
                """, unsafe_allow_html=True)

            # ── Data preview ──
            section("Data Preview (First 50 Rows)")
            st.dataframe(raw_df.head(50), use_container_width=True, height=350)

            # ── Column status ──
            section("Column Validation")
            col_df = pd.DataFrame({
                "Column Name": REQUIRED_COLUMNS,
                "Status": ["✅ Present" if c in present else "❌ Missing" for c in REQUIRED_COLUMNS],
            })
            st.dataframe(col_df, use_container_width=True, hide_index=True)

            # ── Process button ──
            st.markdown("<br>", unsafe_allow_html=True)
            if is_valid:
                if st.button("🚀 Process & Classify Data", use_container_width=True):
                    run_full_pipeline(raw_df)
                    st.success("✅ Processing complete! Navigate to other pages to view results.")
                    st.balloons()
            else:
                st.warning("Fix the missing columns before processing.")
    else:
        # Landing state
        st.markdown("""
        <div class="section-card" style="text-align:center; padding:48px">
            <div style="font-size:64px">📊</div>
            <h2 style="color:#1F4E79">WDI Visit Analytics Engine</h2>
            <p style="color:#555; max-width:500px; margin:0 auto 20px">
                Upload your Excel visit report to automatically classify customers,
                track journeys, and generate executive analytics — fully offline.
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📋 Required Column Names"):
            cols_df = pd.DataFrame({"Required Columns": REQUIRED_COLUMNS})
            st.dataframe(cols_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 2 — CUSTOMER CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════

elif page == "🧠 Customer Classification":
    page_banner("🧠", "Automatic Customer Classification",
                "Rule-based keyword scoring engine — No AI, fully offline")

    if not st.session_state["processing_done"]:
        no_data_warning()
        st.stop()

    classified_df = st.session_state["classified_df"]
    journey_df    = st.session_state["journey_df"]

    # ── Summary KPIs ──
    status_counts = classified_df["Display Status"].value_counts()
    kpi_row({
        "Total Records":       len(classified_df),
        "Unique Customers":    classified_df["Customer Name"].nunique(),
        "Classified":          int((classified_df["Suggested Status"] != "unclassified").sum()),
        "Unclassified":        int((classified_df["Suggested Status"] == "unclassified").sum()),
    })

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Classification Results",
        "🗺️ Customer Journey",
        "⚙️ Keyword Rules",
        "📥 Export",
    ])

    # ─── Tab 1: Results table ───
    with tab1:
        section("Classification Results")

        # Filters
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            reps_list = ["All"] + sorted(classified_df["Sales Rep Name"].dropna().unique().tolist())
            sel_rep = st.selectbox("Filter by Sales Rep", reps_list, key="cls_rep")
        with fc2:
            statuses_list = ["All"] + sorted(classified_df["Display Status"].dropna().unique().tolist())
            sel_status = st.selectbox("Filter by Status", statuses_list, key="cls_status")
        with fc3:
            min_conf = st.slider("Min Confidence Score", 0, 100, 0, 5, key="cls_conf")

        filtered = classified_df.copy()
        if sel_rep != "All":
            filtered = filtered[filtered["Sales Rep Name"] == sel_rep]
        if sel_status != "All":
            filtered = filtered[filtered["Display Status"] == sel_status]
        filtered = filtered[filtered["Confidence Score"] >= min_conf]

        # ── اختيار طريقة العرض ──
        view_mode = st.radio(
            "طريقة العرض",
            options=["👤 عميل واحد — الموقف النهائي", "📋 كل الزيارات"],
            horizontal=True,
            key="cls_view_mode"
        )

        # ── عمود عدد الزيارات لكل عميل ──
        visit_counts = (
            classified_df.groupby("Customer Name")
            .size()
            .reset_index(name="Visit Count")
        )
        filtered = filtered.merge(visit_counts, on="Customer Name", how="left")

        if view_mode == "👤 عميل واحد — الموقف النهائي":

            # ── آخر زيارة لكل عميل = الموقف النهائي ──
            final_status_df = (
                filtered.sort_values("Visit Date", ascending=True)
                .groupby("Customer Name", as_index=False)
                .last()
            )

            # ── إضافة أول وآخر تاريخ زيارة ──
            date_range = (
                classified_df.groupby("Customer Name")["Visit Date"]
                .agg(
                    First_Visit="min",
                    Last_Visit="max"
                )
                .reset_index()
            )
            final_status_df = final_status_df.merge(
                date_range, on="Customer Name", how="left"
            )

            # ── ترتيب الأعمدة ──
            display_cols_final = [
                "Customer Name", "Sales Rep Name", "Governorate",
                "Display Status", "Visit Count",
                "First_Visit", "Last_Visit",
                "Confidence Score", "Matched Keywords",
                "Classification Reason",
            ]
            show_cols_final = [c for c in display_cols_final if c in final_status_df.columns]

            # ── تنسيق التواريخ ──
            for dc in ["First_Visit", "Last_Visit", "Visit Date"]:
                if dc in final_status_df.columns:
                    final_status_df[dc] = pd.to_datetime(
                        final_status_df[dc], errors="coerce"
                    ).dt.strftime("%Y-%m-%d")

            # ── إعادة تسمية الأعمدة بالعربي ──
            final_status_df = final_status_df[show_cols_final].rename(columns={
                "Customer Name":         "اسم العميل",
                "Sales Rep Name":        "المندوب",
                "Governorate":           "المحافظة",
                "Display Status":        "الحالة النهائية",
                "Visit Count":           "عدد الزيارات",
                "First_Visit":           "أول زيارة",
                "Last_Visit":            "آخر زيارة",
                "Confidence Score":      "نسبة الثقة",
                "Matched Keywords":      "الكلمات المفتاحية",
                "Classification Reason": "سبب التصنيف",
            })

            st.info(
                f"👤 إجمالي العملاء: **{len(final_status_df):,}** عميل فريد"
            )

            # ── ملخص الحالات فوق الجدول ──
            status_summary = (
                final_status_df["الحالة النهائية"]
                .value_counts()
                .reset_index()
            )
            status_summary.columns = ["الحالة", "العدد"]
            summary_cols = st.columns(len(status_summary))
            for col, (_, row) in zip(summary_cols, status_summary.iterrows()):
                with col:
                    st.metric(row["الحالة"], row["العدد"])

            st.markdown("<br>", unsafe_allow_html=True)

            st.dataframe(
                final_status_df.reset_index(drop=True),
                use_container_width=True,
                height=500,
            )

            # ── Export الموقف النهائي ──
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                final_status_df.to_excel(writer, index=False, sheet_name="الموقف النهائي")
            st.download_button(
                "⬇️ تحميل الموقف النهائي Excel",
                data=output.getvalue(),
                file_name="Final_Customer_Status.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        else:
            # ── عرض كل الزيارات كما كان ──
            display_cols = [
                "Visit Date", "Customer Name", "Sales Rep Name",
                "Display Status", "Visit Count", "Confidence Score",
                "Matched Keywords", "Classification Reason", "Governorate",
            ]
            show_cols = [c for c in display_cols if c in filtered.columns]

            st.info(
                f"📋 إجمالي الزيارات: **{fmt_number(len(filtered))}** "
                f"من **{fmt_number(len(classified_df))}**"
            )
            st.dataframe(
                filtered[show_cols].reset_index(drop=True),
                use_container_width=True,
                height=500,
            )


    # ─── Tab 2: Customer Journey ───
    with tab2:
        section("Customer Journey History")

        search_name = st.text_input("🔍 Search Customer Name", placeholder="Type to search...", key="journey_search")

        if search_name.strip():
            mask = journey_df["Customer Name"].str.contains(search_name.strip(), case=False, na=False)
            journey_filtered = journey_df[mask]
        else:
            journey_filtered = journey_df

        display_journey_cols = [
            "Customer Name", "Latest Status", "Latest Confidence",
            "Visit Count", "First Visit Date", "Last Visit Date",
            "Days Since Last Visit", "Governorate", "Sales Rep Name",
        ]
        show_j = [c for c in display_journey_cols if c in journey_filtered.columns]

        st.dataframe(
            journey_filtered[show_j].reset_index(drop=True),
            use_container_width=True, height=420,
        )

        # Detail drilldown
        if not journey_filtered.empty:
            st.markdown("---")
            st.subheader("Customer Detail View")
            selected_customer = st.selectbox(
                "Select a customer to view full journey",
                journey_filtered["Customer Name"].tolist(),
                key="journey_detail_select",
            )
            if selected_customer:
                row = journey_filtered[journey_filtered["Customer Name"] == selected_customer].iloc[0]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Visit Count",       row["Visit Count"])
                c2.metric("Latest Status",      row["Latest Status"])
                c3.metric("Days Since Last Visit", row.get("Days Since Last Visit", "—"))
                c4.metric("Confidence",         f"{row.get('Latest Confidence', 0):.1f}%")

                st.markdown("**Full Status Journey:**")
                st.code(row.get("Status History", "—"), language=None)

                # Show all visits for this customer
                cust_visits = classified_df[classified_df["Customer Name"] == selected_customer].copy()
                cust_visits["Visit Date"] = pd.to_datetime(cust_visits["Visit Date"], errors="coerce").dt.strftime("%Y-%m-%d")
                visit_show_cols = [
                    "Visit Date", "Sales Rep Name", "Display Status",
                    "Confidence Score", "Visit Notes", "Matched Keywords",
                ]
                st.dataframe(
                    cust_visits[[c for c in visit_show_cols if c in cust_visits.columns]].reset_index(drop=True),
                    use_container_width=True,
                )

    # ─── Tab 3: Keyword Rules ───
    with tab3:
        section("Keyword Rules & تصدير بيانات الزيارات حسب الحالة")

        t3_col1, t3_col2 = st.columns([1, 1])

        # ── جدول الكلمات المفتاحية ──
        with t3_col1:
            st.markdown("#### 📋 جدول الكلمات المفتاحية")
            rules_df = get_rules_dataframe()

            # فلتر الحالة في جدول الكلمات
            all_statuses_rules = ["الكل"] + sorted(rules_df["Status"].unique().tolist())
            sel_rule_status = st.selectbox(
                "فلتر حسب الحالة",
                all_statuses_rules,
                key="rules_status_filter"
            )
            if sel_rule_status != "الكل":
                rules_filtered = rules_df[rules_df["Status"] == sel_rule_status]
            else:
                rules_filtered = rules_df

            st.dataframe(
                rules_filtered.reset_index(drop=True),
                use_container_width=True,
                height=400,
                hide_index=True
            )

            st.markdown("""
            | Score | Category |
            |-------|----------|
            | +100  | Current Customer |
            | +80   | New Customer |
            | +60   | Potential Customer |
            | +40   | Target Customer |
            | +20   | Former Customer |
            | −100  | Not Interested |
            """)

        # ── تصدير بيانات الزيارات حسب الحالة ──
        with t3_col2:
            st.markdown("#### 📤 استخراج بيانات الزيارات حسب الحالة")

            # قائمة الحالات المتاحة من البيانات الفعلية
            available_statuses = sorted(
                classified_df["Display Status"].dropna().unique().tolist()
            )

            sel_export_status = st.selectbox(
                "اختار الحالة اللي عايز تشتغل عليها",
                options=["الكل"] + available_statuses,
                key="export_status_select"
            )

            # فلتر إضافي للمندوب
            reps_list_t3 = ["الكل"] + sorted(
                classified_df["Sales Rep Name"].dropna().unique().tolist()
            )
            sel_rep_t3 = st.selectbox(
                "فلتر حسب المندوب (اختياري)",
                options=reps_list_t3,
                key="export_rep_select"
            )

            # فلتر إضافي للمحافظة
            gov_list_t3 = ["الكل"] + sorted(
                classified_df["Governorate"].dropna().unique().tolist()
            )
            sel_gov_t3 = st.selectbox(
                "فلتر حسب المحافظة (اختياري)",
                options=gov_list_t3,
                key="export_gov_select"
            )

            # ── تطبيق الفلاتر ──
            export_df = classified_df.copy()

            if sel_export_status != "الكل":
                export_df = export_df[
                    export_df["Display Status"] == sel_export_status
                ]
            if sel_rep_t3 != "الكل":
                export_df = export_df[
                    export_df["Sales Rep Name"] == sel_rep_t3
                ]
            if sel_gov_t3 != "الكل":
                export_df = export_df[
                    export_df["Governorate"] == sel_gov_t3
                ]

            # ── إحصائيات سريعة ──
            st.markdown("<br>", unsafe_allow_html=True)

            m1, m2, m3 = st.columns(3)
            m1.metric("إجمالي الزيارات",  f"{len(export_df):,}")
            m2.metric("عدد العملاء",       f"{export_df['Customer Name'].nunique():,}")
            m3.metric("عدد المندوبين",     f"{export_df['Sales Rep Name'].nunique():,}")

            st.markdown("<br>", unsafe_allow_html=True)

            # ── معاينة البيانات ──
            preview_cols = [
                "Visit Date", "Customer Name", "Sales Rep Name",
                "Display Status", "Governorate", "District",
                "Visit Notes", "Matched Keywords", "Classification Reason",
            ]
            show_preview = [c for c in preview_cols if c in export_df.columns]

            with st.expander("👁️ معاينة البيانات قبل التحميل"):
                preview_data = export_df[show_preview].copy()
                if "Visit Date" in preview_data.columns:
                    preview_data["Visit Date"] = pd.to_datetime(
                        preview_data["Visit Date"], errors="coerce"
                    ).dt.strftime("%Y-%m-%d")
                st.dataframe(
                    preview_data.reset_index(drop=True),
                    use_container_width=True,
                    height=300,
                )

            # ── تحميل Excel ──
            if not export_df.empty:
                # تجهيز ملف الاستخراج
                export_out = export_df[show_preview].copy()
                if "Visit Date" in export_out.columns:
                    export_out["Visit Date"] = pd.to_datetime(
                        export_out["Visit Date"], errors="coerce"
                    ).dt.strftime("%Y-%m-%d")

                # إضافة عمود عدد زيارات العميل
                vc = (
                    classified_df.groupby("Customer Name")
                    .size()
                    .reset_index(name="عدد الزيارات")
                )
                export_out = export_out.merge(vc, on="Customer Name", how="left")

                # تسمية الأعمدة بالعربي
                export_out = export_out.rename(columns={
                    "Visit Date":            "تاريخ الزيارة",
                    "Customer Name":         "اسم العميل",
                    "Sales Rep Name":        "المندوب",
                    "Display Status":        "الحالة",
                    "Governorate":           "المحافظة",
                    "District":              "المنطقة",
                    "Visit Notes":           "ملاحظات الزيارة",
                    "Matched Keywords":      "الكلمات المفتاحية",
                    "Classification Reason": "سبب التصنيف",
                })

                import io
                output_t3 = io.BytesIO()
                with pd.ExcelWriter(output_t3, engine="openpyxl") as writer:
                    export_out.to_excel(
                        writer,
                        index=False,
                        sheet_name=sel_export_status[:30] if sel_export_status != "الكل" else "كل الحالات"
                    )

                # اسم الملف
                file_label = sel_export_status.replace(" ", "_") if sel_export_status != "الكل" else "All_Statuses"
                rep_label  = f"_{sel_rep_t3}"  if sel_rep_t3  != "الكل" else ""
                gov_label  = f"_{sel_gov_t3}"  if sel_gov_t3  != "الكل" else ""

                st.download_button(
                    label=f"⬇️ تحميل بيانات ({sel_export_status}) — {len(export_out):,} زيارة",
                    data=output_t3.getvalue(),
                    file_name=f"Visits_{file_label}{rep_label}{gov_label}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.warning("⚠️ مفيش بيانات بالفلاتر دي")

    # ─── Tab 4: Export ───
    with tab4:
        section("Export Classification Results")
        st.markdown("Download the full classification table as a styled Excel file.")

        if st.button("📥 Generate Classification Export", use_container_width=False):
            xlsx_bytes = export_classification_results(classified_df)
            st.download_button(
                label="⬇️ Download Classification Results.xlsx",
                data=xlsx_bytes,
                file_name="Classification_Results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


# ═══════════════════════════════════════════════════════════════════
# PAGE 3 — CUSTOMER ANALYTICS
# ═══════════════════════════════════════════════════════════════════

elif page == "👥 Customer Analytics":
    page_banner("👥", "Customer Analytics", "Deep-dive into customer segments and visit patterns")

    if not st.session_state["processing_done"]:
        no_data_warning()
        st.stop()

    analytics = st.session_state["analytics_data"]
    journey_df = st.session_state["journey_df"]

    # ── KPI Row ──
    kpis = analytics["kpi"]
    kpi_row({k: v for k, v in list(kpis.items())[:4]}, cols_per_row=4)
    kpi_row({k: v for k, v in list(kpis.items())[4:]}, cols_per_row=5)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row ──
    ch1, ch2 = st.columns([1, 1])
    with ch1:
        if analytics.get("fig_status_pie"):
            st.plotly_chart(analytics["fig_status_pie"], use_container_width=True)
    with ch2:
        if analytics.get("fig_gov"):
            st.plotly_chart(analytics["fig_gov"], use_container_width=True)

    # ── Top 20 Most Visited ──
    section("Top 20 Most Visited Customers")
    top20 = analytics.get("top_20", pd.DataFrame())
    if not top20.empty:
        st.dataframe(top20, use_container_width=True, height=380)

        # Bar chart
        fig_top = go.Figure(go.Bar(
            y=top20["Customer Name"],
            x=top20["Visit Count"],
            orientation="h",
            marker_color="#2E75B6",
            text=top20["Visit Count"],
            textposition="outside",
        ))
        fig_top.update_layout(
            title="Top 20 Most Visited Customers",
            template="plotly_white",
            paper_bgcolor="#F5F7FA",
            yaxis=dict(autorange="reversed"),
            margin=dict(l=20, r=40, t=50, b=20),
            height=520,
        )
        st.plotly_chart(fig_top, use_container_width=True)

    # ── Not Visited Segments ──
    section("Customers Not Visited")

    nv_tabs = st.tabs(["30 Days", "60 Days", "90 Days", "180 Days"])
    for tab_obj, days, key in zip(
        nv_tabs,
        [30, 60, 90, 180],
        ["not_visited_30", "not_visited_60", "not_visited_90", "not_visited_180"],
    ):
        with tab_obj:
            df_nv = analytics.get(key, pd.DataFrame())
            if df_nv.empty:
                st.info(f"No customers with {days}+ days since last visit.")
            else:
                st.warning(f"⚠️ {len(df_nv)} customers not visited for {days}+ days")
                st.dataframe(df_nv, use_container_width=True, height=320)
                xlsx_nv = export_followup_customers(journey_df, days_threshold=days)
                st.download_button(
                    f"⬇️ Export {days}-Day Follow-up List",
                    data=xlsx_nv,
                    file_name=f"Followup_{days}_Days.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    # ── District Distribution ──
    section("Governorate & District Breakdown")
    bd1, bd2 = st.columns(2)
    with bd1:
        gov_df = analytics.get("gov_dist_df", pd.DataFrame())
        if not gov_df.empty:
            st.markdown("**Customers by Governorate**")
            st.dataframe(gov_df, use_container_width=True, hide_index=True)
    with bd2:
        dist_df = analytics.get("district_dist_df", pd.DataFrame())
        if not dist_df.empty:
            st.markdown("**Customers by District (Top 20)**")
            st.dataframe(dist_df.head(20), use_container_width=True, hide_index=True)

    # ── Export ──
    section("Export Customer Summary")
    journey_clean = journey_df.drop(columns=["_journey"], errors="ignore")
    xlsx_cust = export_customer_summary(journey_clean)
    st.download_button(
        "⬇️ Download Customer Summary.xlsx",
        data=xlsx_cust,
        file_name="Customer_Summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ═══════════════════════════════════════════════════════════════════
# PAGE 4 — SALES REP PERFORMANCE
# ═══════════════════════════════════════════════════════════════════

elif page == "🏆 Sales Rep Performance":
    page_banner("🏆", "Sales Rep Performance", "Individual and comparative rep KPIs, rankings and trends")

    if not st.session_state["processing_done"]:
        no_data_warning()
        st.stop()

    rep_kpi_df  = st.session_state["rep_kpi_df"]
    rep_figures = st.session_state["rep_figures"]
    classified  = st.session_state["classified_df"]

    if rep_kpi_df is None or rep_kpi_df.empty:
        st.warning("No sales rep data available.")
        st.stop()

    # ── Team summary row ──
    kpi_row({
        "Total Reps":            len(rep_kpi_df),
        "Total Visits":          int(rep_kpi_df["Total Visits"].sum()),
        "Total Unique Customers":int(rep_kpi_df["Unique Customers"].sum()),
        "Avg Conversion Rate":   f"{rep_kpi_df['Conversion Rate (%)'].mean():.1f}%",
    })

    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPI Table ──
    section("Sales Rep KPI Table")

    # Highlight best performer
    st.info(f"🥇 Top performer: **{rep_kpi_df.iloc[0]['Sales Rep Name']}** "
            f"with {fmt_number(rep_kpi_df.iloc[0]['Total Visits'])} visits")

    st.dataframe(
        rep_kpi_df.reset_index(drop=True),
        use_container_width=True,
        height=420,
    )

    # ── Charts ──
    section("Performance Charts")
    for chart_title, fig in rep_figures:
        st.plotly_chart(fig, use_container_width=True)

    # ── Monthly trend per rep ──
    section("Monthly Visits per Sales Rep")
    if "Visit Date" in classified.columns and "Sales Rep Name" in classified.columns:
        df_m = classified.copy()
        df_m["Visit Date"] = pd.to_datetime(df_m["Visit Date"], errors="coerce")

        # ── فلاتر ──
        fl1, fl2, fl3, fl4 = st.columns(4)

        # فلتر السنة
        years_avail = sorted(df_m["Visit Date"].dt.year.dropna().unique().astype(int).tolist())
        with fl1:
            sel_years = st.multiselect(
                "📅 السنة",
                options=years_avail,
                default=years_avail,
                key="rep_trend_year"
            )

        # فلتر الشهر
        months_map = {
            1:"يناير", 2:"فبراير", 3:"مارس", 4:"أبريل",
            5:"مايو", 6:"يونيو", 7:"يوليو", 8:"أغسطس",
            9:"سبتمبر", 10:"أكتوبر", 11:"نوفمبر", 12:"ديسمبر"
        }
        months_avail = sorted(df_m["Visit Date"].dt.month.dropna().unique().astype(int).tolist())
        with fl2:
            sel_months = st.multiselect(
                "📅 الشهر",
                options=months_avail,
                format_func=lambda x: f"{months_map[x]} ({x})",
                default=months_avail,
                key="rep_trend_month"
            )

        # فلتر اليوم
        days_avail = sorted(df_m["Visit Date"].dt.day.dropna().unique().astype(int).tolist())
        with fl3:
            sel_days = st.multiselect(
                "📅 اليوم",
                options=days_avail,
                default=days_avail,
                key="rep_trend_day"
            )

        # فلتر المندوب
        reps_avail = sorted(df_m["Sales Rep Name"].dropna().unique().tolist())
        with fl4:
            sel_reps_trend = st.multiselect(
                "👤 المندوب",
                options=reps_avail,
                default=reps_avail,
                key="rep_trend_rep"
            )

        # ── تطبيق الفلاتر ──
        mask = (
            df_m["Visit Date"].dt.year.isin(sel_years) &
            df_m["Visit Date"].dt.month.isin(sel_months) &
            df_m["Visit Date"].dt.day.isin(sel_days) &
            df_m["Sales Rep Name"].isin(sel_reps_trend)
        )
        df_m_filtered = df_m[mask].copy()

        if df_m_filtered.empty:
            st.warning("⚠️ مفيش بيانات بالفلاتر دي — جرب تغير الاختيارات")
        else:
            # ── عرض إجمالي بعد الفلترة ──
            st.info(
                f"📊 إجمالي الزيارات: **{len(df_m_filtered):,}** | "
                f"عدد المندوبين: **{df_m_filtered['Sales Rep Name'].nunique()}** | "
                f"عدد العملاء: **{df_m_filtered['Customer Name'].nunique()}**"
            )

            # ── تجميع البيانات ──
            df_m_filtered["Month_Period"] = df_m_filtered["Visit Date"].dt.to_period("M").astype(str)
            monthly_rep = (
                df_m_filtered.groupby(["Month_Period", "Sales Rep Name"])
                .size().reset_index(name="Visits")
            )

            import plotly.express as px

            # ── Chart 1: Line Chart ──
            fig_monthly = px.line(
                monthly_rep,
                x="Month_Period",
                y="Visits",
                color="Sales Rep Name",
                markers=True,
                template="plotly_white",
                title="Monthly Visits per Sales Rep",
                text="Visits",
            )
            fig_monthly.update_traces(textposition="top center")
            fig_monthly.update_layout(
                paper_bgcolor="#F5F7FA",
                legend=dict(orientation="h", y=-0.3),
                xaxis_tickangle=-45,
                margin=dict(l=20, r=20, t=50, b=100),
            )
            st.plotly_chart(fig_monthly, use_container_width=True)

            # ── Chart 2: Bar Chart مقارنة ──
            rep_totals = (
                df_m_filtered.groupby("Sales Rep Name")
                .size().reset_index(name="Total Visits")
                .sort_values("Total Visits", ascending=False)
            )
            fig_bar = px.bar(
                rep_totals,
                x="Sales Rep Name",
                y="Total Visits",
                color="Total Visits",
                color_continuous_scale=[[0, "#BDD7EE"], [1, "#1F4E79"]],
                template="plotly_white",
                title="إجمالي الزيارات لكل مندوب (بعد الفلترة)",
                text="Total Visits",
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(
                paper_bgcolor="#F5F7FA",
                showlegend=False,
                xaxis_tickangle=-35,
                margin=dict(l=20, r=20, t=50, b=80),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            # ── جدول تفصيلي ──
            with st.expander("📋 عرض الجدول التفصيلي"):
                pivot = monthly_rep.pivot_table(
                    index="Month_Period",
                    columns="Sales Rep Name",
                    values="Visits",
                    fill_value=0
                ).reset_index()
                pivot["الإجمالي"] = pivot.iloc[:, 1:].sum(axis=1)
                st.dataframe(pivot, use_container_width=True, hide_index=True)

    # ── Individual rep drilldown ──
    section("Individual Rep Drilldown")
    rep_names = rep_kpi_df["Sales Rep Name"].tolist()
    sel_rep2 = st.selectbox("Select Sales Rep", rep_names, key="rep_drill")
    if sel_rep2:
        row_r = rep_kpi_df[rep_kpi_df["Sales Rep Name"] == sel_rep2].iloc[0]
        dr1, dr2, dr3, dr4, dr5 = st.columns(5)
        dr1.metric("Total Visits",      fmt_number(row_r["Total Visits"]))
        dr2.metric("Unique Customers",  fmt_number(row_r["Unique Customers"]))
        dr3.metric("Current Customers", fmt_number(row_r["Current Customers"]))
        dr4.metric("Conversion Rate",   f"{row_r['Conversion Rate (%)']:.1f}%")
        dr5.metric("Visits/Month",      f"{row_r['Visits Per Month']:.1f}")

        rep_visits = classified[classified["Sales Rep Name"] == sel_rep2]
        if not rep_visits.empty:
            cust_freq = (
                rep_visits.groupby("Customer Name").size()
                .reset_index(name="Visits")
                .sort_values("Visits", ascending=False)
                .head(15)
            )
            import plotly.express as px
            fig_rep_cust = px.bar(
                cust_freq, x="Visits", y="Customer Name",
                orientation="h",
                color_discrete_sequence=["#2E75B6"],
                template="plotly_white",
                title=f"Top 15 Customers for {sel_rep2}",
                text="Visits",
            )
            fig_rep_cust.update_traces(textposition="outside")
            fig_rep_cust.update_layout(
                paper_bgcolor="#F5F7FA",
                yaxis=dict(autorange="reversed"),
                margin=dict(l=20, r=40, t=50, b=20),
            )
            st.plotly_chart(fig_rep_cust, use_container_width=True)

    # ── Export ──
    section("Export Sales Rep KPI")
    xlsx_rep = export_sales_rep_kpi(rep_kpi_df)
    st.download_button(
        "⬇️ Download Sales Rep KPI.xlsx",
        data=xlsx_rep,
        file_name="Sales_Rep_KPI.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ═══════════════════════════════════════════════════════════════════
# PAGE 5 — EXECUTIVE DASHBOARD
# ═══════════════════════════════════════════════════════════════════

elif page == "🏢 Executive Dashboard":
    page_banner("🏢", "Executive Dashboard", "High-level KPIs, trends and strategic insights")

    if not st.session_state["processing_done"]:
        no_data_warning()
        st.stop()

    exec_data  = st.session_state["exec_data"]
    journey_df = st.session_state["journey_df"]
    rep_kpi_df = st.session_state["rep_kpi_df"]

    # ── KPI cards (row 1 — 4 cols) ──
    kpis = exec_data.get("kpis", {})
    kpi_items = list(kpis.items())

    c1, c2, c3, c4 = st.columns(4)
    for col, (label, val) in zip([c1, c2, c3, c4], kpi_items[:4]):
        with col:
            st.metric(label, fmt_number(val))

    # ── KPI cards (row 2 — 4 cols) ──
    if len(kpi_items) > 4:
        c5, c6, c7, c8 = st.columns(4)
        for col, (label, val) in zip([c5, c6, c7, c8], kpi_items[4:8]):
            with col:
                st.metric(label, fmt_number(val))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Monthly trend (full width) ──
    section("Monthly Visit Trend")
    fig_trend = exec_data.get("fig_trend")
    if fig_trend:
        st.plotly_chart(fig_trend, use_container_width=True)

    # ── Two-column: pie + rep ranking ──
    col_left, col_right = st.columns([1, 1])
    with col_left:
        section("Customer Status Distribution")
        fig_pie = exec_data.get("fig_status_pie")
        if fig_pie:
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        section("Top Sales Reps Ranking")
        fig_rank = exec_data.get("fig_rep_ranking")
        if fig_rank:
            st.plotly_chart(fig_rank, use_container_width=True)

    # ── Governorate + District ──
    col_g, col_d = st.columns([1, 1])
    with col_g:
        section("Governorate Distribution")
        fig_gov = exec_data.get("fig_gov")
        if fig_gov:
            st.plotly_chart(fig_gov, use_container_width=True)
        else:
            gov_df = exec_data.get("gov_dist_df", pd.DataFrame())
            if not gov_df.empty:
                st.dataframe(gov_df, use_container_width=True, hide_index=True)

    with col_d:
        section("District Distribution")
        fig_dist = exec_data.get("fig_district")
        if fig_dist:
            st.plotly_chart(fig_dist, use_container_width=True)

    # ── Top Customers ──
    section("Top 20 Most Visited Customers")
    top_c_df = exec_data.get("top_customers_df", pd.DataFrame())
    if not top_c_df.empty:
        st.dataframe(top_c_df, use_container_width=True, height=340)

    # ── Follow-up Required ──
    section("⏰ Follow-up Required (Not Visited 30+ Days)")
    fu_df = exec_data.get("followup_df", pd.DataFrame())
    if not fu_df.empty:
        st.error(f"🚨 {len(fu_df)} customers require follow-up (showing top 30)")
        st.dataframe(fu_df, use_container_width=True, height=320)

    # ── Export section ──
    section("Export Executive Reports")
    e1, e2 = st.columns(2)

    with e1:
        # Executive dashboard export
        summary_dict = {
            "kpis":         kpis,
            "monthly":      exec_data.get("monthly_df", pd.DataFrame()),
            "status_dist":  exec_data.get("status_dist_df", pd.DataFrame()),
            "gov_dist":     exec_data.get("gov_dist_df", pd.DataFrame()),
            "top_customers":exec_data.get("top_customers_df", pd.DataFrame()),
        }
        xlsx_exec = export_executive_dashboard(summary_dict)
        st.download_button(
            "⬇️ Executive Dashboard.xlsx",
            data=xlsx_exec,
            file_name="Executive_Dashboard.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with e2:
        # Customer summary export
        journey_clean = journey_df.drop(columns=["_journey"], errors="ignore") if journey_df is not None else pd.DataFrame()
        if not journey_clean.empty:
            xlsx_cust = export_customer_summary(journey_clean)
            st.download_button(
                "⬇️ Customer Summary.xlsx",
                data=xlsx_cust,
                file_name="Customer_Summary.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    # Sales rep KPI export
    if rep_kpi_df is not None and not rep_kpi_df.empty:
        xlsx_rep = export_sales_rep_kpi(rep_kpi_df)
        st.download_button(
            "⬇️ Sales Rep KPI.xlsx",
            data=xlsx_rep,
            file_name="Sales_Rep_KPI.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
