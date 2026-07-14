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

import plotly.io as pio

from utils import safe_str, days_since, STATUS_COLORS, NON_STATUS_LABELS, STATUS_AR

# Brand palette (WDI dark design)
PRIMARY   = "#2DD4BF"   # teal
SECONDARY = "#4C9AFF"   # blue
ACCENT    = "#70AD47"   # green
BG        = "rgba(0,0,0,0)"

# ── Custom dark Plotly template matching the approved design ──
_wdi = go.layout.Template(pio.templates["plotly_dark"])
_wdi.layout.paper_bgcolor = "rgba(0,0,0,0)"
_wdi.layout.plot_bgcolor  = "rgba(0,0,0,0)"
_wdi.layout.font = dict(color="#8B98A5",
                        family="'IBM Plex Sans Arabic','Segoe UI',sans-serif")
_wdi.layout.xaxis = dict(gridcolor="#1D262F", zerolinecolor="#1D262F", linecolor="#2A3540")
_wdi.layout.yaxis = dict(gridcolor="#1D262F", zerolinecolor="#1D262F", linecolor="#2A3540")
_wdi.layout.colorway = ["#2DD4BF", "#4C9AFF", "#70AD47", "#FFC000",
                        "#F08080", "#A78BFA", "#ED7D31", "#8B98A5"]
_wdi.layout.hoverlabel = dict(bgcolor="#10171D", bordercolor="#1D262F",
                              font=dict(color="#E6EDF3"))
pio.templates["wdi_dark"] = _wdi

