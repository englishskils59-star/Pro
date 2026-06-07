# dashboard.py
# WDI Visit Analytics Engine
# Analytics computation functions for pages 3, 4, 5.
# Returns DataFrames and dicts consumed by app.py for rendering.

import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from utils import safe_str, days_since, STATUS_COLORS

# Brand palette
PRIMARY   = "#1F4E79"
SECONDARY = "#2E75B6"
ACCENT    = "#70AD47"
BG        = "#F5F7FA"

PLOTLY_TEMPLATE = "plotly_white"

# ═══════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════

def _color_sequence():
    return [PRIMARY, SECONDARY, ACCENT, "#FFC000", "#C00000", "#A9A9A9",
            "#70AD47", "#ED7D31", "#4472C4", "#9E480E"]


def status_color_map() -> dict:
    return STATUS_COLORS.copy()


# ═══════════════════════════════════════════════════════════════════
# PAGE 3 — CUSTOMER ANALYTICS
# ═══════════════════════════════════════════════════════════════════

def customer_analytics_summary(classified_df: pd.DataFrame, journey_df: pd.DataFrame) -> dict:
    """
    Compute all customer analytics KPIs and tables.
    Returns a dict with keys used by app.py page 3.
    """
    today = pd.Timestamp(datetime.today().date())
    result = {}

    # ── Basic counts ──
    total_visits       = len(classified_df)
    unique_customers   = journey_df["Customer Name"].nunique() if not journey_df.empty else 0
    repeated_customers = int((journey_df["Visit Count"] > 1).sum()) if not journey_df.empty else 0
    new_customers      = int((journey_df["Latest Status"] == "New Customer").sum())
    current_customers  = int((journey_df["Latest Status"] == "Current Customer").sum())
    potential_customers= int((journey_df["Latest Status"] == "Potential Customer").sum())
    target_customers   = int((journey_df["Latest Status"] == "Target Customer").sum())
    former_customers   = int((journey_df["Latest Status"] == "Former Customer").sum())
    not_interested     = int((journey_df["Latest Status"] == "Not Interested").sum())

    result["kpi"] = {
        "Total Visits":         total_visits,
        "Unique Customers":     unique_customers,
        "Repeated Customers":   repeated_customers,
        "New Customers":        new_customers,
        "Current Customers":    current_customers,
        "Potential Customers":  potential_customers,
        "Target Customers":     target_customers,
        "Former Customers":     former_customers,
        "Not Interested":       not_interested,
    }

    # ── Top 20 Most Visited ──
    top20 = (
        journey_df.nlargest(20, "Visit Count")[
            ["Customer Name", "Visit Count", "Latest Status", "Governorate", "Last Visit Date"]
        ].reset_index(drop=True)
    )
    top20.index += 1
    result["top_20"] = top20

    # ── Not visited segments ──
    def _not_visited(days: int) -> pd.DataFrame:
        if journey_df.empty:
            return pd.DataFrame()
        mask = journey_df["Days Since Last Visit"].fillna(9999) >= days
        subset = journey_df[mask][
            ["Customer Name", "Days Since Last Visit", "Latest Status",
             "Last Visit Date", "Governorate", "Sales Rep Name"]
        ].sort_values("Days Since Last Visit", ascending=False).reset_index(drop=True)
        subset.index += 1
        return subset

    result["not_visited_30"]  = _not_visited(30)
    result["not_visited_60"]  = _not_visited(60)
    result["not_visited_90"]  = _not_visited(90)
    result["not_visited_180"] = _not_visited(180)

    # ── Status distribution chart ──
    status_counts = journey_df["Latest Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    result["status_dist_df"] = status_counts

    colors = [STATUS_COLORS.get(s, PRIMARY) for s in status_counts["Status"]]
    fig_pie = go.Figure(go.Pie(
        labels=status_counts["Status"],
        values=status_counts["Count"],
        marker_colors=colors,
        hole=0.4,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
    ))
    fig_pie.update_layout(
        title="Customer Status Distribution",
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=BG,
        legend=dict(orientation="v", x=1.0, y=0.5),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    result["fig_status_pie"] = fig_pie

    # ── Governorate distribution ──
    gov_counts = (
        classified_df.groupby("Governorate")["Customer Name"]
        .nunique().reset_index()
        .rename(columns={"Customer Name": "Unique Customers"})
        .sort_values("Unique Customers", ascending=False)
    )
    result["gov_dist_df"] = gov_counts

    fig_gov = px.bar(
        gov_counts.head(15), x="Governorate", y="Unique Customers",
        color_discrete_sequence=[SECONDARY],
        template=PLOTLY_TEMPLATE,
        title="Unique Customers by Governorate (Top 15)",
        text="Unique Customers",
    )
    fig_gov.update_traces(textposition="outside")
    fig_gov.update_layout(paper_bgcolor=BG, margin=dict(l=20, r=20, t=50, b=80))
    result["fig_gov"] = fig_gov

    # ── District distribution ──
    district_counts = (
        classified_df.groupby("District")["Customer Name"]
        .nunique().reset_index()
        .rename(columns={"Customer Name": "Unique Customers"})
        .sort_values("Unique Customers", ascending=False)
    )
    result["district_dist_df"] = district_counts

    return result


# ═══════════════════════════════════════════════════════════════════
# PAGE 4 — SALES REP PERFORMANCE
# ═══════════════════════════════════════════════════════════════════

def sales_rep_kpi(classified_df: pd.DataFrame, journey_df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """
    Compute per-rep KPIs.
    Returns (kpi_df, figures_list).
    """
    if classified_df.empty or "Sales Rep Name" not in classified_df.columns:
        return pd.DataFrame(), []

    records = []
    today = pd.Timestamp(datetime.today().date())

    for rep_name, grp in classified_df.groupby("Sales Rep Name"):
        total_visits     = len(grp)
        unique_customers = grp["Customer Name"].nunique()

        # Customers acquired as Current in this rep's visits
        current_acq  = int((grp["Display Status"] == "Current Customer").sum())
        new_acq      = int((grp["Display Status"] == "New Customer").sum())
        potential    = int((grp["Display Status"] == "Potential Customer").sum())

        # Visit days span
        dates = grp["Visit Date"].dropna()
        if len(dates) > 1:
            span_days = max(1, (dates.max() - dates.min()).days + 1)
        else:
            span_days = 1

        visits_per_day = round(total_visits / span_days, 2)

        # Months active
        months_active = grp["Visit Date"].dropna().dt.to_period("M").nunique()
        visits_per_month = round(total_visits / max(1, months_active), 1)

        # Conversion rate: (current_acq / unique_customers) * 100
        conversion_rate = round((current_acq / max(1, unique_customers)) * 100, 1)

        records.append({
            "Sales Rep Name":          rep_name,
            "Total Visits":            total_visits,
            "Unique Customers":        unique_customers,
            "Current Customers":       current_acq,
            "New Customers":           new_acq,
            "Potential Customers":     potential,
            "Visits Per Day":          visits_per_day,
            "Visits Per Month":        visits_per_month,
            "Conversion Rate (%)":     conversion_rate,
        })

    kpi_df = pd.DataFrame(records)
    if kpi_df.empty:
        return kpi_df, []

    # Ranking by total visits
    kpi_df = kpi_df.sort_values("Total Visits", ascending=False).reset_index(drop=True)
    kpi_df.insert(0, "Rank", range(1, len(kpi_df) + 1))

    # ── Charts ──
    figures = []

    # 1. Total visits bar
    fig1 = px.bar(
        kpi_df, x="Sales Rep Name", y="Total Visits",
        color="Total Visits",
        color_continuous_scale=[[0, "#BDD7EE"], [1, PRIMARY]],
        template=PLOTLY_TEMPLATE,
        title="Total Visits per Sales Rep",
        text="Total Visits",
    )
    fig1.update_traces(textposition="outside")
    fig1.update_layout(paper_bgcolor=BG, showlegend=False,
                       margin=dict(l=20, r=20, t=50, b=100),
                       xaxis_tickangle=-35)
    figures.append(("Total Visits per Sales Rep", fig1))

    # 2. Conversion rate
    fig2 = px.bar(
        kpi_df.sort_values("Conversion Rate (%)"), x="Conversion Rate (%)", y="Sales Rep Name",
        orientation="h",
        color="Conversion Rate (%)",
        color_continuous_scale=[[0, "#BDD7EE"], [1, ACCENT]],
        template=PLOTLY_TEMPLATE,
        title="Conversion Rate (%) by Sales Rep",
        text="Conversion Rate (%)",
    )
    fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig2.update_layout(paper_bgcolor=BG, showlegend=False,
                       margin=dict(l=20, r=20, t=50, b=20))
    figures.append(("Conversion Rate", fig2))

    # 3. Customer status stacked bar
    status_cols = ["Current Customers", "New Customers", "Potential Customers"]
    available   = [c for c in status_cols if c in kpi_df.columns]
    if available:
        fig3 = go.Figure()
        colors_map = {
            "Current Customers":   ACCENT,
            "New Customers":       PRIMARY,
            "Potential Customers": SECONDARY,
        }
        for col in available:
            fig3.add_trace(go.Bar(
                name=col, x=kpi_df["Sales Rep Name"], y=kpi_df[col],
                marker_color=colors_map.get(col, "#888"),
            ))
        fig3.update_layout(
            barmode="stack",
            title="Customer Status by Sales Rep",
            template=PLOTLY_TEMPLATE,
            paper_bgcolor=BG,
            margin=dict(l=20, r=20, t=50, b=100),
            xaxis_tickangle=-35,
        )
        figures.append(("Customer Status by Rep", fig3))

    return kpi_df, figures


# ═══════════════════════════════════════════════════════════════════
# PAGE 5 — EXECUTIVE DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def executive_dashboard_data(
    classified_df: pd.DataFrame,
    journey_df: pd.DataFrame,
    kpi_df: pd.DataFrame,
) -> dict:
    """
    Prepare all data needed for the executive dashboard page.
    """
    result = {}
    today = pd.Timestamp(datetime.today().date())

    # ── KPI cards ──
    unique_c   = journey_df["Customer Name"].nunique() if not journey_df.empty else 0
    kpis = {}
    kpis["Total Visits"]        = len(classified_df)
    kpis["Unique Customers"]    = unique_c
    kpis["Current Customers"]   = int((journey_df["Latest Status"] == "Current Customer").sum())
    kpis["Target Customers"]    = int((journey_df["Latest Status"] == "Target Customer").sum())
    kpis["Potential Customers"] = int((journey_df["Latest Status"] == "Potential Customer").sum())
    kpis["New Customers"]       = int((journey_df["Latest Status"] == "New Customer").sum())
    kpis["Former Customers"]    = int((journey_df["Latest Status"] == "Former Customer").sum())
    kpis["Not Interested"]      = int((journey_df["Latest Status"] == "Not Interested").sum())
    result["kpis"] = kpis

    # ── Monthly trend ──
    if "Visit Date" in classified_df.columns:
        df_m = classified_df.copy()
        df_m["Month_Period"] = df_m["Visit Date"].dt.to_period("M").astype(str)
        monthly = (
            df_m.groupby("Month_Period")
            .agg(
                Total_Visits=("Customer Name", "count"),
                Unique_Customers=("Customer Name", "nunique"),
            )
            .reset_index()
            .rename(columns={"Month_Period": "Month", "Total_Visits": "Total Visits",
                              "Unique_Customers": "Unique Customers"})
        )
        result["monthly_df"] = monthly

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=monthly["Month"], y=monthly["Total Visits"],
            mode="lines+markers+text",
            name="Total Visits",
            line=dict(color=PRIMARY, width=3),
            marker=dict(size=8),
            text=monthly["Total Visits"],
            textposition="top center",
        ))
        fig_trend.add_trace(go.Scatter(
            x=monthly["Month"], y=monthly["Unique Customers"],
            mode="lines+markers",
            name="Unique Customers",
            line=dict(color=ACCENT, width=2, dash="dot"),
            marker=dict(size=6),
        ))
        fig_trend.update_layout(
            title="Monthly Visit Trend",
            template=PLOTLY_TEMPLATE,
            paper_bgcolor=BG,
            legend=dict(orientation="h", y=-0.2),
            margin=dict(l=20, r=20, t=50, b=60),
            xaxis_tickangle=-45,
        )
        result["fig_trend"] = fig_trend
    else:
        result["monthly_df"] = pd.DataFrame()
        result["fig_trend"]  = None

    # ── Sales rep ranking ──
    if not kpi_df.empty:
        fig_rank = px.bar(
            kpi_df.head(10), x="Total Visits", y="Sales Rep Name",
            orientation="h",
            color="Total Visits",
            color_continuous_scale=[[0, "#BDD7EE"], [1, PRIMARY]],
            template=PLOTLY_TEMPLATE,
            title="Top Sales Reps by Total Visits",
            text="Total Visits",
        )
        fig_rank.update_traces(textposition="outside")
        fig_rank.update_layout(
            paper_bgcolor=BG, showlegend=False,
            margin=dict(l=20, r=20, t=50, b=20),
            yaxis=dict(autorange="reversed"),
        )
        result["fig_rep_ranking"] = fig_rank
    else:
        result["fig_rep_ranking"] = None

    # ── Status distribution pie ──
    status_counts = journey_df["Latest Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    result["status_dist_df"] = status_counts

    colors = [STATUS_COLORS.get(s, PRIMARY) for s in status_counts["Status"]]
    fig_status = go.Figure(go.Pie(
        labels=status_counts["Status"],
        values=status_counts["Count"],
        marker_colors=colors,
        hole=0.45,
        textinfo="label+percent+value",
        hovertemplate="<b>%{label}</b><br>Customers: %{value}<br>%{percent}<extra></extra>",
    ))
    fig_status.update_layout(
        title="Customer Status Distribution",
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=BG,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    result["fig_status_pie"] = fig_status

    # ── Governorate distribution ──
    if "Governorate" in classified_df.columns:
        gov_counts = (
            classified_df.groupby("Governorate")["Customer Name"]
            .nunique().reset_index()
            .rename(columns={"Customer Name": "Unique Customers"})
            .sort_values("Unique Customers", ascending=False)
            .head(15)
        )
        result["gov_dist_df"] = gov_counts

        fig_gov = px.bar(
            gov_counts, x="Unique Customers", y="Governorate",
            orientation="h",
            color_discrete_sequence=[SECONDARY],
            template=PLOTLY_TEMPLATE,
            title="Customers by Governorate (Top 15)",
            text="Unique Customers",
        )
        fig_gov.update_traces(textposition="outside")
        fig_gov.update_layout(
            paper_bgcolor=BG,
            margin=dict(l=20, r=20, t=50, b=20),
            yaxis=dict(autorange="reversed"),
        )
        result["fig_gov"] = fig_gov
    else:
        result["gov_dist_df"] = pd.DataFrame()
        result["fig_gov"]     = None

    # ── District distribution ──
    if "District" in classified_df.columns:
        dist_counts = (
            classified_df.groupby("District")["Customer Name"]
            .nunique().reset_index()
            .rename(columns={"Customer Name": "Unique Customers"})
            .sort_values("Unique Customers", ascending=False)
            .head(15)
        )
        result["district_dist_df"] = dist_counts

        fig_dist = px.treemap(
            dist_counts, path=["District"], values="Unique Customers",
            color="Unique Customers",
            color_continuous_scale=[[0, "#BDD7EE"], [1, PRIMARY]],
            title="Customers by District",
        )
        fig_dist.update_layout(paper_bgcolor=BG, margin=dict(l=10, r=10, t=50, b=10))
        result["fig_district"] = fig_dist
    else:
        result["district_dist_df"] = pd.DataFrame()
        result["fig_district"]     = None

    # ── Top customers ──
    if not journey_df.empty:
        top_c = (
            journey_df.nlargest(20, "Visit Count")[
                ["Customer Name", "Visit Count", "Latest Status",
                 "Days Since Last Visit", "Governorate"]
            ].reset_index(drop=True)
        )
        top_c.index += 1
        result["top_customers_df"] = top_c
    else:
        result["top_customers_df"] = pd.DataFrame()

    # ── Follow-up required (not visited 30+ days) ──
    if not journey_df.empty:
        fu = (
            journey_df[journey_df["Days Since Last Visit"].fillna(9999) >= 30]
            .sort_values("Days Since Last Visit", ascending=False)
            [["Customer Name", "Days Since Last Visit", "Latest Status",
              "Last Visit Date", "Sales Rep Name"]]
            .head(30)
            .reset_index(drop=True)
        )
        fu.index += 1
        result["followup_df"] = fu
    else:
        result["followup_df"] = pd.DataFrame()

    return result