PLOTLY_TEMPLATE = "wdi_dark"

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
        labels=[STATUS_AR.get(s, s) for s in status_counts["Status"]],
        values=status_counts["Count"],
        marker=dict(colors=colors, line=dict(color="#161D24", width=2)),
        hole=0.45,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value}<br>%{percent}<extra></extra>",
    ))
    fig_pie.update_layout(
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
# CUSTOMER TRANSITIONS (FUNNEL)
# ═══════════════════════════════════════════════════════════════════

def customer_transitions(classified_df: pd.DataFrame) -> pd.DataFrame:
    """
    Ordered real-status changes per customer, visit by visit.
    No Meeting / Unclassified visits are ignored — they don't represent
    a change in the customer's position.
    """
    if classified_df.empty or "Display Status" not in classified_df.columns:
        return pd.DataFrame()

    df = classified_df[~classified_df["Display Status"].isin(NON_STATUS_LABELS)]
    df = df.sort_values("Visit Date")

    recs = []
    for cust, g in df.groupby("Customer Name", sort=False):
        statuses = g["Display Status"].tolist()
        dates    = g["Visit Date"].tolist()
        reps     = g["Sales Rep Name"].tolist() if "Sales Rep Name" in g.columns else [""] * len(g)
        govs     = g["Governorate"].tolist()    if "Governorate"    in g.columns else [""] * len(g)
        prev = statuses[0]
        for i in range(1, len(statuses)):
            if statuses[i] != prev:
                recs.append({
                    "Customer Name":   cust,
                    "From Status":     prev,
                    "To Status":       statuses[i],
                    "Transition Date": dates[i],
                    "Sales Rep Name":  reps[i],
                    "Governorate":     govs[i],
                })
                prev = statuses[i]
    return pd.DataFrame(recs)


def funnel_data(classified_df: pd.DataFrame, journey_df: pd.DataFrame) -> dict:
    """
    Funnel analytics:
      - transitions:  all status changes
      - matrix:       From × To counts
      - conversions:  first transition of each customer INTO Current Customer
      - churn:        customers who were Current and whose latest status is
                      Former / Not Interested (قائمة إنقاذ)
      - rep_conversions + fig
    """
    out = {"transitions": pd.DataFrame(), "matrix": pd.DataFrame(),
           "conversions": pd.DataFrame(), "churn": pd.DataFrame(),
           "rep_conversions": pd.DataFrame(), "fig_rep_conversions": None}

    trans = customer_transitions(classified_df)
    out["transitions"] = trans

    # ── Churn (independent of transitions) ──
    if not journey_df.empty:
        was_current = set(
            classified_df.loc[classified_df["Display Status"] == "Current Customer", "Customer Name"]
        )
        churn = journey_df[
            journey_df["Customer Name"].isin(was_current)
            & journey_df["Latest Status"].isin(["Former Customer", "Not Interested"])
        ]
        cols = [c for c in ["Customer Name", "Latest Status", "Last Visit Date",
                            "Days Since Last Visit", "Governorate", "Sales Rep Name"]
                if c in churn.columns]
        out["churn"] = (churn[cols]
                        .sort_values("Days Since Last Visit", ascending=False)
                        .reset_index(drop=True))

    if trans.empty:
        return out

    # ── From × To matrix ──
    out["matrix"] = trans.pivot_table(
        index="From Status", columns="To Status",
        values="Customer Name", aggfunc="count", fill_value=0,
    )

    # ── Conversions into Current (first one per customer) ──
    conv = (trans[trans["To Status"] == "Current Customer"]
            .sort_values("Transition Date")
            .groupby("Customer Name", as_index=False).head(1).copy())
    if not conv.empty and not journey_df.empty and "First Visit Date" in journey_df.columns:
        conv = conv.merge(journey_df[["Customer Name", "First Visit Date"]],
                          on="Customer Name", how="left")
        conv["Days To Convert"] = (
            pd.to_datetime(conv["Transition Date"], errors="coerce")
            - pd.to_datetime(conv["First Visit Date"], errors="coerce")
        ).dt.days
    out["conversions"] = conv.reset_index(drop=True)

    # ── Conversions per rep ──
    if not conv.empty:
        rep_conv = (conv.groupby("Sales Rep Name").size()
                    .reset_index(name="Conversions")
                    .sort_values("Conversions", ascending=True))
        out["rep_conversions"] = rep_conv
        fig = px.bar(
            rep_conv, x="Conversions", y="Sales Rep Name", orientation="h",
            color_discrete_sequence=[ACCENT], template=PLOTLY_TEMPLATE,
            text="Conversions",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(paper_bgcolor=BG, margin=dict(l=20, r=40, t=50, b=20))
        out["fig_rep_conversions"] = fig

    return out


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

    # True conversions: customers whose status CHANGED to Current during
    # a visit by this rep (attribution to the converting visit's rep)
    trans = customer_transitions(classified_df)
    if not trans.empty:
        conv_by_rep = (trans[trans["To Status"] == "Current Customer"]
                       .sort_values("Transition Date")
                       .groupby("Customer Name", as_index=False).head(1)
                       .groupby("Sales Rep Name").size())
    else:
        conv_by_rep = pd.Series(dtype=int)

    for rep_name, grp in classified_df.groupby("Sales Rep Name"):
        total_visits     = len(grp)
        unique_customers = grp["Customer Name"].nunique()

        # Count CUSTOMERS (not visits) by their final real status with this rep —
        # a current customer visited 5 times used to count as 5.
        real = grp[~grp["Display Status"].isin(NON_STATUS_LABELS)]
        last_real = real.sort_values("Visit Date").groupby("Customer Name").tail(1)
        current_acq  = int((last_real["Display Status"] == "Current Customer").sum())
        new_acq      = int((last_real["Display Status"] == "New Customer").sum())
        potential    = int((last_real["Display Status"] == "Potential Customer").sum())

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
            "True Conversions":        int(conv_by_rep.get(rep_name, 0)),
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

    # ── Charts (per the approved design: two horizontal bars) ──
    figures = []

    # 1. Total visits per rep — horizontal teal
    by_visits = kpi_df.sort_values("Total Visits")
    fig1 = px.bar(
        by_visits, x="Total Visits", y="Sales Rep Name", orientation="h",
        color_discrete_sequence=[PRIMARY], template=PLOTLY_TEMPLATE,
        text="Total Visits",
    )
    fig1.update_traces(textposition="outside", marker=dict(cornerradius=4))
    fig1.update_layout(paper_bgcolor=BG, showlegend=False, height=380,
                       margin=dict(l=10, r=45, t=10, b=10),
                       xaxis_title="", yaxis_title="")
    figures.append(("إجمالي الزيارات لكل مندوب", fig1))

    # 2. Conversion rate — horizontal green
    by_rate = kpi_df.sort_values("Conversion Rate (%)")
    fig2 = px.bar(
        by_rate, x="Conversion Rate (%)", y="Sales Rep Name", orientation="h",
        color_discrete_sequence=[ACCENT], template=PLOTLY_TEMPLATE,
        text="Conversion Rate (%)",
    )
    fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside",
                       marker=dict(cornerradius=4))
    fig2.update_layout(paper_bgcolor=BG, showlegend=False, height=380,
                       margin=dict(l=10, r=45, t=10, b=10),
                       xaxis_title="", yaxis_title="")
    figures.append(("معدل التحويل % لكل مندوب", fig2))

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
            color_discrete_sequence=[PRIMARY],
            template=PLOTLY_TEMPLATE,
            text="Total Visits",
        )
        fig_rank.update_traces(textposition="outside", marker=dict(cornerradius=4))
        fig_rank.update_layout(
            paper_bgcolor=BG, showlegend=False,
            margin=dict(l=10, r=45, t=10, b=10),
            xaxis_title="", yaxis_title="",
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
        labels=[STATUS_AR.get(s, s) for s in status_counts["Status"]],
        values=status_counts["Count"],
        marker=dict(colors=colors, line=dict(color="#161D24", width=2)),
        hole=0.45,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value}<br>%{percent}<extra></extra>",
    ))
    fig_status.update_layout(
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
            color_continuous_scale=[[0, "#14655C"], [1, PRIMARY]],
            
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

    # ── Funnel: transitions, conversions, churn ──
    result["funnel"] = funnel_data(classified_df, journey_df)

    return result
